"""Processamento em lote: lê os documentos baixados (em vários processos) e grava páginas e trechos.

O trabalho pesado (pdfplumber, renderização e OCR) roda em processos separados; só o processo
principal escreve no banco. Um documento já processado com a mesma versão do leitor é pulado, então
a execução pode ser interrompida e retomada.
"""

import logging
import os
import time
from collections.abc import Callable, Iterable
from concurrent.futures import Executor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from contratolens.db.models import Chunk as ChunkRecord
from contratolens.db.models import Document, Page, ProcessingStatus
from contratolens.documents.chunker import chunk_pages
from contratolens.documents.reader import UnsupportedDocumentError, read_document

logger = logging.getLogger(__name__)

READER_VERSION = "1"


def _limit_ocr_threads() -> None:
    """Prepara cada processo de trabalho.

    Um processo por núcleo: o Tesseract não deve abrir várias threads em cada processo. Os
    processos não herdam a configuração de log do principal, então os avisos do pdfminer sobre
    PDFs malformados (sem efeito na extração) são silenciados aqui também.
    """
    os.environ["OMP_THREAD_LIMIT"] = "1"
    logging.getLogger("pdfminer").setLevel(logging.ERROR)


def process_file(document_id: int, path: str, lang: str = "por") -> dict[str, Any]:
    """Lê um arquivo e devolve um resultado serializável (roda dentro do processo de trabalho)."""
    start = time.perf_counter()
    result: dict[str, Any] = {"document_id": document_id, "pages": [], "chunks": []}
    try:
        content = read_document(Path(path), lang=lang)
    except UnsupportedDocumentError as exc:
        result.update(status=ProcessingStatus.UNSUPPORTED, file_type=str(exc), error=None)
    except Exception as exc:  # noqa: BLE001 - qualquer falha de leitura vira registro, não queda
        result.update(
            status=ProcessingStatus.ERROR, file_type=None, error=f"{type(exc).__name__}: {exc}"
        )
    else:
        result.update(
            status=ProcessingStatus.DONE,
            file_type=content.file_type,
            error=None,
            ocr_pages=content.ocr_pages,
            pages=[
                {
                    "page_number": page.number,
                    "width": page.width,
                    "height": page.height,
                    "source": page.source,
                    "char_count": page.char_count,
                    "ocr_confidence": page.ocr_confidence,
                    "words": [word.as_list() for word in page.words],
                }
                for page in content.pages
            ],
            chunks=[chunk.__dict__ for chunk in chunk_pages(content.pages)],
        )
    result["seconds"] = round(time.perf_counter() - start, 3)
    return result


@dataclass
class BatchStats:
    """Contagem de uma execução do lote."""

    processed: int = 0
    done: int = 0
    unsupported: int = 0
    errors: int = 0
    pages: int = 0
    ocr_pages: int = 0
    chunks: int = 0
    seconds: list[float] = field(default_factory=list)


def pending_documents(
    session_factory: sessionmaker[Session], *, retry_errors: bool = False, reprocess: bool = False
) -> list[tuple[int, str]]:
    """Documentos a processar: pendentes, de versão antiga do leitor e, se pedido, os com erro."""
    with session_factory() as session:
        query = select(Document.id, Document.local_path)
        if not reprocess:
            statuses = [ProcessingStatus.PENDING]
            if retry_errors:
                statuses.append(ProcessingStatus.ERROR)
            query = query.where(
                (Document.processing_status.in_(statuses))
                | (
                    Document.reader_version.is_not(None)
                    & (Document.reader_version != READER_VERSION)
                )
            )
        return [(row.id, row.local_path) for row in session.execute(query.order_by(Document.id))]


def save_result(session: Session, result: dict[str, Any]) -> None:
    """Grava o resultado de um documento, substituindo páginas e trechos de uma leitura anterior."""
    document = session.get(Document, result["document_id"])
    session.execute(delete(Page).where(Page.document_id == document.id))
    session.execute(delete(ChunkRecord).where(ChunkRecord.document_id == document.id))
    document.processing_status = result["status"]
    document.file_type = result["file_type"]
    document.processing_error = result["error"]
    document.processing_seconds = result["seconds"]
    document.ocr_pages = result.get("ocr_pages")
    document.pages = len(result["pages"]) or None
    document.needs_ocr = bool(result.get("ocr_pages")) if result["status"] == "done" else None
    document.reader_version = READER_VERSION
    document.processed_at = datetime.now()
    for page in result["pages"]:
        session.add(Page(document_id=document.id, **page))
    for chunk in result["chunks"]:
        session.add(
            ChunkRecord(
                document_id=document.id,
                page_number=chunk["page_number"],
                chunk_index=chunk["index"],
                text=chunk["text"],
                x0=chunk["x0"],
                top=chunk["top"],
                x1=chunk["x1"],
                bottom=chunk["bottom"],
                source=chunk["source"],
            )
        )


def process_documents(
    session_factory: sessionmaker[Session],
    documents: Iterable[tuple[int, str]],
    *,
    workers: int = 1,
    executor_factory: Callable[[int], Executor] | None = None,
    progress_every: int = 10,
) -> BatchStats:
    """Processa os documentos em paralelo e grava cada resultado assim que fica pronto."""
    documents = list(documents)
    stats = BatchStats()
    started = time.monotonic()
    factory = executor_factory or (
        lambda n: ProcessPoolExecutor(max_workers=n, initializer=_limit_ocr_threads)
    )
    executor = factory(workers)
    futures = [executor.submit(process_file, doc_id, path) for doc_id, path in documents]
    try:
        for future in as_completed(futures):
            result = _save_or_record_error(session_factory, future.result())
            stats.processed += 1
            stats.seconds.append(result["seconds"])
            if result["status"] == ProcessingStatus.DONE:
                stats.done += 1
                stats.pages += len(result["pages"])
                stats.ocr_pages += result.get("ocr_pages") or 0
                stats.chunks += len(result["chunks"])
            elif result["status"] == ProcessingStatus.UNSUPPORTED:
                stats.unsupported += 1
                logger.info(
                    "Documento %s em formato não tratado: %s",
                    result["document_id"],
                    result["file_type"],
                )
            else:
                stats.errors += 1
                logger.warning("Documento %s com erro: %s", result["document_id"], result["error"])
            if progress_every and stats.processed % progress_every == 0:
                elapsed = time.monotonic() - started
                rate = stats.processed / elapsed * 3600 if elapsed else 0.0
                remaining = (len(documents) - stats.processed) / rate if rate else 0.0
                logger.info(
                    "Progresso: %s/%s documentos, %s páginas (%s com OCR); %.0f docs/h; "
                    "faltam ~%.1f h",
                    stats.processed,
                    len(documents),
                    stats.pages,
                    stats.ocr_pages,
                    rate,
                    remaining,
                )
    except BaseException:
        # Ctrl+C ou erro inesperado: cancela o que ainda não começou, em vez de esperar a fila toda.
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    executor.shutdown(wait=True)
    return stats


def _save_or_record_error(
    session_factory: sessionmaker[Session], result: dict[str, Any]
) -> dict[str, Any]:
    """Grava o resultado; se o banco recusar, registra o documento como erro e segue em frente."""
    try:
        with session_factory.begin() as session:
            save_result(session, result)
        return result
    except SQLAlchemyError as exc:
        message = f"Falha ao gravar: {type(exc).__name__}: {str(exc).splitlines()[0][:300]}"
        failed = {
            **result,
            "status": ProcessingStatus.ERROR,
            "error": message,
            "pages": [],
            "chunks": [],
            "ocr_pages": None,
        }
        with session_factory.begin() as session:
            save_result(session, failed)
        return failed

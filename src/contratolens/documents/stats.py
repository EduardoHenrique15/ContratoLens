"""Estatísticas da leitura de documentos (Fase 2), só com números agregados."""

import statistics
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from contratolens.db.models import Chunk, Document, Page, ProcessingStatus


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def _summary(values: list[float], digits: int = 1) -> dict[str, float | None]:
    if not values:
        return {"media": None, "mediana": None, "p95": None}
    return {
        "media": round(statistics.mean(values), digits),
        "mediana": round(statistics.median(values), digits),
        "p95": round(_percentile(values, 0.95), digits),
    }


def reading_stats(session_factory: sessionmaker[Session]) -> dict[str, Any]:
    """Páginas, porcentagem escaneada, qualidade do OCR, trechos e tempo de processamento."""
    with session_factory() as session:
        by_status = dict(
            session.execute(
                select(Document.processing_status, func.count()).group_by(
                    Document.processing_status
                )
            ).all()
        )
        by_type = dict(
            session.execute(
                select(Document.file_type, func.count()).group_by(Document.file_type)
            ).all()
        )
        done = Document.processing_status == ProcessingStatus.DONE
        docs = session.execute(
            select(Document.pages, Document.ocr_pages, Document.processing_seconds).where(done)
        ).all()
        pages = session.execute(select(Page.source, Page.char_count, Page.ocr_confidence)).all()
        chunk_lengths = [
            length for (length,) in session.execute(select(func.length(Chunk.text))).all()
        ]

    total_pages = len(pages)
    ocr_pages = [p for p in pages if p.source == "ocr"]
    native_pages = [p for p in pages if p.source == "native"]
    docs_with_ocr = sum(1 for d in docs if d.ocr_pages)
    return {
        "documentos_por_status": {k or "?": v for k, v in by_status.items()},
        "documentos_por_formato": {k or "?": v for k, v in by_type.items()},
        "documentos_lidos": len(docs),
        "documentos_com_ocr": docs_with_ocr,
        "porcentagem_documentos_com_ocr": round(100 * docs_with_ocr / len(docs), 1)
        if docs
        else None,
        "paginas": total_pages,
        "paginas_com_ocr": len(ocr_pages),
        "porcentagem_paginas_com_ocr": (
            round(100 * len(ocr_pages) / total_pages, 1) if total_pages else None
        ),
        "paginas_por_documento": _summary([d.pages or 0 for d in docs]),
        "caracteres_por_pagina_nativa": _summary([p.char_count for p in native_pages], 0),
        "caracteres_por_pagina_ocr": _summary([p.char_count for p in ocr_pages], 0),
        "confianca_ocr": _summary([p.ocr_confidence for p in ocr_pages if p.ocr_confidence]),
        "paginas_ocr_vazias": sum(1 for p in ocr_pages if p.char_count == 0),
        "trechos": len(chunk_lengths),
        "caracteres_por_trecho": _summary(chunk_lengths, 0),
        "segundos_por_documento": _summary([d.processing_seconds or 0 for d in docs], 2),
        "segundos_por_documento_com_ocr": _summary(
            [d.processing_seconds or 0 for d in docs if d.ocr_pages], 2
        ),
        "segundos_por_documento_sem_ocr": _summary(
            [d.processing_seconds or 0 for d in docs if not d.ocr_pages], 2
        ),
    }

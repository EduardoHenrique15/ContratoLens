import shutil
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from contratolens.db.models import Chunk, Contract, Document, Page, ProcessingStatus
from contratolens.documents.processor import (
    READER_VERSION,
    pending_documents,
    process_documents,
)
from tests.fakes.pdf_factory import CONTRACT_PAGE, scanned_pdf, text_pdf


def threads(n):
    return ThreadPoolExecutor(max_workers=n)


def add_document(session_factory, path, seq):
    with session_factory.begin() as session:
        contract_id = f"1-2-{seq:06d}/2026"
        if session.get(Contract, contract_id) is None:
            session.add(Contract(id=contract_id, orgao_cnpj="1", ano=2026, sequencial=seq, raw={}))
        document = Document(
            contract_id=contract_id,
            sequencial_documento=1,
            url="u",
            local_path=str(path),
            sha256="x" * 64,
            size_bytes=path.stat().st_size,
        )
        session.add(document)
        session.flush()
        return document.id


def count(session_factory, model, *where):
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model).where(*where))


def test_processes_native_pdf_and_saves_pages_and_chunks(session_factory, tmp_path):
    path = text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE, [(72, 72, "Página final do contrato.")]])
    doc_id = add_document(session_factory, path, 1)
    stats = process_documents(
        session_factory, pending_documents(session_factory), executor_factory=threads
    )
    assert stats.done == 1 and stats.pages == 2 and stats.ocr_pages == 0
    with session_factory() as session:
        document = session.get(Document, doc_id)
        assert document.processing_status == ProcessingStatus.DONE
        assert document.pages == 2 and document.needs_ocr is False
        assert document.reader_version == READER_VERSION
        page = session.scalar(select(Page).where(Page.page_number == 1))
        assert page.source == "native" and page.words[0][0] == "CONTRATO"
        chunks = session.scalars(select(Chunk).order_by(Chunk.chunk_index)).all()
        assert any("71.240,90" in c.text and c.page_number == 1 for c in chunks)


def test_is_idempotent(session_factory, tmp_path):
    path = text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE])
    add_document(session_factory, path, 1)
    process_documents(session_factory, pending_documents(session_factory), executor_factory=threads)
    chunks_before = count(session_factory, Chunk)
    assert pending_documents(session_factory) == []
    process_documents(
        session_factory,
        pending_documents(session_factory, reprocess=True),
        executor_factory=threads,
    )
    assert count(session_factory, Chunk) == chunks_before  # reprocessar substitui, não duplica


def test_unsupported_and_broken_files_are_recorded(session_factory, tmp_path):
    ole = tmp_path / "b.pdf"
    ole.write_bytes(b"\xd0\xcf\x11\xe0" + b"0" * 64)
    broken = tmp_path / "c.pdf"
    broken.write_bytes(b"%PDF-1.4\nisso nao e um pdf valido")
    add_document(session_factory, ole, 2)
    add_document(session_factory, broken, 3)
    stats = process_documents(
        session_factory, pending_documents(session_factory), executor_factory=threads
    )
    assert stats.unsupported == 1 and stats.errors == 1
    with session_factory() as session:
        rows = dict(session.execute(select(Document.file_type, Document.processing_status)).all())
    assert rows["ole"] == ProcessingStatus.UNSUPPORTED
    assert count(session_factory, Document, Document.processing_status == "error") == 1
    assert pending_documents(session_factory) == []
    assert len(pending_documents(session_factory, retry_errors=True)) == 1


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract ausente")
def test_scanned_pdf_with_real_process_pool(session_factory, tmp_path):
    source = text_pdf(tmp_path / "fonte.pdf", [CONTRACT_PAGE])
    path = scanned_pdf(tmp_path / "escaneado.pdf", source)
    doc_id = add_document(session_factory, path, 4)
    stats = process_documents(session_factory, pending_documents(session_factory), workers=2)
    assert stats.ocr_pages == 1
    with session_factory() as session:
        document = session.get(Document, doc_id)
        assert document.needs_ocr is True and document.ocr_pages == 1
        page = session.scalar(select(Page))
        assert page.source == "ocr" and page.ocr_confidence > 70


def test_reading_stats(session_factory, tmp_path):
    from contratolens.documents.stats import reading_stats

    native = text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE, CONTRACT_PAGE])
    ole = tmp_path / "b.pdf"
    ole.write_bytes(b"\xd0\xcf\x11\xe0" + b"0" * 64)
    add_document(session_factory, native, 1)
    add_document(session_factory, ole, 2)
    process_documents(session_factory, pending_documents(session_factory), executor_factory=threads)
    stats = reading_stats(session_factory)
    assert stats["documentos_por_status"] == {"done": 1, "unsupported": 1}
    assert stats["documentos_por_formato"] == {"pdf": 1, "ole": 1}
    assert stats["paginas"] == 2 and stats["paginas_com_ocr"] == 0
    assert stats["porcentagem_paginas_com_ocr"] == 0.0
    assert stats["trechos"] >= 2
    assert stats["paginas_por_documento"]["mediana"] == 2


def test_database_rejection_is_recorded_as_error_and_batch_continues(
    session_factory, tmp_path, monkeypatch
):
    from sqlalchemy.exc import DataError

    from contratolens.documents import processor

    first = add_document(session_factory, text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE]), 1)
    second = add_document(session_factory, text_pdf(tmp_path / "b.pdf", [CONTRACT_PAGE]), 2)
    original = processor.save_result

    def reject_first(session, result):
        if result["document_id"] == first and result["status"] == "done":
            raise DataError("INSERT", {}, Exception("text fields cannot contain NUL (0x00) bytes"))
        return original(session, result)

    monkeypatch.setattr(processor, "save_result", reject_first)
    stats = process_documents(
        session_factory, pending_documents(session_factory), executor_factory=threads
    )
    assert stats.errors == 1 and stats.done == 1
    with session_factory() as session:
        failed = session.get(Document, first)
        assert failed.processing_status == "error" and "NUL" in failed.processing_error
        assert session.get(Document, second).processing_status == "done"
    assert count(session_factory, Chunk, Chunk.document_id == first) == 0


def test_nul_text_reaching_the_database_is_recorded_not_fatal(session_factory, tmp_path):
    """No PostgreSQL, \\x00 é recusado: o documento vira erro e o lote continua."""
    from contratolens.documents.processor import _save_or_record_error

    doc_id = add_document(session_factory, text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE]), 1)
    result = {
        "document_id": doc_id,
        "status": "done",
        "file_type": "pdf",
        "error": None,
        "ocr_pages": 0,
        "seconds": 0.1,
        "pages": [],
        "chunks": [
            {
                "page_number": 1,
                "index": 0,
                "text": "CON\x00TRATO",
                "x0": 0,
                "top": 0,
                "x1": 1,
                "bottom": 1,
                "source": "native",
            }
        ],
    }
    saved = _save_or_record_error(session_factory, result)
    dialect = session_factory.kw["bind"].dialect.name
    expected = "error" if dialect == "postgresql" else "done"
    assert saved["status"] == expected
    with session_factory() as session:
        assert session.get(Document, doc_id).processing_status == expected

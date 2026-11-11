"""Modelos do banco.

Fase 1: contratos, documentos e fila de coleta. Fase 2: páginas e trechos com coordenadas.
As tabelas das fases seguintes (extractions, reviews, llm_calls) entram com migrações próprias.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from contratolens.db.base import Base


class DownloadStatus:
    """Valores possíveis de Contract.download_status."""

    PENDING = "pending"
    DOWNLOADED = "downloaded"
    NO_CONTRACT_DOCUMENT = "no_contract_document"
    FAILED = "failed"


class ProcessingStatus:
    """Valores possíveis de Document.processing_status (leitura do arquivo, Fase 2)."""

    PENDING = "pending"
    DONE = "done"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class JobStatus:
    """Valores possíveis de IngestJob.status."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Contract(Base):
    """Contrato publicado no PNCP, com os metadados oficiais usados como gabarito."""

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # numeroControlePNCP
    orgao_cnpj: Mapped[str] = mapped_column(String(14), index=True)
    ano: Mapped[int] = mapped_column(Integer)
    sequencial: Mapped[int] = mapped_column(Integer)
    orgao_nome: Mapped[str | None] = mapped_column(Text)
    esfera: Mapped[str | None] = mapped_column(String(8))
    unidade_nome: Mapped[str | None] = mapped_column(Text)
    uf: Mapped[str | None] = mapped_column(String(2), index=True)
    municipio: Mapped[str | None] = mapped_column(Text)
    tipo_pessoa: Mapped[str | None] = mapped_column(String(8))
    # CNPJ, CPF mascarado ou identificador de estrangeiro (ex.: "ESTRANGEIRO_GLOBAL_LIFE")
    fornecedor_ni: Mapped[str | None] = mapped_column(Text)
    fornecedor_nome: Mapped[str | None] = mapped_column(Text)
    objeto: Mapped[str | None] = mapped_column(Text)
    valor_inicial: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    valor_global: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    data_assinatura: Mapped[date | None] = mapped_column(Date)
    vigencia_inicio: Mapped[date | None] = mapped_column(Date)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, index=True)
    tipo_contrato: Mapped[str | None] = mapped_column(Text)
    categoria_processo: Mapped[str | None] = mapped_column(Text)
    numero_contrato: Mapped[str | None] = mapped_column(Text)
    data_publicacao_pncp: Mapped[datetime | None] = mapped_column(DateTime)
    raw: Mapped[dict] = mapped_column(JSON)
    download_status: Mapped[str] = mapped_column(
        String(32), default=DownloadStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(back_populates="contract")


class Document(Base):
    """Arquivo (PDF) de um contrato, baixado do PNCP."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("contract_id", "sequencial_documento"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), index=True)
    sequencial_documento: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str | None] = mapped_column(Text)
    tipo_documento: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    local_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    pages: Mapped[int | None] = mapped_column(Integer)
    needs_ocr: Mapped[bool | None] = mapped_column()
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    file_type: Mapped[str | None] = mapped_column(String(16))
    processing_status: Mapped[str] = mapped_column(
        String(16), default=ProcessingStatus.PENDING, server_default="pending", index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    processing_seconds: Mapped[float | None] = mapped_column(Float)
    ocr_pages: Mapped[int | None] = mapped_column(Integer)
    reader_version: Mapped[str | None] = mapped_column(String(16))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    contract: Mapped[Contract] = relationship(back_populates="documents")
    page_records: Mapped[list["Page"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Page(Base):
    """Página lida: palavras com coordenadas (JSON compacto) e origem do texto (nativo ou OCR)."""

    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(8))
    char_count: Mapped[int] = mapped_column(Integer)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    words: Mapped[list] = mapped_column(JSON)  # [[texto, x0, top, x1, bottom], ...]

    document: Mapped[Document] = relationship(back_populates="page_records")


class Chunk(Base):
    """Trecho (parágrafo ou cláusula) de uma página, com a caixa delimitadora em pontos do PDF."""

    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_document_page", "document_id", "page_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    x0: Mapped[float] = mapped_column(Float)
    top: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    bottom: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(8))

    document: Mapped[Document] = relationship(back_populates="chunks")


class IngestJob(Base):
    """Item da fila de coleta. A chave única garante idempotência ao reenfileirar."""

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    key: Mapped[str] = mapped_column(String(128), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.PENDING, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

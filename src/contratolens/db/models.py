"""Modelos do banco usados na coleta (Fase 1).

As tabelas das fases seguintes (chunks, extractions, reviews, llm_calls) entram com migrações
próprias.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
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

    contract: Mapped[Contract] = relationship(back_populates="documents")


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

"""Coletor do PNCP: fila em banco, idempotência e retomada após queda.

Dois tipos de tarefa na fila (`ingest_jobs`):
- `list_window`: lista os contratos de uma janela de datas, uma página por vez (a próxima
  página fica guardada no payload, então a coleta retoma da página certa);
- `contract_files`: lista os arquivos de um contrato e baixa os do tipo "Contrato".

As tarefas de arquivos têm prioridade, para que os downloads avancem junto com a listagem.
Ao atingir a meta de contratos baixados, a execução para; as tarefas restantes ficam na fila
para uma próxima vez.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from contratolens.core.errors import ExternalServiceError
from contratolens.db.models import Contract, Document, DownloadStatus, IngestJob, JobStatus
from contratolens.ingest.pncp_client import PNCPClient
from contratolens.ingest.schemas import contract_columns

logger = logging.getLogger(__name__)

LIST_WINDOW = "list_window"
CONTRACT_FILES = "contract_files"


@dataclass
class RunStats:
    """Contagem do que aconteceu numa execução."""

    jobs_processed: int = 0
    pages_listed: int = 0
    contracts_seen: int = 0
    contracts_saved: int = 0
    documents_downloaded: int = 0
    documents_skipped: int = 0
    contracts_without_document: int = 0
    failures: int = 0


class Collector:
    """Processa a fila de coleta até acabar, atingir a meta ou o limite de tarefas."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        client: PNCPClient,
        pdf_dir: Path,
        *,
        ufs: set[str] | None = None,
        contract_types: set[str] | None = None,
        max_attempts: int = 3,
        target_downloads: int | None = None,
    ):
        self.session_factory = session_factory
        self.client = client
        self.pdf_dir = pdf_dir
        self.ufs = {uf.upper() for uf in ufs} if ufs else None
        self.contract_types = (
            {t.strip().lower() for t in contract_types} if contract_types else None
        )
        self.max_attempts = max_attempts
        self.target_downloads = target_downloads

    def enqueue_period(self, start: date, end: date, window_days: int = 1) -> int:
        """Cria tarefas de listagem por janela de datas. Janelas já enfileiradas são ignoradas."""
        created = 0
        with self.session_factory.begin() as session:
            current = start
            while current <= end:
                window_end = min(current + timedelta(days=window_days - 1), end)
                key = f"{LIST_WINDOW}:{current:%Y%m%d}:{window_end:%Y%m%d}"
                if session.scalar(select(IngestJob.id).where(IngestJob.key == key)) is None:
                    session.add(
                        IngestJob(
                            kind=LIST_WINDOW,
                            key=key,
                            payload={
                                "start": current.isoformat(),
                                "end": window_end.isoformat(),
                                "next_page": 1,
                            },
                        )
                    )
                    created += 1
                current = window_end + timedelta(days=1)
        return created

    def recover(self) -> int:
        """Devolve à fila as tarefas que ficaram 'running' após uma queda."""
        with self.session_factory.begin() as session:
            result = session.execute(
                update(IngestJob)
                .where(IngestJob.status == JobStatus.RUNNING)
                .values(status=JobStatus.PENDING)
            )
            return result.rowcount or 0

    def downloaded_count(self) -> int:
        """Quantos contratos já têm o documento baixado."""
        with self.session_factory() as session:
            return session.scalar(
                select(func.count())
                .select_from(Contract)
                .where(Contract.download_status == DownloadStatus.DOWNLOADED)
            )

    def run(self, max_jobs: int | None = None) -> RunStats:
        """Processa a fila. Chame `recover()` antes, para retomar após uma queda."""
        stats = RunStats()
        while max_jobs is None or stats.jobs_processed < max_jobs:
            if (
                self.target_downloads is not None
                and self.downloaded_count() >= self.target_downloads
            ):
                logger.info("Meta de %s contratos baixados atingida.", self.target_downloads)
                break
            job_id = self._claim_next()
            if job_id is None:
                break
            self._process(job_id, stats)
            stats.jobs_processed += 1
        return stats

    def _claim_next(self) -> int | None:
        with self.session_factory.begin() as session:
            query = select(IngestJob).where(IngestJob.status == JobStatus.PENDING)
            query = query.order_by(
                case((IngestJob.kind == CONTRACT_FILES, 0), else_=1), IngestJob.id
            ).limit(1)
            job = session.scalar(query)
            if job is None:
                return None
            job.status = JobStatus.RUNNING
            job.attempts += 1
            return job.id

    def _process(self, job_id: int, stats: RunStats) -> None:
        try:
            with self.session_factory.begin() as session:
                job = session.get(IngestJob, job_id)
                if job.kind == LIST_WINDOW:
                    self._process_list_page(session, job, stats)
                elif job.kind == CONTRACT_FILES:
                    self._process_contract_files(session, job, stats)
                else:
                    raise ValueError(f"Tipo de tarefa desconhecido: {job.kind}")
        except (ExternalServiceError, OSError, ValueError, KeyError) as exc:
            stats.failures += 1
            logger.warning("Tarefa %s falhou: %s", job_id, exc)
            self._mark_failure(job_id, exc)

    def _mark_failure(self, job_id: int, exc: Exception) -> None:
        with self.session_factory.begin() as session:
            job = session.get(IngestJob, job_id)
            job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
            if job.attempts >= self.max_attempts:
                job.status = JobStatus.FAILED
                if job.kind == CONTRACT_FILES:
                    contract = session.get(Contract, job.payload["contract_id"])
                    if contract is not None:
                        contract.download_status = DownloadStatus.FAILED
            else:
                job.status = JobStatus.PENDING

    def _process_list_page(self, session: Session, job: IngestJob, stats: RunStats) -> None:
        payload = dict(job.payload)
        page_number = int(payload["next_page"])
        page = self.client.list_contracts(
            date.fromisoformat(payload["start"]), date.fromisoformat(payload["end"]), page_number
        )
        stats.pages_listed += 1
        for item in page.items:
            stats.contracts_seen += 1
            uf = ((item.get("unidadeOrgao") or {}).get("ufSigla") or "").upper()
            if self.ufs is not None and uf not in self.ufs:
                continue
            tipo = ((item.get("tipoContrato") or {}).get("nome") or "").strip().lower()
            if self.contract_types is not None and tipo not in self.contract_types:
                continue
            columns = contract_columns(item)
            if session.get(Contract, columns["id"]) is None:
                session.add(Contract(**columns))
                stats.contracts_saved += 1
            self._enqueue_files(session, columns["id"])
        if page_number >= page.total_pages:
            job.status = JobStatus.DONE
        else:
            payload["next_page"] = page_number + 1
            job.payload = payload
            job.status = JobStatus.PENDING
            job.attempts = 0
        job.last_error = None

    def _enqueue_files(self, session: Session, contract_id: str) -> None:
        key = f"{CONTRACT_FILES}:{contract_id}"
        if session.scalar(select(IngestJob.id).where(IngestJob.key == key)) is None:
            session.add(
                IngestJob(kind=CONTRACT_FILES, key=key, payload={"contract_id": contract_id})
            )
            session.flush()

    def _process_contract_files(self, session: Session, job: IngestJob, stats: RunStats) -> None:
        contract = session.get(Contract, job.payload["contract_id"])
        if contract is None:
            raise KeyError(f"Contrato {job.payload['contract_id']} não está no banco")
        files = [
            f
            for f in self.client.list_files(contract.orgao_cnpj, contract.ano, contract.sequencial)
            if f.is_contract
        ]
        if not files:
            contract.download_status = DownloadStatus.NO_CONTRACT_DOCUMENT
            stats.contracts_without_document += 1
        for info in files:
            existing = session.scalar(
                select(Document).where(
                    Document.contract_id == contract.id,
                    Document.sequencial_documento == info.sequencial_documento,
                )
            )
            if existing is not None and Path(existing.local_path).exists():
                stats.documents_skipped += 1
                continue
            destination = (
                self.pdf_dir
                / contract.orgao_cnpj
                / str(contract.ano)
                / f"{contract.sequencial}_{info.sequencial_documento}.pdf"
            )
            result = self.client.download(info.url, destination)
            if not result.is_pdf:
                logger.warning("Arquivo de %s não começa com %%PDF: %s", contract.id, info.url)
            document = existing or Document(
                contract_id=contract.id, sequencial_documento=info.sequencial_documento
            )
            document.titulo = info.titulo
            document.tipo_documento = info.tipo_documento
            document.url = info.url
            document.local_path = str(result.path)
            document.sha256 = result.sha256
            document.size_bytes = result.size_bytes
            session.add(document)
            stats.documents_downloaded += 1
        if files:
            contract.download_status = DownloadStatus.DOWNLOADED
        job.status = JobStatus.DONE
        job.last_error = None

"""Estatísticas da coleta, lidas do banco e dos arquivos (só números agregados)."""

import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from contratolens.db.models import Contract, Document, DownloadStatus, IngestJob


def _counter(session: Session, column, *where) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count()).where(*where).group_by(column).order_by(func.count().desc())
    ).all()
    return {str(key) if key is not None else "?": count for key, count in rows}


def collection_stats(session_factory: sessionmaker[Session]) -> dict[str, Any]:
    """Calcula os números da coleta: contratos, cobertura de PDF, tamanhos, fila e distribuição."""
    with session_factory() as session:
        by_status = _counter(session, Contract.download_status)
        downloaded = Contract.download_status == DownloadStatus.DOWNLOADED
        documents = session.execute(select(Document.local_path, Document.size_bytes)).all()
        jobs = session.execute(
            select(IngestJob.kind, IngestJob.status, func.count()).group_by(
                IngestJob.kind, IngestJob.status
            )
        ).all()
        stats: dict[str, Any] = {
            "contratos_no_banco": sum(by_status.values()),
            "contratos_por_status": by_status,
            "baixados_por_uf": _counter(session, Contract.uf, downloaded),
            "baixados_por_esfera": _counter(session, Contract.esfera, downloaded),
            "baixados_por_tipo": _counter(session, Contract.tipo_contrato, downloaded),
            "tarefas": {f"{kind}:{status}": count for kind, status, count in jobs},
        }

    with_pdf = by_status.get(DownloadStatus.DOWNLOADED, 0)
    without_pdf = by_status.get(DownloadStatus.NO_CONTRACT_DOCUMENT, 0)
    checked = with_pdf + without_pdf
    stats["cobertura_pdf_contrato"] = round(with_pdf / checked, 4) if checked else None

    sizes = [size for _, size in documents]
    headers = Counter()
    for path, _ in documents:
        file = Path(path)
        if not file.exists():
            headers["arquivo_ausente"] += 1
            continue
        with file.open("rb") as handle:
            headers["pdf" if handle.read(5) == b"%PDF-" else "nao_pdf"] += 1
    stats["documentos"] = {
        "total": len(documents),
        "tamanho_total_gb": round(sum(sizes) / 1e9, 3),
        "tamanho_medio_mb": round(statistics.mean(sizes) / 1e6, 2) if sizes else None,
        "tamanho_mediano_mb": round(statistics.median(sizes) / 1e6, 2) if sizes else None,
        "por_cabecalho": dict(headers),
    }
    return stats

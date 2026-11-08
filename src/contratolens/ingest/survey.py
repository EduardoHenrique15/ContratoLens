"""Levantamento do recorte só com metadados (sem baixar PDFs), para escolher período e estados."""

import logging
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from contratolens.core.errors import ExternalServiceError
from contratolens.ingest.pncp_client import PNCPClient

logger = logging.getLogger(__name__)


@dataclass
class Survey:
    """Contagens do levantamento."""

    total_records: int = 0
    pages_read: int = 0
    by_uf: Counter = field(default_factory=Counter)
    by_esfera: Counter = field(default_factory=Counter)
    by_tipo_contrato: Counter = field(default_factory=Counter)
    sample: list[dict] = field(default_factory=list)


def survey_period(
    client: PNCPClient,
    start: date,
    end: date,
    *,
    max_pages: int | None = None,
    sample_size: int = 0,
    seed: int = 42,
) -> Survey:
    """Lê as páginas da listagem e conta contratos por UF, esfera e tipo.

    Guarda uma amostra aleatória (reprodutível pela semente) para medir a cobertura de PDFs.
    """
    result = Survey()
    rng = random.Random(seed)
    seen = 0
    page = 1
    while True:
        listing = client.list_contracts(start, end, page)
        result.pages_read += 1
        result.total_records = listing.total_records
        for item in listing.items:
            seen += 1
            result.by_uf[(item.get("unidadeOrgao") or {}).get("ufSigla") or "?"] += 1
            result.by_esfera[(item.get("orgaoEntidade") or {}).get("esferaId") or "?"] += 1
            result.by_tipo_contrato[(item.get("tipoContrato") or {}).get("nome") or "?"] += 1
            if sample_size:
                if len(result.sample) < sample_size:
                    result.sample.append(item)
                else:
                    index = rng.randrange(seen)
                    if index < sample_size:
                        result.sample[index] = item
        if page >= listing.total_pages or (max_pages is not None and page >= max_pages):
            break
        page += 1
    return result


@dataclass
class Coverage:
    """Cobertura de PDFs numa amostra, no geral e por tipo de contrato."""

    overall: Counter = field(default_factory=Counter)
    by_tipo_contrato: dict[str, Counter] = field(default_factory=dict)
    latencies_seconds: list[float] = field(default_factory=list)

    def latency_summary(self) -> dict[str, float]:
        """Mediana e p95 do tempo da rota de arquivos (inclui novas tentativas)."""
        if not self.latencies_seconds:
            return {}
        ordered = sorted(self.latencies_seconds)
        p95 = ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]
        return {"p50": round(statistics.median(ordered), 1), "p95": round(p95, 1)}


def file_coverage(client: PNCPClient, sample: list[dict]) -> Coverage:
    """Conta, na amostra, quantos contratos têm arquivo do tipo "Contrato".

    Uma falha num contrato não interrompe o levantamento: ela é contada como "erro".
    """
    result = Coverage()
    for index, item in enumerate(sample, start=1):
        tipo = (item.get("tipoContrato") or {}).get("nome") or "?"
        start = time.perf_counter()
        try:
            files = client.list_files(
                item["orgaoEntidade"]["cnpj"],
                int(item["anoContrato"]),
                int(item["sequencialContrato"]),
            )
        except ExternalServiceError as exc:
            logger.warning(
                "Contrato %s ignorado na amostra: %s", item.get("numeroControlePNCP"), exc
            )
            outcome = "erro"
        else:
            if any(f.is_contract for f in files):
                outcome = "com_contrato"
            elif files:
                outcome = "so_outros_documentos"
            else:
                outcome = "sem_arquivo"
        result.latencies_seconds.append(time.perf_counter() - start)
        result.overall[outcome] += 1
        result.by_tipo_contrato.setdefault(tipo, Counter())[outcome] += 1
        logger.info("Amostra %s/%s: %s (%s)", index, len(sample), outcome, tipo)
    return result

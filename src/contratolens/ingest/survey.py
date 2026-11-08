"""Levantamento do recorte só com metadados (sem baixar PDFs), para escolher período e estados."""

import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from contratolens.ingest.pncp_client import PNCPClient


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


def file_coverage(client: PNCPClient, sample: list[dict]) -> Counter:
    """Conta, na amostra, quantos contratos têm arquivo do tipo "Contrato"."""
    counts: Counter = Counter()
    for item in sample:
        files = client.list_files(
            item["orgaoEntidade"]["cnpj"], int(item["anoContrato"]), int(item["sequencialContrato"])
        )
        if any(f.is_contract for f in files):
            counts["com_contrato"] += 1
        elif files:
            counts["so_outros_documentos"] += 1
        else:
            counts["sem_arquivo"] += 1
    return counts

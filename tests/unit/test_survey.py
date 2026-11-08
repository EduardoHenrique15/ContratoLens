from datetime import date

from contratolens.ingest.survey import file_coverage, survey_period
from tests.conftest import PDF_BYTES
from tests.fakes.fake_pncp import API, make_contract

DAY = date(2026, 10, 1)


def test_survey_counts_and_sample(client, fake_pncp):
    for seq in range(1, 8):
        fake_pncp.add_contract(make_contract("1", 2026, seq, DAY, uf="TO" if seq < 5 else "GO"))
    survey = survey_period(client, DAY, DAY, sample_size=3, seed=1)
    assert survey.total_records == 7
    assert survey.by_uf == {"TO": 4, "GO": 3}
    assert len(survey.sample) == 3
    again = survey_period(client, DAY, DAY, sample_size=3, seed=1)
    assert [c["sequencialContrato"] for c in again.sample] == [
        c["sequencialContrato"] for c in survey.sample
    ]


def test_coverage_counts_failures_without_stopping(client, fake_pncp):
    fake_pncp.add_contract(make_contract("1", 2026, 1, DAY), [("Contrato", PDF_BYTES)])
    fake_pncp.add_contract(make_contract("1", 2026, 2, DAY), [("Nota de Empenho", b"x")])
    fake_pncp.add_contract(make_contract("1", 2026, 3, DAY), [("Contrato", PDF_BYTES)])
    fake_pncp.failures[f"{API}/v1/orgaos/1/contratos/2026/3/arquivos"] = [503, 503, 503]
    sample = [make_contract("1", 2026, s, DAY) for s in (1, 2, 3)]
    coverage = file_coverage(client, sample)
    assert coverage.overall == {"com_contrato": 1, "so_outros_documentos": 1, "erro": 1}
    assert coverage.by_tipo_contrato["Contrato (termo inicial)"]["erro"] == 1
    assert set(coverage.latency_summary()) == {"p50", "p95"}

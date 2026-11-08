from datetime import date

import pytest

from contratolens.core.errors import ExternalServiceError
from tests.conftest import PDF_BYTES
from tests.fakes.fake_pncp import CONSULTA, make_contract

DAY = date(2026, 10, 1)


def test_list_contracts_paginates(client, fake_pncp):
    for seq in range(1, 6):
        fake_pncp.add_contract(make_contract("1", 2026, seq, DAY))
    page = client.list_contracts(DAY, DAY, page=2, page_size=2)
    assert page.total_records == 5
    assert page.total_pages == 3
    assert [c["sequencialContrato"] for c in page.items] == [3, 4]


def test_list_contracts_empty_period_returns_empty_page(client):
    page = client.list_contracts(DAY, DAY, page=1)
    assert page.items == [] and page.total_pages == 0


def test_rejects_page_size_above_limit(client):
    with pytest.raises(ValueError):
        client.list_contracts(DAY, DAY, page=1, page_size=501)


def test_retries_transient_errors(client, fake_pncp):
    fake_pncp.add_contract(make_contract("1", 2026, 1, DAY))
    fake_pncp.failures[f"{CONSULTA}/v1/contratos"] = [429, 503]
    page = client.list_contracts(DAY, DAY, page=1)
    assert page.total_records == 1
    assert len(fake_pncp.calls) == 3


def test_gives_up_after_max_attempts(client, fake_pncp):
    fake_pncp.failures[f"{CONSULTA}/v1/contratos"] = [500, 500, 500]
    with pytest.raises(ExternalServiceError) as error:
        client.list_contracts(DAY, DAY, page=1)
    assert error.value.status_code == 500


def test_does_not_retry_client_errors(client, fake_pncp):
    fake_pncp.failures[f"{CONSULTA}/v1/contratos"] = [400]
    with pytest.raises(ExternalServiceError):
        client.list_contracts(DAY, DAY, page=1)
    assert len(fake_pncp.calls) == 1


def test_list_files_and_download(client, fake_pncp, tmp_path):
    fake_pncp.add_contract(
        make_contract("1", 2026, 7, DAY), [("Nota de Empenho", b"x"), ("Contrato", PDF_BYTES)]
    )
    files = client.list_files("1", 2026, 7)
    assert [f.tipo_documento for f in files] == ["Nota de Empenho", "Contrato"]
    result = client.download(files[1].url, tmp_path / "a" / "c.pdf")
    assert result.path.read_bytes() == PDF_BYTES
    assert result.is_pdf and result.size_bytes == len(PDF_BYTES)
    assert len(result.sha256) == 64
    assert not (tmp_path / "a" / "c.pdf.part").exists()


def test_list_files_without_files_returns_empty(client):
    assert client.list_files("1", 2026, 99) == []


def test_sends_generic_user_agent(client, fake_pncp):
    client.list_files("9", 2026, 1)
    assert fake_pncp.user_agents == ["contratolens-testes"]

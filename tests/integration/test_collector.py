from datetime import date

import pytest
from sqlalchemy import func, select

from contratolens.db.models import Contract, Document, DownloadStatus, IngestJob, JobStatus
from contratolens.ingest.collector import Collector
from tests.conftest import PDF_BYTES
from tests.fakes.fake_pncp import API, make_contract

DAY1, DAY2 = date(2026, 10, 1), date(2026, 10, 2)


def count(session_factory, model, *where):
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model).where(*where))


def seed(fake, n=3, day=DAY1, uf="TO", start_seq=1):
    for seq in range(start_seq, start_seq + n):
        fake.add_contract(make_contract("1", 2026, seq, day, uf=uf), [("Contrato", PDF_BYTES)])


def make_collector(session_factory, client, tmp_path, **kwargs):
    return Collector(session_factory, client, tmp_path / "pdfs", **kwargs)


def test_collects_contracts_and_downloads_only_contract_documents(
    session_factory, client, fake_pncp, tmp_path
):
    seed(fake_pncp, n=2)
    fake_pncp.add_contract(make_contract("1", 2026, 3, DAY1), [("Nota de Empenho", b"x")])
    collector = make_collector(session_factory, client, tmp_path)
    collector.enqueue_period(DAY1, DAY2)
    stats = collector.run()

    assert stats.contracts_saved == 3
    assert stats.documents_downloaded == 2
    assert stats.contracts_without_document == 1
    assert count(session_factory, Document) == 2
    assert (
        count(
            session_factory,
            Contract,
            Contract.download_status == DownloadStatus.NO_CONTRACT_DOCUMENT,
        )
        == 1
    )
    assert (tmp_path / "pdfs" / "1" / "2026" / "1_1.pdf").read_bytes() == PDF_BYTES
    assert count(session_factory, IngestJob, IngestJob.status != JobStatus.DONE) == 0


def test_filters_by_uf(session_factory, client, fake_pncp, tmp_path):
    seed(fake_pncp, n=2, uf="TO")
    seed(fake_pncp, n=2, uf="SP", start_seq=10)
    collector = make_collector(session_factory, client, tmp_path, ufs={"to"})
    collector.enqueue_period(DAY1, DAY1)
    collector.run()
    with session_factory() as session:
        assert set(session.scalars(select(Contract.uf))) == {"TO"}


def test_enqueue_is_idempotent(session_factory, client, tmp_path):
    collector = make_collector(session_factory, client, tmp_path)
    assert collector.enqueue_period(DAY1, date(2026, 10, 7), window_days=3) == 3
    assert collector.enqueue_period(DAY1, date(2026, 10, 7), window_days=3) == 0


def test_second_run_does_not_download_again(session_factory, client, fake_pncp, tmp_path):
    seed(fake_pncp, n=2)
    collector = make_collector(session_factory, client, tmp_path)
    collector.enqueue_period(DAY1, DAY1)
    collector.run()
    downloads_before = sum("/arquivos/" in c for c in fake_pncp.calls)

    # Reenfileirar o mesmo período não cria tarefas novas nem baixa de novo.
    collector.enqueue_period(DAY1, DAY1)
    stats = collector.run()
    assert stats.jobs_processed == 0
    assert sum("/arquivos/" in c for c in fake_pncp.calls) == downloads_before


def test_resumes_after_crash(session_factory, client, fake_pncp, tmp_path, monkeypatch):
    seed(fake_pncp, n=4)
    collector = make_collector(session_factory, client, tmp_path)
    collector.enqueue_period(DAY1, DAY1)

    original = client.download
    calls = {"n": 0}

    def crash_on_third(url, destination):
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt("queda simulada")
        return original(url, destination)

    monkeypatch.setattr(client, "download", crash_on_third)
    with pytest.raises(KeyboardInterrupt):
        collector.run()
    assert count(session_factory, Document) == 2
    assert count(session_factory, IngestJob, IngestJob.status == JobStatus.RUNNING) == 1

    monkeypatch.setattr(client, "download", original)
    restarted = make_collector(session_factory, client, tmp_path)
    assert restarted.recover() == 1
    restarted.run()
    assert count(session_factory, Document) == 4
    assert count(session_factory, IngestJob, IngestJob.status != JobStatus.DONE) == 0


def test_resumes_listing_from_saved_page(session_factory, client, fake_pncp, tmp_path, monkeypatch):
    seed(fake_pncp, n=5)
    monkeypatch.setattr(
        client,
        "list_contracts",
        lambda s, e, p, page_size=2: type(client).list_contracts(client, s, e, p, page_size=2),
    )
    collector = make_collector(session_factory, client, tmp_path)
    collector.enqueue_period(DAY1, DAY1)
    collector.run(max_jobs=1)  # lê só a página 1
    with session_factory() as session:
        job = session.scalar(select(IngestJob).where(IngestJob.kind == "list_window"))
        assert job.payload["next_page"] == 2 and job.status == JobStatus.PENDING
    collector.run()
    assert count(session_factory, Contract) == 5


def test_transient_failure_is_retried_on_next_job_attempt(
    session_factory, client, fake_pncp, tmp_path
):
    seed(fake_pncp, n=1)
    files_url = f"{API}/v1/orgaos/1/contratos/2026/1/arquivos"
    # 3 falhas esgotam as tentativas do cliente; a tarefa volta para a fila e passa depois.
    fake_pncp.failures[files_url] = [503, 503, 503]
    collector = make_collector(session_factory, client, tmp_path, max_attempts=3)
    collector.enqueue_period(DAY1, DAY1)
    stats = collector.run()
    assert stats.failures == 1
    assert count(session_factory, Document) == 1


def test_marks_contract_failed_after_max_attempts(session_factory, client, fake_pncp, tmp_path):
    seed(fake_pncp, n=1)
    files_url = f"{API}/v1/orgaos/1/contratos/2026/1/arquivos"
    fake_pncp.failures[files_url] = [503] * 9
    collector = make_collector(session_factory, client, tmp_path, max_attempts=3)
    collector.enqueue_period(DAY1, DAY1)
    collector.run()
    with session_factory() as session:
        assert session.scalar(select(Contract.download_status)) == DownloadStatus.FAILED
        job = session.scalar(select(IngestJob).where(IngestJob.kind == "contract_files"))
        assert job.status == JobStatus.FAILED and "503" in job.last_error


def test_stops_at_target_downloads(session_factory, client, fake_pncp, tmp_path, monkeypatch):
    seed(fake_pncp, n=6)
    monkeypatch.setattr(
        client,
        "list_contracts",
        lambda s, e, p, page_size=2: type(client).list_contracts(client, s, e, p, page_size=2),
    )
    collector = make_collector(session_factory, client, tmp_path, target_downloads=3)
    collector.enqueue_period(DAY1, DAY1)
    collector.run()
    # A meta é conferida antes de cada tarefa: para ao chegar a 3. Ficam na fila 1 tarefa de
    # arquivos (página 2) e a listagem (página 3), para uma próxima execução.
    assert collector.downloaded_count() == 3
    assert count(session_factory, IngestJob, IngestJob.status == JobStatus.PENDING) == 2

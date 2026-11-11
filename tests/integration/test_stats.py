from datetime import date

from contratolens.ingest.collector import Collector
from contratolens.ingest.stats import collection_stats
from tests.conftest import PDF_BYTES
from tests.fakes.fake_pncp import make_contract

DAY = date(2026, 10, 1)


def test_collection_stats(session_factory, client, fake_pncp, tmp_path):
    for seq in (1, 2, 3):
        fake_pncp.add_contract(
            make_contract("1", 2026, seq, DAY, uf="TO" if seq < 3 else "GO"),
            [("Contrato", PDF_BYTES)],
        )
    fake_pncp.add_contract(make_contract("1", 2026, 4, DAY), [("Nota de Empenho", b"x")])
    collector = Collector(session_factory, client, tmp_path / "pdfs")
    collector.enqueue_period(DAY, DAY)
    collector.run()

    stats = collection_stats(session_factory)
    assert stats["contratos_no_banco"] == 4
    assert stats["contratos_por_status"] == {"downloaded": 3, "no_contract_document": 1}
    assert stats["cobertura_pdf_contrato"] == 0.75
    assert stats["baixados_por_uf"] == {"TO": 2, "GO": 1}
    assert stats["documentos"]["total"] == 3
    assert stats["documentos"]["por_cabecalho"] == {"pdf": 3}
    assert stats["tarefas"]["contract_files:done"] == 4

from datetime import date
from decimal import Decimal

from contratolens.core.masking import CPF_MASK
from contratolens.ingest.schemas import FileInfo, contract_columns
from tests.fakes.fake_pncp import make_contract


def test_contract_columns():
    item = make_contract("37344371000109", 2026, 115, date(2026, 10, 1), valor=71240.9)
    columns = contract_columns(item)
    assert columns["id"] == "37344371000109-2-000115/2026"
    assert columns["valor_global"] == Decimal("71240.9")
    assert columns["vigencia_fim"] == date(2027, 8, 14)
    assert columns["uf"] == "TO"
    assert columns["fornecedor_ni"] == "10855248000198"


def test_masks_cpf_of_individual_supplier_everywhere():
    item = make_contract("1", 2026, 1, date(2026, 10, 1), tipo_pessoa="PF", ni="52998224725")
    columns = contract_columns(item)
    assert columns["fornecedor_ni"] == CPF_MASK
    assert columns["raw"]["niFornecedor"] == CPF_MASK
    assert item["niFornecedor"] == "52998224725"  # o original não é alterado


def test_file_info_detects_contract_type():
    def build(kind):
        return FileInfo.from_api({"sequencialDocumento": 1, "url": "u", "tipoDocumentoNome": kind})

    assert build("Contrato").is_contract
    assert build(" contrato ").is_contract
    assert not build("Nota de Empenho").is_contract
    assert not build(None).is_contract

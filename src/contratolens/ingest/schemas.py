"""Leitura das respostas da API do PNCP e conversão para as colunas do banco."""

import copy
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from contratolens.core.masking import CPF_MASK

CONTRACT_DOCUMENT_TYPE = "contrato"


@dataclass(frozen=True)
class ContractPage:
    """Uma página da listagem de contratos."""

    items: list[dict[str, Any]]
    total_records: int
    total_pages: int
    page: int


@dataclass(frozen=True)
class FileInfo:
    """Arquivo listado para um contrato."""

    sequencial_documento: int
    url: str
    titulo: str | None = None
    tipo_documento: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_contract(self) -> bool:
        """Verdadeiro quando o arquivo é o instrumento contratual (não nota de empenho etc.)."""
        return (self.tipo_documento or "").strip().lower() == CONTRACT_DOCUMENT_TYPE

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "FileInfo":
        """Cria a partir de um item da rota de arquivos."""
        return cls(
            sequencial_documento=int(item["sequencialDocumento"]),
            url=item["url"],
            titulo=item.get("titulo"),
            tipo_documento=item.get("tipoDocumentoNome"),
            extra=item,
        )


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _decimal(value: Any) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def sanitize_contract(item: dict[str, Any]) -> dict[str, Any]:
    """Remove o CPF de fornecedor pessoa física antes de guardar o registro.

    O CPF não é usado pelo projeto; guardá-lo mascarado segue o princípio de minimização de dados.
    """
    clean = copy.deepcopy(item)
    for kind_key, ni_key in (
        ("tipoPessoa", "niFornecedor"),
        ("tipoPessoaSubContratada", "niFornecedorSubContratado"),
    ):
        if clean.get(kind_key) == "PF" and clean.get(ni_key):
            clean[ni_key] = CPF_MASK
    return clean


def contract_columns(item: dict[str, Any]) -> dict[str, Any]:
    """Converte um item da listagem de contratos nas colunas da tabela contracts."""
    clean = sanitize_contract(item)
    orgao = clean.get("orgaoEntidade") or {}
    unidade = clean.get("unidadeOrgao") or {}
    return {
        "id": clean["numeroControlePNCP"],
        "orgao_cnpj": orgao["cnpj"],
        "ano": int(clean["anoContrato"]),
        "sequencial": int(clean["sequencialContrato"]),
        "orgao_nome": orgao.get("razaoSocial"),
        "esfera": orgao.get("esferaId"),
        "unidade_nome": unidade.get("nomeUnidade"),
        "uf": unidade.get("ufSigla"),
        "municipio": unidade.get("municipioNome"),
        "tipo_pessoa": clean.get("tipoPessoa"),
        "fornecedor_ni": clean.get("niFornecedor"),
        "fornecedor_nome": clean.get("nomeRazaoSocialFornecedor"),
        "objeto": clean.get("objetoContrato"),
        "valor_inicial": _decimal(clean.get("valorInicial")),
        "valor_global": _decimal(clean.get("valorGlobal")),
        "data_assinatura": _date(clean.get("dataAssinatura")),
        "vigencia_inicio": _date(clean.get("dataVigenciaInicio")),
        "vigencia_fim": _date(clean.get("dataVigenciaFim")),
        "tipo_contrato": (clean.get("tipoContrato") or {}).get("nome"),
        "categoria_processo": (clean.get("categoriaProcesso") or {}).get("nome"),
        "numero_contrato": clean.get("numeroContratoEmpenho"),
        "data_publicacao_pncp": _datetime(clean.get("dataPublicacaoPncp")),
        "raw": clean,
    }

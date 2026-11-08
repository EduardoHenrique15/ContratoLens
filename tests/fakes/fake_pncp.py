"""PNCP falso para os testes: responde às rotas de listagem, arquivos e download via respx."""

import re
from dataclasses import dataclass, field
from datetime import date

import httpx
import respx

CONSULTA = "https://pncp.test/api/consulta"
API = "https://pncp.test/api/pncp"


def make_contract(
    cnpj: str,
    year: int,
    seq: int,
    published: date,
    *,
    uf: str = "TO",
    tipo_pessoa: str = "PJ",
    ni: str = "10855248000198",
    valor: float = 1000.0,
) -> dict:
    """Cria um item no formato da listagem de contratos do PNCP."""
    return {
        "numeroControlePNCP": f"{cnpj}-2-{seq:06d}/{year}",
        "orgaoEntidade": {"cnpj": cnpj, "razaoSocial": "MUNICIPIO TESTE", "esferaId": "M"},
        "unidadeOrgao": {"ufSigla": uf, "nomeUnidade": "PREFEITURA", "municipioNome": "Teste"},
        "anoContrato": year,
        "sequencialContrato": seq,
        "tipoPessoa": tipo_pessoa,
        "niFornecedor": ni,
        "nomeRazaoSocialFornecedor": "EMPRESA TESTE LTDA",
        "objetoContrato": "Aquisição de materiais",
        "valorInicial": valor,
        "valorGlobal": valor,
        "dataAssinatura": "2026-08-14",
        "dataVigenciaInicio": "2026-08-14",
        "dataVigenciaFim": "2027-08-14",
        "tipoContrato": {"id": 1, "nome": "Contrato (termo inicial)"},
        "categoriaProcesso": {"id": 2, "nome": "Compras"},
        "numeroContratoEmpenho": str(seq),
        "dataPublicacaoPncp": f"{published.isoformat()}T10:00:00",
    }


@dataclass
class FakePNCP:
    """Estado do PNCP falso. `failures` guarda status a devolver antes do sucesso, por URL."""

    contracts: list[dict] = field(default_factory=list)
    files: dict[str, list[dict]] = field(default_factory=dict)
    blobs: dict[str, bytes] = field(default_factory=dict)
    failures: dict[str, list[int | tuple[int, dict]]] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    user_agents: list[str] = field(default_factory=list)

    def add_contract(self, item: dict, documents: list[tuple[str, bytes]] | None = None) -> None:
        """Adiciona um contrato e seus arquivos [(tipoDocumentoNome, conteúdo)]."""
        self.contracts.append(item)
        cnpj, year, seq = (
            item["orgaoEntidade"]["cnpj"],
            item["anoContrato"],
            item["sequencialContrato"],
        )
        entries = []
        for index, (kind, content) in enumerate(documents or [], start=1):
            url = f"{API}/v1/orgaos/{cnpj}/contratos/{year}/{seq}/arquivos/{index}"
            entries.append(
                {
                    "url": url,
                    "sequencialDocumento": index,
                    "titulo": f"DOC {index}",
                    "tipoDocumentoNome": kind,
                }
            )
            self.blobs[url] = content
        self.files[f"{cnpj}/{year}/{seq}"] = entries

    def _fail(self, url: str) -> httpx.Response | None:
        queue = self.failures.get(url)
        if not queue:
            return None
        failure = queue.pop(0)
        status, headers = failure if isinstance(failure, tuple) else (failure, {})
        return httpx.Response(status, headers=headers)

    def _list(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(str(request.url))
        if (failure := self._fail(f"{CONSULTA}/v1/contratos")) is not None:
            return failure
        params = request.url.params
        start = date.fromisoformat(_iso(params["dataInicial"]))
        end = date.fromisoformat(_iso(params["dataFinal"]))
        page, size = int(params["pagina"]), int(params["tamanhoPagina"])
        if size > 500:
            return httpx.Response(400)
        selected = [
            c
            for c in self.contracts
            if start <= date.fromisoformat(c["dataPublicacaoPncp"][:10]) <= end
        ]
        if not selected:
            return httpx.Response(204)
        total_pages = -(-len(selected) // size)
        chunk = selected[(page - 1) * size : page * size]
        return httpx.Response(
            200,
            json={
                "data": chunk,
                "totalRegistros": len(selected),
                "totalPaginas": total_pages,
                "numeroPagina": page,
            },
        )

    def _files(self, request: httpx.Request, cnpj: str, year: str, seq: str) -> httpx.Response:
        self.calls.append(str(request.url))
        self.user_agents.append(request.headers.get("User-Agent", ""))
        if (failure := self._fail(str(request.url))) is not None:
            return failure
        entries = self.files.get(f"{cnpj}/{year}/{seq}")
        if not entries:
            return httpx.Response(404)
        return httpx.Response(200, json=entries)

    def _download(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(str(request.url))
        if (failure := self._fail(str(request.url))) is not None:
            return failure
        return httpx.Response(200, content=self.blobs[str(request.url)])

    def install(self, router: respx.Router) -> None:
        """Registra as rotas no router do respx."""
        router.get(f"{CONSULTA}/v1/contratos").mock(side_effect=self._list)
        router.get(
            url__regex=rf"^{re.escape(API)}/v1/orgaos/\d+/contratos/\d+/\d+/arquivos/\d+$"
        ).mock(side_effect=self._download)
        router.get(
            url__regex=rf"^{re.escape(API)}/v1/orgaos/(?P<cnpj>\d+)/contratos/(?P<year>\d+)/(?P<seq>\d+)/arquivos$"
        ).mock(side_effect=self._files)


def _iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"

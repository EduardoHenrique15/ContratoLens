"""Cliente da API pública do PNCP, com limite de taxa e novas tentativas para erros transitórios."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential
from tenacity.wait import wait_base

from contratolens.core.errors import ExternalServiceError
from contratolens.ingest.rate_limit import MinIntervalLimiter
from contratolens.ingest.schemas import ContractPage, FileInfo

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 500
TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ExternalServiceError) and exc.transient


@dataclass(frozen=True)
class DownloadResult:
    """Resultado de um download."""

    path: Path
    sha256: str
    size_bytes: int
    is_pdf: bool


class PNCPClient:
    """Acesso às rotas de consulta de contratos e de arquivos do PNCP."""

    def __init__(
        self,
        *,
        consulta_base_url: str,
        api_base_url: str,
        user_agent: str,
        limiter: MinIntervalLimiter,
        timeout: float = 60.0,
        max_attempts: int = 5,
        wait: wait_base | None = None,
        http: httpx.Client | None = None,
    ):
        self.consulta_base_url = consulta_base_url.rstrip("/")
        self.api_base_url = api_base_url.rstrip("/")
        self.limiter = limiter
        self.http = http or httpx.Client(
            timeout=timeout, headers={"User-Agent": user_agent}, follow_redirects=True
        )
        self._retrying = Retrying(
            retry=retry_if_exception(_is_transient),
            stop=stop_after_attempt(max_attempts),
            wait=wait if wait is not None else wait_exponential(multiplier=2, min=2, max=60),
            reraise=True,
        )

    def close(self) -> None:
        """Fecha a conexão HTTP."""
        self.http.close()

    def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        return self._retrying(self._get_once, url, params)

    def _get_once(self, url: str, params: dict[str, Any] | None) -> httpx.Response:
        self.limiter.wait()
        try:
            response = self.http.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning("Falha de rede em %s: %s", url, exc)
            raise ExternalServiceError(f"Falha de rede: {exc}", transient=True) from exc
        if response.status_code in TRANSIENT_STATUS:
            logger.warning("Status %s transitório em %s", response.status_code, url)
            raise ExternalServiceError(
                f"Status {response.status_code} em {url}",
                status_code=response.status_code,
                transient=True,
            )
        return response

    def list_contracts(
        self, start: date, end: date, page: int, page_size: int = MAX_PAGE_SIZE
    ) -> ContractPage:
        """Lista contratos publicados entre `start` e `end` (inclusive)."""
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size precisa estar entre 1 e {MAX_PAGE_SIZE}.")
        response = self._get(
            f"{self.consulta_base_url}/v1/contratos",
            params={
                "dataInicial": start.strftime("%Y%m%d"),
                "dataFinal": end.strftime("%Y%m%d"),
                "pagina": page,
                "tamanhoPagina": page_size,
            },
        )
        if response.status_code == 204:
            return ContractPage(items=[], total_records=0, total_pages=0, page=page)
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Status {response.status_code} na listagem de contratos",
                status_code=response.status_code,
            )
        body = response.json()
        return ContractPage(
            items=body.get("data") or [],
            total_records=int(body.get("totalRegistros") or 0),
            total_pages=int(body.get("totalPaginas") or 0),
            page=int(body.get("numeroPagina") or page),
        )

    def list_files(self, cnpj: str, year: int, sequential: int) -> list[FileInfo]:
        """Lista os arquivos de um contrato. Devolve lista vazia se não houver nenhum."""
        response = self._get(
            f"{self.api_base_url}/v1/orgaos/{cnpj}/contratos/{year}/{sequential}/arquivos"
        )
        if response.status_code in (204, 404):
            return []
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Status {response.status_code} ao listar arquivos",
                status_code=response.status_code,
            )
        body = response.json()
        items = body if isinstance(body, list) else [body]
        return [FileInfo.from_api(item) for item in items if item]

    def download(self, url: str, destination: Path) -> DownloadResult:
        """Baixa um arquivo para `destination`, de forma atômica, e calcula o SHA-256."""
        response = self._get(url)
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Status {response.status_code} ao baixar {url}",
                status_code=response.status_code,
            )
        content = response.content
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.write_bytes(content)
        temporary.replace(destination)
        return DownloadResult(
            path=destination,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            is_pdf=content.startswith(b"%PDF"),
        )

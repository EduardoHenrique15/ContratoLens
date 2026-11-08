"""Funções compartilhadas pelos scripts de linha de comando."""

from datetime import date

from contratolens.core.config import Settings
from contratolens.ingest.pncp_client import PNCPClient
from contratolens.ingest.rate_limit import MinIntervalLimiter


def parse_date(value: str) -> date:
    """Lê uma data no formato AAAA-MM-DD."""
    return date.fromisoformat(value)


def make_client(settings: Settings) -> PNCPClient:
    """Cria o cliente do PNCP com os limites da configuração."""
    return PNCPClient(
        consulta_base_url=settings.pncp_consulta_base_url,
        api_base_url=settings.pncp_api_base_url,
        user_agent=settings.pncp_user_agent,
        limiter=MinIntervalLimiter(settings.pncp_min_interval_seconds),
        timeout=settings.pncp_timeout_seconds,
        max_attempts=settings.pncp_max_attempts,
    )


def confirm(question: str) -> bool:
    """Pergunta sim/não no terminal. Só 's' confirma."""
    return input(f"{question} (s/N) ").strip().lower() == "s"

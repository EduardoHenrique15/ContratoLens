"""Configuração de logs com correlation id por execução."""

import logging
import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        return True


def new_correlation_id() -> str:
    """Gera e ativa um novo correlation id para a execução atual."""
    value = uuid.uuid4().hex[:12]
    correlation_id.set(value)
    return value


def setup_logging(level: str = "INFO") -> None:
    """Configura o log raiz com data, nível, correlation id e mensagem."""
    handler = logging.StreamHandler()
    handler.addFilter(_CorrelationFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

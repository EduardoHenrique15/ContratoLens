"""Erros do domínio do ContratoLens."""


class ContratoLensError(Exception):
    """Erro base do projeto."""


class ExternalServiceError(ContratoLensError):
    """Falha ao chamar um serviço externo (PNCP, provedor de LLM)."""

    def __init__(self, message: str, *, status_code: int | None = None, transient: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.transient = transient


class BudgetExceededError(ContratoLensError):
    """O orçamento diário de LLM foi atingido."""

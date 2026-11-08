"""Configuração do ContratoLens, lida de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação. Segredos usam SecretStr para não aparecerem em logs."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://contratolens:contratolens@localhost:5432/contratolens"
    data_dir: Path = Path("data")
    log_level: str = "INFO"

    pncp_consulta_base_url: str = "https://pncp.gov.br/api/consulta"
    pncp_api_base_url: str = "https://pncp.gov.br/api/pncp"
    pncp_user_agent: str = (
        "contratolens/0.1 (projeto de portfolio; github.com/EduardoHenrique15/contratolens)"
    )
    pncp_min_interval_seconds: float = 1.0
    pncp_timeout_seconds: float = 60.0
    pncp_max_attempts: int = 5

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"

    @property
    def pdf_dir(self) -> Path:
        """Pasta onde os PDFs baixados são guardados."""
        return self.data_dir / "pdfs"


@lru_cache
def get_settings() -> Settings:
    """Devolve a configuração (lida uma vez por processo)."""
    return Settings()

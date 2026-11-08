from pathlib import Path

from contratolens.core.config import Settings


def test_reads_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # garante que nenhum .env real seja lido
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "dados"))
    monkeypatch.setenv("PNCP_MIN_INTERVAL_SECONDS", "2.5")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-falsa")
    settings = Settings()
    assert settings.data_dir == tmp_path / "dados"
    assert settings.pdf_dir == tmp_path / "dados" / "pdfs"
    assert settings.pncp_min_interval_seconds == 2.5
    assert "chave-falsa" not in repr(settings)
    assert settings.gemini_api_key.get_secret_value() == "chave-falsa"


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("DATA_DIR", "DATABASE_URL", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    assert settings.data_dir == Path("data")
    assert settings.gemini_api_key is None
    assert "@" not in settings.pncp_user_agent  # identificação genérica, sem e-mail

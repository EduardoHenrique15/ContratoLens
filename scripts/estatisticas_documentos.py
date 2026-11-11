"""Números da leitura de documentos (Fase 2), salvos em eval/results/documentos_<data>.json.

Uso (PowerShell, com o .venv ativado):
    python scripts\\estatisticas_documentos.py
"""

import json
import sys
from datetime import date
from pathlib import Path

from contratolens.core.config import get_settings
from contratolens.db.session import make_engine, make_session_factory
from contratolens.documents.stats import reading_stats


def main() -> int:
    """Calcula, mostra e salva as estatísticas."""
    settings = get_settings()
    stats = reading_stats(make_session_factory(make_engine(settings.database_url)))
    stats["gerado_em"] = date.today().isoformat()
    output = Path("eval/results") / f"documentos_{date.today():%Y%m%d}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"\nSalvo em {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

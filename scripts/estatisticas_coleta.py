"""Números da coleta (Fase 1), calculados do banco e dos PDFs baixados.

Salva o resultado em eval/results/coleta_<data>.json (só números agregados, sem dados pessoais),
para que todo número citado na documentação seja reproduzível.

Uso (PowerShell, com o .venv ativado):
    python scripts\\estatisticas_coleta.py
"""

import json
import sys
from datetime import date
from pathlib import Path

from contratolens.core.config import get_settings
from contratolens.db.session import make_engine, make_session_factory
from contratolens.ingest.stats import collection_stats


def main() -> int:
    """Calcula, mostra e salva as estatísticas."""
    settings = get_settings()
    session_factory = make_session_factory(make_engine(settings.database_url))
    stats = collection_stats(session_factory)
    stats["gerado_em"] = date.today().isoformat()

    output = Path("eval/results") / f"coleta_{date.today():%Y%m%d}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"\nSalvo em {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

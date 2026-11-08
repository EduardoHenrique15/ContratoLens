"""Levantamento do recorte só com metadados: conta contratos por UF, esfera e tipo, sem baixar PDFs.

Opcionalmente mede, numa amostra aleatória (semente fixa), quantos contratos têm arquivo do tipo
"Contrato". O resultado é salvo em JSON na pasta de dados (fora do git).

Uso (PowerShell, com o .venv ativado):
    python scripts\\levantar_recorte.py --inicio 2026-10-01 --fim 2026-10-07 --amostra 100
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import confirm, make_client, parse_date  # noqa: E402

from contratolens.core.config import get_settings  # noqa: E402
from contratolens.core.logging import new_correlation_id, setup_logging  # noqa: E402
from contratolens.ingest.survey import file_coverage, survey_period  # noqa: E402


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt(pairs) -> str:
    return ", ".join(f"{k}={v}" for k, v in pairs)


def main() -> int:
    """Executa o levantamento e mostra o resumo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=parse_date, required=True, help="AAAA-MM-DD")
    parser.add_argument("--fim", type=parse_date, required=True, help="AAAA-MM-DD")
    parser.add_argument("--amostra", type=int, default=0, help="contratos para medir cobertura")
    parser.add_argument("--max-paginas", type=int, default=None)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--sim", action="store_true", help="não pedir confirmação")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    new_correlation_id()
    client = make_client(settings)
    try:
        first = client.list_contracts(args.inicio, args.fim, 1)
        pages = (
            first.total_pages
            if args.max_paginas is None
            else min(first.total_pages, args.max_paginas)
        )
        calls = pages + args.amostra
        # A listagem leva ~2 s por página; a rota de arquivos levou de 10 a 60 s por contrato.
        minutes = math.ceil(
            (pages * settings.pncp_min_interval_seconds * 1.5 + args.amostra * 30) / 60
        )
        print(f"Registros no período: {first.total_records} em {first.total_pages} páginas de 500.")
        print(
            f"Estimativa: {calls} chamadas ao PNCP, cerca de {minutes} min. Nenhum PDF é baixado."
        )
        if not args.sim and not confirm("Continuar?"):
            return 1

        survey = survey_period(
            client,
            args.inicio,
            args.fim,
            max_pages=args.max_paginas,
            sample_size=args.amostra,
            seed=args.semente,
        )
        result = {
            "inicio": args.inicio.isoformat(),
            "fim": args.fim.isoformat(),
            "semente": args.semente,
            "registros": survey.total_records,
            "paginas_lidas": survey.pages_read,
            "por_uf": dict(survey.by_uf.most_common()),
            "por_esfera": dict(survey.by_esfera.most_common()),
            "por_tipo_contrato": dict(survey.by_tipo_contrato.most_common()),
            "amostra": len(survey.sample),
        }
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        output = settings.data_dir / f"levantamento_{args.inicio:%Y%m%d}_{args.fim:%Y%m%d}.json"
        _save(output, result)  # salva a listagem antes da amostra, que é a parte lenta

        print(f"\nRegistros: {survey.total_records} (páginas lidas: {survey.pages_read})")
        print("UFs com mais registros:", _fmt(survey.by_uf.most_common(10)))
        print("Esferas:", _fmt(survey.by_esfera.most_common()))
        print("Tipos de contrato:", _fmt(survey.by_tipo_contrato.most_common(8)))

        if args.amostra:
            print(
                f"\nMedindo a cobertura de PDFs em {len(survey.sample)} contratos (rota lenta)..."
            )
            coverage = file_coverage(client, survey.sample)
            result["cobertura_amostra"] = dict(coverage.overall)
            result["cobertura_por_tipo"] = {
                k: dict(v) for k, v in coverage.by_tipo_contrato.items()
            }
            result["latencia_arquivos_s"] = coverage.latency_summary()
            _save(output, result)
            print("Cobertura na amostra:", _fmt(coverage.overall.items()))
            for tipo, counts in coverage.by_tipo_contrato.items():
                print(f"  {tipo}: {_fmt(counts.items())}")
            print("Tempo da rota de arquivos (s):", coverage.latency_summary())
    finally:
        client.close()

    print(f"Resultado salvo em {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

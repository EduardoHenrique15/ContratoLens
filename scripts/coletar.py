"""Coleta do recorte: lista contratos do PNCP, filtra por UF e baixa os PDFs do tipo "Contrato".

A coleta usa a fila do banco: pode ser interrompida (Ctrl+C, queda de energia) e retomada rodando o
mesmo comando de novo. Antes de começar, mostra a estimativa de chamadas, tempo e disco.

Uso (PowerShell, com o .venv ativado):
    python scripts\\coletar.py --inicio 2026-05-01 --fim 2026-10-31 --ufs TO,GO --meta 3000
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import confirm, make_client, parse_date  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from contratolens.core.config import get_settings  # noqa: E402
from contratolens.core.logging import new_correlation_id, setup_logging  # noqa: E402
from contratolens.db.models import Contract, Document  # noqa: E402
from contratolens.db.session import make_engine, make_session_factory  # noqa: E402
from contratolens.ingest.collector import Collector  # noqa: E402


def estimate(meta: int, coverage: float, avg_mb: float, interval: float) -> tuple[int, int, float]:
    """Estima chamadas, minutos e gigabytes para baixar `meta` contratos."""
    contracts_to_check = math.ceil(meta / coverage)
    calls = contracts_to_check + meta  # 1 listagem de arquivos por contrato + 1 download por PDF
    # No levantamento de 2026-11-08, a rota de arquivos teve mediana de 51 s por contrato.
    minutes = math.ceil((contracts_to_check * 51 + meta * max(interval, 5)) / 60)
    return calls, minutes, meta * avg_mb / 1024


def main() -> int:
    """Executa (ou retoma) a coleta."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=parse_date, required=True, help="AAAA-MM-DD")
    parser.add_argument("--fim", type=parse_date, required=True, help="AAAA-MM-DD")
    parser.add_argument("--ufs", default="", help="siglas separadas por vírgula; vazio = todas")
    parser.add_argument("--meta", type=int, required=True, help="contratos com PDF a baixar")
    parser.add_argument(
        "--tipos",
        default="",
        help='tipos de contrato separados por ";" (ex.: "Contrato (termo inicial)"); vazio = todos',
    )
    parser.add_argument("--janela-dias", type=int, default=1)
    parser.add_argument("--cobertura", type=float, default=0.8, help="fração com PDF de contrato")
    parser.add_argument("--semente", type=int, default=42, help="ordem aleatória dos downloads")
    parser.add_argument(
        "--refazer-falhas", action="store_true", help="devolve à fila as tarefas que falharam"
    )
    parser.add_argument("--tamanho-medio-mb", type=float, default=4.6)
    parser.add_argument("--sim", action="store_true", help="não pedir confirmação")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    new_correlation_id()
    ufs = {uf.strip().upper() for uf in args.ufs.split(",") if uf.strip()} or None
    tipos = {t.strip() for t in args.tipos.split(";") if t.strip()} or None

    calls, minutes, gigabytes = estimate(
        args.meta, args.cobertura, args.tamanho_medio_mb, settings.pncp_min_interval_seconds
    )
    print(f"Período: {args.inicio} a {args.fim}; UFs: {', '.join(sorted(ufs)) if ufs else 'todas'}")
    print(f"Tipos: {'; '.join(sorted(tipos)) if tipos else 'todos'}")
    print(f"Meta: {args.meta} contratos com PDF; pasta: {settings.pdf_dir}")
    print(
        f"Estimativa: ~{calls} chamadas aos arquivos (mais a listagem), ~{minutes / 60:.0f} h, "
        f"~{gigabytes:.1f} GB em disco. Pode ser interrompida e retomada."
    )
    if not args.sim and not confirm("Começar ou retomar a coleta?"):
        return 1

    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    client = make_client(settings)
    collector = Collector(
        session_factory,
        client,
        settings.pdf_dir,
        ufs=ufs,
        contract_types=tipos,
        target_downloads=args.meta,
        list_first=True,
        seed=args.semente,
    )
    try:
        recovered = collector.recover()
        if recovered:
            print(f"Retomando: {recovered} tarefa(s) interrompida(s) voltaram para a fila.")
        if args.refazer_falhas:
            print(f"Refazendo falhas: {collector.retry_failed()} tarefa(s) voltaram para a fila.")
        collector.enqueue_period(args.inicio, args.fim, window_days=args.janela_dias)
        stats = collector.run()
    finally:
        client.close()

    with session_factory() as session:
        contracts = session.scalar(select(func.count()).select_from(Contract))
        documents = session.scalar(select(func.count()).select_from(Document))
        total_bytes = session.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0)))
    print(f"\nNesta execução: {stats}")
    print(f"No banco: {contracts} contratos, {documents} documentos, {total_bytes / 1e9:.2f} GB.")
    print(f"Contratos com PDF baixado: {collector.downloaded_count()} (meta {args.meta}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

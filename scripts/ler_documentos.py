"""Leitura em lote dos documentos baixados: texto com coordenadas e OCR só nas páginas escaneadas.

Roda em vários processos (um por núcleo). Pode ser interrompida com Ctrl+C e retomada com o mesmo
comando: documentos já lidos são pulados.

Uso (PowerShell, com o .venv ativado):
    python scripts\\ler_documentos.py --processos 4
"""

import argparse
import math
import os
import sys

from contratolens.core.config import get_settings
from contratolens.core.logging import new_correlation_id, setup_logging
from contratolens.db.session import make_engine, make_session_factory
from contratolens.documents.processor import pending_documents, process_documents

# Medido na Fase 0: OCR a 300 dpi levou 3,35 s por página num núcleo do i7-1165G7.
OCR_SECONDS_PER_PAGE = 3.35
NATIVE_SECONDS_PER_PAGE = 0.15


def _duration(seconds: float) -> str:
    minutes = math.ceil(seconds / 60)
    return f"{minutes} min" if minutes < 90 else f"{minutes / 60:.1f} h"


def count_pages(paths: list[str]) -> tuple[int, int]:
    """Conta as páginas dos PDFs pendentes (rápido) e quantos arquivos não abriram como PDF."""
    import pypdfium2 as pdfium

    total, unreadable = 0, 0
    for path in paths:
        try:
            document = pdfium.PdfDocument(path)
        except Exception:  # noqa: BLE001 - só para a estimativa
            unreadable += 1
            continue
        total += len(document)
        document.close()
    return total, unreadable


def main() -> int:
    """Mostra a estimativa, pede confirmação e processa."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processos", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--limite", type=int, default=None, help="processa só N documentos")
    parser.add_argument("--refazer-erros", action="store_true")
    parser.add_argument("--reprocessar", action="store_true", help="lê tudo de novo")
    parser.add_argument("--sim", action="store_true", help="não pedir confirmação")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    new_correlation_id()
    session_factory = make_session_factory(make_engine(settings.database_url))
    documents = pending_documents(
        session_factory, retry_errors=args.refazer_erros, reprocess=args.reprocessar
    )
    if args.limite:
        documents = documents[: args.limite]
    if not documents:
        print("Nenhum documento pendente.")
        return 0

    pages, unreadable = count_pages([path for _, path in documents])
    workers = max(1, args.processos)
    best = pages * NATIVE_SECONDS_PER_PAGE / workers
    worst = pages * OCR_SECONDS_PER_PAGE / workers
    print(f"Documentos a ler: {len(documents)} ({pages} páginas; {unreadable} não abrem como PDF)")
    print(
        f"Estimativa com {workers} processo(s): de ~{_duration(best)} (tudo com texto nativo) "
        f"a ~{_duration(worst)} (tudo escaneado). Nada sai do computador."
    )
    if not args.sim and input("Começar ou retomar a leitura? (s/N) ").strip().lower() != "s":
        return 1

    stats = process_documents(session_factory, documents, workers=workers)
    print(
        f"\nLidos: {stats.done}; formato não tratado: {stats.unsupported}; erros: {stats.errors}; "
        f"páginas: {stats.pages} ({stats.ocr_pages} com OCR); trechos: {stats.chunks}."
    )
    print("Rode scripts\\estatisticas_documentos.py para os números completos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

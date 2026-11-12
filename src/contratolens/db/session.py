"""Criação do engine e das sessões do banco."""

import sys

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

DB_UNAVAILABLE_MESSAGE = """O banco de dados não respondeu ({detail}).

Como resolver:
  1. Abra o Docker Desktop e espere aparecer "Engine running".
  2. Rode: docker compose up -d db
  3. Confira com: docker compose ps   (o contratolens-db-1 deve estar "Up (healthy)")
  4. Rode este comando de novo. Nada foi perdido: os dados ficam no volume do Docker."""


def make_engine(database_url: str) -> Engine:
    """Cria o engine do SQLAlchemy para a URL informada."""
    connect_args = {"connect_timeout": 5} if database_url.startswith("postgresql") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Cria a fábrica de sessões ligada ao engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def connect_or_exit(database_url: str) -> Engine:
    """Cria o engine e confere a conexão; se o banco não responder, explica o que fazer e sai.

    Usado pelos scripts de linha de comando, para trocar um traceback longo por uma instrução clara.
    """
    engine = make_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        detail = str(exc.orig).splitlines()[0] if exc.orig else type(exc).__name__
        print(DB_UNAVAILABLE_MESSAGE.format(detail=detail), file=sys.stderr)
        raise SystemExit(2) from None
    return engine

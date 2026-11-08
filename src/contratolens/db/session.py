"""Criação do engine e das sessões do banco."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    """Cria o engine do SQLAlchemy para a URL informada."""
    return create_engine(database_url, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Cria a fábrica de sessões ligada ao engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)

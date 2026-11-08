"""Base declarativa do SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de todos os modelos do banco."""

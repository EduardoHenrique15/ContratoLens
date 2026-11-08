from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from contratolens.db.base import Base


def test_migration_creates_same_tables_as_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrado.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    inspector = inspect(create_engine(url))
    migrated = set(inspector.get_table_names()) - {"alembic_version"}
    assert migrated == set(Base.metadata.tables)
    for table in Base.metadata.tables.values():
        columns = {c["name"] for c in inspector.get_columns(table.name)}
        assert columns == {c.name for c in table.columns}

    command.downgrade(config, "base")
    assert set(inspect(create_engine(url)).get_table_names()) == {"alembic_version"}

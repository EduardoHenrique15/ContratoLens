"""amplia colunas de texto vindas da API

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-08 19:18:23.510078
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Amplia colunas que recebem texto livre da API (ex.: id de fornecedor estrangeiro)."""
    with op.batch_alter_table("contracts") as batch:
        batch.alter_column(
            "esfera",
            existing_type=sa.String(length=2),
            type_=sa.String(length=8),
            existing_nullable=True,
        )
        batch.alter_column(
            "tipo_pessoa",
            existing_type=sa.String(length=2),
            type_=sa.String(length=8),
            existing_nullable=True,
        )
        batch.alter_column(
            "fornecedor_ni",
            existing_type=sa.String(length=20),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch.alter_column(
            "numero_contrato",
            existing_type=sa.String(length=64),
            type_=sa.Text(),
            existing_nullable=True,
        )
    with op.batch_alter_table("documents") as batch:
        batch.alter_column(
            "tipo_documento",
            existing_type=sa.String(length=64),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Volta aos tamanhos antigos (falha se já houver valores maiores)."""
    with op.batch_alter_table("contracts") as batch:
        batch.alter_column(
            "esfera",
            existing_type=sa.String(length=8),
            type_=sa.String(length=2),
            existing_nullable=True,
        )
        batch.alter_column(
            "tipo_pessoa",
            existing_type=sa.String(length=8),
            type_=sa.String(length=2),
            existing_nullable=True,
        )
        batch.alter_column(
            "fornecedor_ni",
            existing_type=sa.Text(),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
        batch.alter_column(
            "numero_contrato",
            existing_type=sa.Text(),
            type_=sa.String(length=64),
            existing_nullable=True,
        )
    with op.batch_alter_table("documents") as batch:
        batch.alter_column(
            "tipo_documento",
            existing_type=sa.Text(),
            type_=sa.String(length=64),
            existing_nullable=True,
        )

"""Add storage_key column to songs

Revision ID: 5134a255a1eb
Revises: 47d65135c6ae
Create Date: 2026-06-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5134a255a1eb"
down_revision: str | Sequence[str] | None = "47d65135c6ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("storage_key", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.drop_column("storage_key")

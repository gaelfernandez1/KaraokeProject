"""Add users table and turn songs.user_id into a real FK

Revision ID: a1b2c3d4e5f6
Revises: 5134a255a1eb
Create Date: 2026-06-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "5134a255a1eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    # songs.user_id was an unused nullable Integer; widen it to the UUID type and
    # bolt on the FK. Every existing row is NULL, so the type change is safe.
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=36),
            existing_nullable=True,
        )
        batch_op.create_foreign_key("fk_songs_user_id_users", "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("songs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_songs_user_id_users", type_="foreignkey")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            type_=sa.Integer(),
            existing_nullable=True,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
    op.drop_table("users")

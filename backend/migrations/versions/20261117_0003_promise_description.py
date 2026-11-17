"""Add promise description; category, type and quote become optional.

Real promises (data/sluby.json) come with a title and a description only.
Category and type are filled in later, the verbatim quote once it is extracted.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows get their quote as the description, then the column is required.
    op.add_column("promise", sa.Column("description", sa.Text(), nullable=True))
    op.execute("UPDATE promise SET description = quote")
    op.alter_column("promise", "description", nullable=False)

    op.alter_column("promise", "quote", existing_type=sa.Text(), nullable=True)
    op.alter_column("promise", "category_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("promise", "type", existing_type=sa.String(length=30), nullable=True)


def downgrade() -> None:
    # Fails if promises without a category, type or quote exist; delete them first.
    op.alter_column("promise", "type", existing_type=sa.String(length=30), nullable=False)
    op.alter_column("promise", "category_id", existing_type=sa.Integer(), nullable=False)
    op.execute("UPDATE promise SET quote = description WHERE quote IS NULL")
    op.alter_column("promise", "quote", existing_type=sa.Text(), nullable=False)
    op.drop_column("promise", "description")

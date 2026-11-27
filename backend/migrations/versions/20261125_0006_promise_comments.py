"""Add political scientists' comments on promises (more than one per promise).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promise_comment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("promise_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("author_role", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["promise_id"], ["promise.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_promise_comment_promise_id"), "promise_comment", ["promise_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_promise_comment_promise_id"), table_name="promise_comment")
    op.drop_table("promise_comment")

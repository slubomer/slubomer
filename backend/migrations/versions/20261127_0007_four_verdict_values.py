"""Use the four verdict values of the imported JSON and store vote evidence.

splneny -> splnene, v_procese -> ciastocne, nesplneny -> nesplnene; porusene is new.
Evidence may now be a vote without a quote, its numbers go to evidence.vote.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_VALUES = {"splneny": "splnene", "v_procese": "ciastocne", "nesplneny": "nesplnene"}
# Going back there is no "porusene", the closest old value is "nesplneny".
DOWNGRADE_VALUES = {
    "splnene": "splneny",
    "ciastocne": "v_procese",
    "porusene": "nesplneny",
    "nesplnene": "nesplneny",
}


def _rename_values(mapping: dict[str, str]) -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    # Published verdicts are locked by a trigger (migration 0005). Renaming a value
    # keeps its meaning, so the lock is paused only for this update.
    if postgres:
        op.execute("ALTER TABLE verdict DISABLE TRIGGER verdict_lock")
    for old, new in mapping.items():
        op.execute(
            sa.text("UPDATE verdict SET value = :new WHERE value = :old").bindparams(
                old=old, new=new
            )
        )
    if postgres:
        op.execute("ALTER TABLE verdict ENABLE TRIGGER verdict_lock")


def upgrade() -> None:
    _rename_values(UPGRADE_VALUES)
    with op.batch_alter_table("evidence") as batch:
        batch.alter_column("quote", existing_type=sa.Text(), nullable=True)
        batch.add_column(sa.Column("vote", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Old rows require a quote: evidence without one (votes, web links) is removed.
    op.execute("DELETE FROM evidence WHERE quote IS NULL")
    with op.batch_alter_table("evidence") as batch:
        batch.drop_column("vote")
        batch.alter_column("quote", existing_type=sa.Text(), nullable=False)
    _rename_values(DOWNGRADE_VALUES)

"""Add the audit log. In PostgreSQL its rows can't be updated or deleted.

Also locks published verdicts in the database, so not even raw SQL or a bulk
update can change history (the ORM check in app/models/verdict.py can't see those).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A trigger works even for the database owner, unlike revoking permissions.
PROTECT_FUNCTION = """
CREATE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""
PROTECT_TRIGGER = """
CREATE TRIGGER audit_log_append_only
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
"""

# A published or replaced verdict can't be deleted. Its only allowed change is
# publikovany -> nahradeny with every other column untouched.
VERDICT_LOCK_FUNCTION = """
CREATE FUNCTION verdict_lock() RETURNS trigger AS $$
BEGIN
    IF OLD.state NOT IN ('publikovany', 'nahradeny') THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'published verdict % cannot be deleted', OLD.id;
    END IF;
    IF to_jsonb(NEW) = to_jsonb(OLD) THEN
        RETURN NEW;
    END IF;
    IF OLD.state = 'publikovany' AND NEW.state = 'nahradeny'
       AND (to_jsonb(NEW) - 'state') = (to_jsonb(OLD) - 'state') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'published verdict % cannot be changed, create a new version', OLD.id;
END;
$$ LANGUAGE plpgsql;
"""
VERDICT_LOCK_TRIGGER = """
CREATE TRIGGER verdict_lock
BEFORE UPDATE OR DELETE ON verdict
FOR EACH ROW EXECUTE FUNCTION verdict_lock();
"""


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"])
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"])
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(PROTECT_FUNCTION)
        op.execute(PROTECT_TRIGGER)
        op.execute(VERDICT_LOCK_FUNCTION)
        op.execute(VERDICT_LOCK_TRIGGER)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS verdict_lock ON verdict")
        op.execute("DROP FUNCTION IF EXISTS verdict_lock()")
        op.execute("DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log")
        op.execute("DROP FUNCTION IF EXISTS audit_log_append_only()")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")

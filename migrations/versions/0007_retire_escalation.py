"""retire complaint escalation

Escalation is removed from the product: execs and the president read the
handling channels directly, so a complaint is simply handled by its tier
(docs/complaints-policy.md). Any row stuck in 'escalated' becomes
'acknowledged', and the escalated_to column is dropped. On Postgres the old
escalationtarget enum type is dropped too; the stray 'escalated' label stays
in the complaintstatus type (Postgres cannot drop enum values) and is
harmless because nothing writes it anymore.

Revision ID: 0007_retire_escalation
Revises: 0006_complaints_config
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

from rbga.db.database import COMPLAINTS_SCHEMA

revision = "0007_retire_escalation"
down_revision = "0006_complaints_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = f"{COMPLAINTS_SCHEMA}.complaints" if COMPLAINTS_SCHEMA else "complaints"
    op.execute(f"UPDATE {table} SET status = 'acknowledged' WHERE status = 'escalated'")
    with op.batch_alter_table("complaints", schema=COMPLAINTS_SCHEMA) as batch:
        batch.drop_column("escalated_to")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS escalationtarget")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TYPE escalationtarget AS ENUM ('committee', 'exec', 'president', 'rusu')"
        )
    with op.batch_alter_table("complaints", schema=COMPLAINTS_SCHEMA) as batch:
        batch.add_column(
            sa.Column(
                "escalated_to",
                sa.Enum("committee", "exec", "president", "rusu", name="escalationtarget"),
                nullable=True,
            )
        )

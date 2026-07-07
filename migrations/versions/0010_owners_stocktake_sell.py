"""owners table + stocktake and sell-price fields on board_games

Three exec-management features:
  * owners        — contact details per owner name, kept OUT of the public
                    API (managed only via exec-gated /owner commands)
  * sell_price    — asking price; a condition-based estimate is computed
                    from `price` when unset
  * last_seen_at / missing — /game stocktake checklist state

Revision ID: 0010_owners_stocktake_sell
Revises: 0009_boardgame_thumbnail
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_owners_stocktake_sell"
down_revision = "0009_boardgame_thumbnail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("contact", sa.String(length=256), nullable=True),
        sa.UniqueConstraint("name", name="uq_owners_name"),
    )
    op.create_index("ix_owners_name", "owners", ["name"])
    with op.batch_alter_table("board_games") as batch:
        batch.add_column(sa.Column("sell_price", sa.Numeric(10, 2), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))
        batch.add_column(
            sa.Column("missing", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("board_games") as batch:
        batch.drop_column("missing")
        batch.drop_column("last_seen_at")
        batch.drop_column("sell_price")
    op.drop_index("ix_owners_name", table_name="owners")
    op.drop_table("owners")

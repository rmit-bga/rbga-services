"""add tags to board_games

Free-form labels stored as a JSON list of strings (e.g. ["Strategy",
"Party"]). Auto-filled from BGG's category links when a game is added via a
BGG link; also settable manually through the API and /game add|edit.

Revision ID: 0008_boardgame_tags
Revises: 0007_retire_escalation
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_boardgame_tags"
down_revision = "0007_retire_escalation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("board_games") as batch:
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("board_games") as batch:
        batch.drop_column("tags")

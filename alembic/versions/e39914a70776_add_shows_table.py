"""add shows table

Revision ID: e39914a70776
Revises: a1b2c3d4e5f6
Create Date: 2026-02-03 17:31:15.219658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e39914a70776'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("overview", sa.String(), nullable=True),
        sa.Column("poster_url", sa.String(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("vote_count", sa.Integer(), nullable=True),
        sa.Column("first_air_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id", name="uq_shows_tmdb_id"),
    )
    op.create_index(op.f("ix_shows_id"), "shows", ["id"], unique=False)
    op.create_index(op.f("ix_shows_tmdb_id"), "shows", ["tmdb_id"], unique=True)



def downgrade() -> None:
    op.drop_index(op.f("ix_shows_tmdb_id"), table_name="shows")
    op.drop_index(op.f("ix_shows_id"), table_name="shows")
    op.drop_table("shows")


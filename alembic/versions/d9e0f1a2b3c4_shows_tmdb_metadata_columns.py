"""add shows TMDB metadata columns

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-02-24

Adds content_rating, average_episode_length, number_of_seasons, original_language
to shows so metadata can be read from DB first and written through from TMDB.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shows", sa.Column("content_rating", sa.String(), nullable=True))
    op.add_column("shows", sa.Column("average_episode_length", sa.Integer(), nullable=True))
    op.add_column("shows", sa.Column("number_of_seasons", sa.Integer(), nullable=True))
    op.add_column("shows", sa.Column("original_language", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shows", "original_language")
    op.drop_column("shows", "number_of_seasons")
    op.drop_column("shows", "average_episode_length")
    op.drop_column("shows", "content_rating")

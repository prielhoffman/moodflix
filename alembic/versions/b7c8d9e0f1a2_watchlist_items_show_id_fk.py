"""watchlist_items show_id FK and optional title

Revision ID: b7c8d9e0f1a2
Revises: 6b6f7d9c2f10
Create Date: 2026-02-24

Adds show_id (FK to shows.id) as primary reference; title becomes optional
(denormalized). Existing rows keep title, have show_id NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "6b6f7d9c2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add show_id (nullable for existing rows), FK to shows.id, index
    op.add_column(
        "watchlist_items",
        sa.Column("show_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_watchlist_items_show_id"),
        "watchlist_items",
        ["show_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_watchlist_items_show_id_shows",
        "watchlist_items",
        "shows",
        ["show_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Make title nullable (denormalized / legacy)
    op.alter_column(
        "watchlist_items",
        "title",
        existing_type=sa.String(),
        nullable=True,
    )

    # One row per user per show when show_id is set
    op.create_index(
        "ix_watchlist_items_user_show_unique",
        "watchlist_items",
        ["user_id", "show_id"],
        unique=True,
        postgresql_where=sa.text("show_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watchlist_items_user_show_unique",
        table_name="watchlist_items",
    )
    op.alter_column(
        "watchlist_items",
        "title",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_constraint(
        "fk_watchlist_items_show_id_shows",
        "watchlist_items",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_watchlist_items_show_id"), table_name="watchlist_items")
    op.drop_column("watchlist_items", "show_id")

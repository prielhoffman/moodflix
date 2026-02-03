"""add user table and watchlist user relationship

Revision ID: a1b2c3d4e5f6
Revises: 77c9ad2999fb
Create Date: 2026-02-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4e3c32caba36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Add user_id column, index, and FK to watchlist_items
    op.add_column(
        "watchlist_items",
        sa.Column("user_id", sa.Integer(), nullable=False),
    )
    op.create_index(
        op.f("ix_watchlist_items_user_id"),
        "watchlist_items",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_watchlist_items_user_id_users",
        "watchlist_items",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop FK and index and column from watchlist_items
    op.drop_constraint(
        "fk_watchlist_items_user_id_users",
        "watchlist_items",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_watchlist_items_user_id"),
        table_name="watchlist_items",
    )
    op.drop_column("watchlist_items", "user_id")

    # Drop users indexes and table
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")


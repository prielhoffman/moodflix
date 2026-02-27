"""add full_name and date_of_birth to users table

Revision ID: e5f6a7b8c9d0
Revises: d9e0f1a2b3c4
Create Date: 2026-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns as nullable first for safe migration with existing users
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))

    # Backfill: use email prefix as full_name, and a default DOB (1990-01-01) for age ~36
    op.execute(
        """
        UPDATE users
        SET
            full_name = COALESCE(split_part(email, '@', 1), 'User'),
            date_of_birth = '1990-01-01'
        WHERE full_name IS NULL OR date_of_birth IS NULL
        """
    )

    # Alter to non-null
    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "users",
        "date_of_birth",
        existing_type=sa.Date(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "full_name")

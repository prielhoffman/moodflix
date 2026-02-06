"""add shows embedding vector

Revision ID: 48da73d26c21
Revises: e39914a70776
Create Date: 2026-02-06 18:51:15.968658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '48da73d26c21'
down_revision: Union[str, Sequence[str], None] = 'e39914a70776'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure pgvector extension exists before using the Vector type
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Nullable to avoid breaking existing rows
    op.add_column("shows", sa.Column("embedding", Vector(1536), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("shows", "embedding")
    # Note: we intentionally do NOT drop the pgvector extension here.

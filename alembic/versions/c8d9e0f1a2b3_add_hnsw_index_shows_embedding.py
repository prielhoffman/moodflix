"""add HNSW index on shows.embedding (vector_cosine_ops)

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-02-24

Adds an HNSW index on shows.embedding with vector_cosine_ops so that
ORDER BY embedding <=> query_vector uses the index instead of a full table scan.
Reduces latency for semantic search and more-like-this queries.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute(
        "CREATE INDEX ix_shows_embedding_hnsw ON shows "
        "USING hnsw (embedding vector_cosine_ops)"
        " WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    op.drop_index("ix_shows_embedding_hnsw", table_name="shows")

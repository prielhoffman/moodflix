"""change embedding dim to 384

Revision ID: 6b6f7d9c2f10
Revises: 48da73d26c21
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6b6f7d9c2f10"
down_revision: Union[str, Sequence[str], None] = "48da73d26c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Change embedding dimension to 384 (existing embeddings are cleared)
    op.execute(
        "ALTER TABLE shows ALTER COLUMN embedding TYPE vector(384) "
        "USING NULL::vector(384);"
    )


def downgrade() -> None:
    # Revert embedding dimension to 1536 (existing embeddings are cleared)
    op.execute(
        "ALTER TABLE shows ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL::vector(1536);"
    )


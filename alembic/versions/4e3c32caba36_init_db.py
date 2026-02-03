"""init db

Revision ID: 4e3c32caba36
Revises: 77c9ad2999fb
Create Date: 2026-02-02 20:00:29.476620

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "4e3c32caba36"
down_revision: Union[str, Sequence[str], None] = "77c9ad2999fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (no-op placeholder)."""
    # This revision previously contained no schema changes.
    # It is kept as a placeholder so existing databases that
    # reference this revision can still be migrated.
    pass


def downgrade() -> None:
    """Downgrade schema (no-op placeholder)."""
    # Matching no-op downgrade for the placeholder revision.
    pass


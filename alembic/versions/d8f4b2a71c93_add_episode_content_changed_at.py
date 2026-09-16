"""add episode content_changed_at timestamp

Revision ID: d8f4b2a71c93
Revises: c3f7a1d92e58
Create Date: 2026-09-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "d8f4b2a71c93"
down_revision: Union[str, Sequence[str], None] = "c3f7a1d92e58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column("content_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("episodes", "content_changed_at")

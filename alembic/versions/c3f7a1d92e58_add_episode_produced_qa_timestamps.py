"""add episode video_produced_at and qa_run_at timestamps

Revision ID: c3f7a1d92e58
Revises: b8e4f6a2c710
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "c3f7a1d92e58"
down_revision: Union[str, Sequence[str], None] = "b8e4f6a2c710"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column("video_produced_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "episodes",
        sa.Column("qa_run_at", sa.DateTime(timezone=True), nullable=True),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("episodes", "qa_run_at")
    op.drop_column("episodes", "video_produced_at")

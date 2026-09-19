"""add episode publishing fields

Revision ID: a4d7c1e69f28
Revises: f9c2a5e8d371
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "a4d7c1e69f28"
down_revision: Union[str, Sequence[str], None] = "f9c2a5e8d371"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column(
            "publish_status",
            sa.String(length=50),
            nullable=False,
            server_default="not_published",
        ),
    )
    op.add_column("episodes", sa.Column("youtube_video_id", sa.Text(), nullable=True))
    op.add_column("episodes", sa.Column("youtube_url", sa.Text(), nullable=True))
    op.add_column(
        "episodes",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("episodes", sa.Column("publish_error", sa.Text(), nullable=True))


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("episodes", "publish_error")
    op.drop_column("episodes", "published_at")
    op.drop_column("episodes", "youtube_url")
    op.drop_column("episodes", "youtube_video_id")
    op.drop_column("episodes", "publish_status")

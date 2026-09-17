"""add story_content.caption_segments

Revision ID: f9c2a5e8d371
Revises: e2a9c74f1b06
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "f9c2a5e8d371"
down_revision: Union[str, Sequence[str], None] = "e2a9c74f1b06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "story_content",
        sa.Column("caption_segments", sa.Text(), nullable=True),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("story_content", "caption_segments")

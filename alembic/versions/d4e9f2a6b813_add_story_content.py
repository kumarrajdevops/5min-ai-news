"""add story_content

Revision ID: d4e9f2a6b813
Revises: c7d3f8a91b42
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "d4e9f2a6b813"
down_revision: Union[str, Sequence[str], None] = "c7d3f8a91b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # One row per story: generated script, narration audio, branded
    # visual, and composed video -- the first pass at the
    # architecture's Script/Voice/Visual/Video stages, proven out on
    # one story at a time.
    op.create_table(
        "story_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "story_id",
            sa.Integer(),
            sa.ForeignKey("stories.id"),
            nullable=False,
        ),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("audio_path", sa.Text(), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("image_path", sa.Text(), nullable=True),
        sa.Column("captions_path", sa.Text(), nullable=True),
        sa.Column("video_path", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("story_id", name="uq_story_content_story_id"),
    )

    op.create_index(
        "ix_story_content_story_id", "story_content", ["story_id"]
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_story_content_story_id", table_name="story_content")
    op.drop_table("story_content")

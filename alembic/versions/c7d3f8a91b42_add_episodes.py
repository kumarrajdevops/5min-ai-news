"""add episodes and episode_stories

Revision ID: c7d3f8a91b42
Revises: a1f92e6d7b3c
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "c7d3f8a91b42"
down_revision: Union[str, Sequence[str], None] = "a1f92e6d7b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # One row per ranking/selection run (conceptually, one row per
    # daily video episode). We deliberately do NOT put a unique
    # constraint on run_date -- during MVP testing we may run
    # selection multiple times in one day, and each run should be
    # preserved as its own historical record rather than overwritten.
    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_episodes_run_date", "episodes", ["run_date"])

    # Join table: one row per (episode, story) selection. A story can
    # appear in multiple episodes over time (e.g. re-running selection
    # during testing) -- each run's full Top-30 snapshot is preserved
    # independently rather than mutating the story itself. This keeps
    # `stories` completely untouched by ranking/selection.
    op.create_table(
        "episode_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episodes.id"),
            nullable=False,
        ),
        sa.Column(
            "story_id",
            sa.Integer(),
            sa.ForeignKey("stories.id"),
            nullable=False,
        ),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("selection_status", sa.String(length=20), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("rank_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "episode_id", "story_id", name="uq_episode_story"
        ),
        sa.UniqueConstraint(
            "episode_id", "rank_position", name="uq_episode_rank_position"
        ),
    )

    op.create_index(
        "ix_episode_stories_episode_id", "episode_stories", ["episode_id"]
    )
    op.create_index(
        "ix_episode_stories_story_id", "episode_stories", ["story_id"]
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_episode_stories_story_id", table_name="episode_stories")
    op.drop_index("ix_episode_stories_episode_id", table_name="episode_stories")
    op.drop_table("episode_stories")

    op.drop_index("ix_episodes_run_date", table_name="episodes")
    op.drop_table("episodes")

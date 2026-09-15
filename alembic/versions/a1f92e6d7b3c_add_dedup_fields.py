"""add dedup fields

Revision ID: a1f92e6d7b3c
Revises: 996b16094585
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "a1f92e6d7b3c"
down_revision: Union[str, Sequence[str], None] = "996b16094585"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # Self-referential FK: NULL means "this story is canonical"
    # (either unique, or the chosen representative of a duplicate
    # group). Non-null points at the canonical story's id. We never
    # delete duplicate rows -- the architecture requires full
    # audit/traceability of every raw article we ever collected.
    op.add_column(
        "stories",
        sa.Column(
            "canonical_story_id",
            sa.Integer(),
            sa.ForeignKey("stories.id"),
            nullable=True,
        ),
    )

    # Explanation of why this story was grouped under its canonical
    # story (similarity scores, time delta) -- same audit pattern as
    # filter_reason on the AI relevance filter.
    op.add_column(
        "stories",
        sa.Column(
            "dedup_reason",
            sa.Text(),
            nullable=True,
        ),
    )

    # Index since we will constantly filter/join on this column
    # (both "give me canonical stories" and "give me duplicates of X").
    op.create_index(
        "ix_stories_canonical_story_id",
        "stories",
        ["canonical_story_id"],
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_stories_canonical_story_id", table_name="stories")
    op.drop_column("stories", "dedup_reason")
    op.drop_column("stories", "canonical_story_id")

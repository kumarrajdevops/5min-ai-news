"""add ai relevance fields

Revision ID: 996b16094585
Revises: 6f1e2a7b9c04
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "996b16094585"
down_revision: Union[str, Sequence[str], None] = "6f1e2a7b9c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # Add the AI relevance classification column.
    # It is temporarily nullable so existing stories do not
    # cause a NOT NULL constraint failure.
    op.add_column(
        "stories",
        sa.Column(
            "ai_relevance",
            sa.String(length=50),
            nullable=True,
        ),
    )

    # Add the numerical AI relevance score.
    op.add_column(
        "stories",
        sa.Column(
            "ai_relevance_score",
            sa.Float(),
            nullable=True,
        ),
    )

    # Add the explanation for why the story was accepted/rejected.
    op.add_column(
        "stories",
        sa.Column(
            "filter_reason",
            sa.Text(),
            nullable=True,
        ),
    )

    # Existing stories were collected before the AI relevance
    # filter existed, so mark them as pending classification.
    op.execute(
        """
        UPDATE stories
        SET ai_relevance = 'pending'
        WHERE ai_relevance IS NULL
        """
    )

    # Now that every existing row has a value, enforce NOT NULL
    # for future records.
    op.alter_column(
        "stories",
        "ai_relevance",
        existing_type=sa.String(length=50),
        nullable=False,
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    # Remove the filter explanation column.
    op.drop_column("stories", "filter_reason")

    # Remove the AI relevance score column.
    op.drop_column("stories", "ai_relevance_score")

    # Remove the AI relevance classification column.
    op.drop_column("stories", "ai_relevance")

"""add fact extraction and verification columns to stories

Revision ID: e2a9c74f1b06
Revises: d8f4b2a71c93
Create Date: 2026-09-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "e2a9c74f1b06"
down_revision: Union[str, Sequence[str], None] = "d8f4b2a71c93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("extracted_facts", sa.Text(), nullable=True),
    )

    op.add_column(
        "stories",
        sa.Column(
            "verification_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )

    op.add_column(
        "stories",
        sa.Column("verification_reason", sa.Text(), nullable=True),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("stories", "verification_reason")
    op.drop_column("stories", "verification_status")
    op.drop_column("stories", "extracted_facts")

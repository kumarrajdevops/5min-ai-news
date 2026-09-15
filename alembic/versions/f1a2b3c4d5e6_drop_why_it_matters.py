"""drop why_it_matters from story_content

Revision ID: f1a2b3c4d5e6
Revises: d4e9f2a6b813
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d4e9f2a6b813"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # Scripts read the headline + a deterministic summary of the
    # story, nothing more -- no editorializing/speculative "why it
    # matters" commentary.
    op.drop_column("story_content", "why_it_matters")


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.add_column(
        "story_content",
        sa.Column("why_it_matters", sa.Text(), nullable=True),
    )

"""add episode qa_status and qa_report

Revision ID: b8e4f6a2c710
Revises: a7c3d9e1f204
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "b8e4f6a2c710"
down_revision: Union[str, Sequence[str], None] = "a7c3d9e1f204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column(
            "qa_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )

    op.add_column(
        "episodes",
        sa.Column("qa_report", sa.Text(), nullable=True),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("episodes", "qa_report")
    op.drop_column("episodes", "qa_status")

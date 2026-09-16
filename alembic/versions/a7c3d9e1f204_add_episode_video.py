"""add episode video_path and video_status

Revision ID: a7c3d9e1f204
Revises: f1a2b3c4d5e6
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------
# Migration identifiers
# ---------------------------------------------------------

revision: str = "a7c3d9e1f204"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# Upgrade
# ---------------------------------------------------------

def upgrade() -> None:
    # Final combined episode video -- all primary stories' individual
    # videos concatenated in rank order.
    op.add_column(
        "episodes",
        sa.Column("video_path", sa.Text(), nullable=True),
    )

    op.add_column(
        "episodes",
        sa.Column(
            "video_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )


# ---------------------------------------------------------
# Downgrade
# ---------------------------------------------------------

def downgrade() -> None:
    op.drop_column("episodes", "video_status")
    op.drop_column("episodes", "video_path")

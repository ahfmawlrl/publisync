"""016: add last_comment_collected_at to channels table (Phase 1-B, S9).

Tracks when comments were last collected per channel for incremental fetching.
"""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("last_comment_collected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("channels", "last_comment_collected_at")

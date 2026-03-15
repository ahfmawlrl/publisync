"""021: Add ffmpeg-related ENUM values and parent_asset_id column.

Adds:
  - aijobtype ENUM: SUBTITLE_BURNIN, SHORTFORM_RENDER
  - aitasktype ENUM: SUBTITLE_BURNIN, SHORTFORM_RENDER
  - media_assets.parent_asset_id FK column (for tracking derived videos)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new values to aijobtype ENUM
    op.execute("ALTER TYPE aijobtype ADD VALUE IF NOT EXISTS 'SUBTITLE_BURNIN'")
    op.execute("ALTER TYPE aijobtype ADD VALUE IF NOT EXISTS 'SHORTFORM_RENDER'")

    # 2. Add new values to aitasktype ENUM (used in ai_usage_logs)
    op.execute("ALTER TYPE aitasktype ADD VALUE IF NOT EXISTS 'SUBTITLE_BURNIN'")
    op.execute("ALTER TYPE aitasktype ADD VALUE IF NOT EXISTS 'SHORTFORM_RENDER'")

    # 3. Add parent_asset_id column to media_assets
    # Temporarily disable RLS to avoid app.current_org_id requirement
    op.execute("ALTER TABLE media_assets DISABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE media_assets "
        "ADD COLUMN IF NOT EXISTS parent_asset_id UUID "
        "REFERENCES media_assets(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_media_assets_parent_asset_id "
        "ON media_assets (parent_asset_id)"
    )
    op.execute("ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("idx_media_assets_parent_asset_id", table_name="media_assets")
    op.drop_column("media_assets", "parent_asset_id")
    # Note: PostgreSQL does not support removing values from ENUM types.
    # To fully downgrade, you would need to recreate the ENUM type.

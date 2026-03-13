"""020: Mark deprecated flat columns on contents table.

Adds COMMENT annotations to contents columns that have been superseded by
content_variants and variant_media. The columns are kept for backward
compatibility but should no longer be written to by new code.

Deprecated columns:
  - platforms       → content_variants.platform
  - channel_ids     → content_variants.channel_id
  - platform_contents → content_variants.metadata
  - media_urls      → variant_media (via media_assets)
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "COMMENT ON COLUMN contents.platforms IS "
        "'DEPRECATED: use content_variants.platform instead';"
    )
    op.execute(
        "COMMENT ON COLUMN contents.channel_ids IS "
        "'DEPRECATED: use content_variants.channel_id instead';"
    )
    op.execute(
        "COMMENT ON COLUMN contents.platform_contents IS "
        "'DEPRECATED: use content_variants.metadata instead';"
    )
    op.execute(
        "COMMENT ON COLUMN contents.media_urls IS "
        "'DEPRECATED: use variant_media (via media_assets) instead';"
    )


def downgrade() -> None:
    op.execute("COMMENT ON COLUMN contents.platforms IS NULL;")
    op.execute("COMMENT ON COLUMN contents.channel_ids IS NULL;")
    op.execute("COMMENT ON COLUMN contents.platform_contents IS NULL;")
    op.execute("COMMENT ON COLUMN contents.media_urls IS NULL;")

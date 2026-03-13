"""019: Migrate existing content data to content_variants / variant_media.

Converts:
  - contents.platforms + channel_ids + platform_contents → content_variants rows
  - contents.media_urls → variant_media rows (as SOURCE role)

Existing columns (platforms, channel_ids, platform_contents, media_urls) are
preserved but considered deprecated. They will be removed in a future migration.
"""

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bypass RLS for data migration (we need to read all tenants' data).
    # Both vars must be set: tenant_isolation uses current_setting without missing_ok,
    # so it raises if app.current_org_id is unset even though sa_bypass would pass.
    op.execute("SET LOCAL app.user_role = 'SYSTEM_ADMIN'")
    op.execute("SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000000'")

    # ── Step 1: Convert platforms/channel_ids → content_variants ──
    #
    # For each content that has platforms set:
    #   - If channel_ids is populated, create one variant per (platform, channel_id)
    #   - If channel_ids is empty, create one variant per platform (channel_id NULL)
    #   - Copy platform-specific overrides from platform_contents JSONB if available
    #
    # Logic:
    #   1. Contents with channel_ids -> cross-join platforms x channel_ids
    #   2. Contents without channel_ids → one variant per platform
    #   3. platform_contents JSONB overrides (title, body) if key matches platform

    # Case A: Contents with valid channel_ids -> one variant per (platform, channel)
    op.execute("""
        INSERT INTO content_variants (id, content_id, organization_id, platform, channel_id, title, body, metadata, created_at, updated_at)
        SELECT
            uuid_generate_v4(),
            c.id,
            c.organization_id,
            p.platform::platformtype,
            ch_valid.id,
            COALESCE(
                c.platform_contents -> UPPER(p.platform) ->> 'title',
                c.platform_contents -> p.platform ->> 'title'
            ),
            COALESCE(
                c.platform_contents -> UPPER(p.platform) ->> 'body',
                c.platform_contents -> p.platform ->> 'body'
            ),
            COALESCE(
                c.platform_contents -> UPPER(p.platform),
                c.platform_contents -> p.platform,
                '{}'::jsonb
            ),
            c.created_at,
            c.updated_at
        FROM contents c
        CROSS JOIN LATERAL unnest(c.platforms) AS p(platform)
        JOIN LATERAL unnest(c.channel_ids) AS cid(channel_id) ON true
        JOIN channels ch_valid ON ch_valid.id = cid.channel_id
        WHERE c.platforms IS NOT NULL
          AND array_length(c.platforms, 1) > 0
          AND c.channel_ids IS NOT NULL
          AND array_length(c.channel_ids, 1) > 0
          AND c.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """)

    # Case B: Contents without channel_ids -> one variant per platform (channel_id NULL)
    op.execute("""
        INSERT INTO content_variants (id, content_id, organization_id, platform, title, body, metadata, created_at, updated_at)
        SELECT
            uuid_generate_v4(),
            c.id,
            c.organization_id,
            p.platform::platformtype,
            COALESCE(
                c.platform_contents -> UPPER(p.platform) ->> 'title',
                c.platform_contents -> p.platform ->> 'title'
            ),
            COALESCE(
                c.platform_contents -> UPPER(p.platform) ->> 'body',
                c.platform_contents -> p.platform ->> 'body'
            ),
            COALESCE(
                c.platform_contents -> UPPER(p.platform),
                c.platform_contents -> p.platform,
                '{}'::jsonb
            ),
            c.created_at,
            c.updated_at
        FROM contents c
        CROSS JOIN LATERAL unnest(c.platforms) AS p(platform)
        WHERE c.platforms IS NOT NULL
          AND array_length(c.platforms, 1) > 0
          AND (c.channel_ids IS NULL OR array_length(c.channel_ids, 1) IS NULL)
          AND c.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """)

    # ── Step 2: Link source_media to variants ───────────────────
    #
    # For contents with source_media_id set, create variant_media records
    # linking that media asset to all variants of that content.
    # media_urls (deprecated URL strings) cannot be reliably mapped to
    # media_asset object_keys, so they are skipped.

    op.execute("""
        INSERT INTO variant_media (id, variant_id, media_asset_id, organization_id, role, sort_order, created_at, updated_at)
        SELECT
            uuid_generate_v4(),
            cv.id,
            c.source_media_id,
            cv.organization_id,
            'SOURCE'::mediaroletype,
            0,
            cv.created_at,
            cv.updated_at
        FROM contents c
        JOIN content_variants cv ON cv.content_id = c.id
        WHERE c.source_media_id IS NOT NULL
          AND c.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Remove migrated data (only records that were auto-generated).
    # Since we can't reliably distinguish auto-migrated from manually-created
    # variants, we simply truncate both tables. This is safe because
    # the deprecated columns still hold the original data.
    op.execute("DELETE FROM variant_media")
    op.execute("DELETE FROM content_variants")

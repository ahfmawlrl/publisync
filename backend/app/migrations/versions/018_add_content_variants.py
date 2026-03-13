"""018: Add content_variants + variant_media tables, mediaroletype ENUM (v2.0).

Creates:
  - mediaroletype ENUM (SOURCE, EDITED, SUBTITLE, THUMBNAIL, EFFECT)
  - content_variants table (platform-specific content derivatives)
  - variant_media table (variant ↔ media_asset many-to-many with role)

Alters:
  - contents: add source_media_id FK → media_assets
  - publish_results: add variant_id FK → content_variants
  - approval_histories: add variant_id FK → content_variants

All new tables get RLS tenant_isolation + sa_bypass policies.
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Create mediaroletype ENUM ──────────────────
    op.execute("""
        CREATE TYPE mediaroletype AS ENUM (
            'SOURCE', 'EDITED', 'SUBTITLE', 'THUMBNAIL', 'EFFECT'
        )
    """)

    # ── Step 2: Create content_variants table ──────────────
    op.execute("""
        CREATE TABLE content_variants (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            content_id      UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            platform        platformtype NOT NULL,
            channel_id      UUID REFERENCES channels(id) ON DELETE SET NULL,
            title           VARCHAR(500),
            body            TEXT,
            hashtags        VARCHAR[] DEFAULT '{}',
            metadata        JSONB DEFAULT '{}',
            sort_order      INT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Indexes
    op.execute("CREATE INDEX idx_content_variants_content_id ON content_variants(content_id)")
    op.execute("CREATE INDEX idx_content_variants_org_id ON content_variants(organization_id)")
    op.execute("CREATE INDEX idx_content_variants_platform ON content_variants(platform)")
    op.execute("CREATE INDEX idx_content_variants_channel_id ON content_variants(channel_id)")

    # Unique constraint: (content_id, platform, channel_id) with COALESCE for nullable channel_id
    op.execute("""
        CREATE UNIQUE INDEX uq_variant_content_platform_channel
          ON content_variants(content_id, platform, COALESCE(channel_id, '00000000-0000-0000-0000-000000000000'::uuid))
    """)

    # RLS
    op.execute("ALTER TABLE content_variants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE content_variants FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON content_variants
        USING (organization_id = current_setting('app.current_org_id')::uuid)
    """)
    op.execute("""
        CREATE POLICY sa_bypass ON content_variants
        USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')
    """)

    # ── Step 3: Create variant_media table ─────────────────
    op.execute("""
        CREATE TABLE variant_media (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            variant_id      UUID NOT NULL REFERENCES content_variants(id) ON DELETE CASCADE,
            media_asset_id  UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            role            mediaroletype NOT NULL DEFAULT 'SOURCE',
            sort_order      INT NOT NULL DEFAULT 0,
            metadata        JSONB DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Indexes
    op.execute("CREATE INDEX idx_variant_media_variant_id ON variant_media(variant_id)")
    op.execute("CREATE INDEX idx_variant_media_media_id ON variant_media(media_asset_id)")
    op.execute("CREATE INDEX idx_variant_media_org_id ON variant_media(organization_id)")
    op.execute("CREATE INDEX idx_variant_media_role ON variant_media(role)")

    # Unique constraint: (variant_id, media_asset_id, role)
    op.execute("""
        CREATE UNIQUE INDEX uq_variant_media_role
          ON variant_media(variant_id, media_asset_id, role)
    """)

    # RLS
    op.execute("ALTER TABLE variant_media ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE variant_media FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON variant_media
        USING (organization_id = current_setting('app.current_org_id')::uuid)
    """)
    op.execute("""
        CREATE POLICY sa_bypass ON variant_media
        USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')
    """)

    # ── Step 4: Alter contents — add source_media_id ───────
    op.execute("""
        ALTER TABLE contents
        ADD COLUMN source_media_id UUID REFERENCES media_assets(id) ON DELETE SET NULL
    """)

    # ── Step 5: Alter publish_results — add variant_id ─────
    op.execute("""
        ALTER TABLE publish_results
        ADD COLUMN variant_id UUID REFERENCES content_variants(id) ON DELETE SET NULL
    """)
    op.execute("CREATE INDEX idx_publish_results_variant_id ON publish_results(variant_id)")

    # ── Step 6: Alter approval_histories — add variant_id ──
    op.execute("""
        ALTER TABLE approval_histories
        ADD COLUMN variant_id UUID REFERENCES content_variants(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    # Drop added columns
    op.execute("ALTER TABLE approval_histories DROP COLUMN IF EXISTS variant_id")
    op.execute("DROP INDEX IF EXISTS idx_publish_results_variant_id")
    op.execute("ALTER TABLE publish_results DROP COLUMN IF EXISTS variant_id")
    op.execute("ALTER TABLE contents DROP COLUMN IF EXISTS source_media_id")

    # Drop variant_media
    op.execute("DROP POLICY IF EXISTS sa_bypass ON variant_media")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON variant_media")
    op.execute("DROP TABLE IF EXISTS variant_media")

    # Drop content_variants
    op.execute("DROP POLICY IF EXISTS sa_bypass ON content_variants")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON content_variants")
    op.execute("DROP TABLE IF EXISTS content_variants")

    # Drop ENUM
    op.execute("DROP TYPE IF EXISTS mediaroletype")

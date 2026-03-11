"""017: Convert audit_logs to RANGE partitioned table (Phase 1-B, Step 4).

Converts the existing audit_logs table to monthly RANGE partitioning
on created_at. Creates initial partitions for 2026-03 and 2026-04.
Adds PL/pgSQL functions for automatic partition creation and cleanup.
Re-applies INSERT-ONLY trigger and RLS policies on the new table.
"""

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Rename existing table ────────────────────────
    op.execute("ALTER TABLE audit_logs RENAME TO audit_logs_old")

    # Drop old trigger (it references the old table)
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs_old")

    # Drop old RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_logs_old")
    op.execute("DROP POLICY IF EXISTS sa_bypass ON audit_logs_old")

    # ── Step 2: Create partitioned table ─────────────────────
    op.execute("""
        CREATE TABLE audit_logs (
            id              UUID NOT NULL,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            actor_id        UUID REFERENCES users(id),
            actor_role      user_role,
            action          auditaction NOT NULL,
            resource_type   VARCHAR(50) NOT NULL,
            resource_id     UUID,
            changes         JSONB,
            ip_address      VARCHAR(45),
            user_agent      VARCHAR(500),
            request_id      UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # ── Step 3: Create initial partitions ────────────────────
    op.execute("""
        CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
        FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
        FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)

    # ── Step 3b: Enable RLS on initial partitions ────────────
    for part in ("audit_logs_2026_03", "audit_logs_2026_04"):
        op.execute(f"ALTER TABLE {part} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {part} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {part}"
            " FOR ALL USING (organization_id = current_setting('app.current_org_id')::uuid)"
        )
        op.execute(
            f"CREATE POLICY sa_bypass ON {part}"
            " FOR ALL USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
        )

    # ── Step 4: Migrate existing data ────────────────────────
    op.execute("""
        INSERT INTO audit_logs
        SELECT * FROM audit_logs_old
    """)

    # ── Step 5: Drop old table ───────────────────────────────
    op.execute("DROP TABLE audit_logs_old")

    # ── Step 6: Re-create indexes ────────────────────────────
    op.execute("CREATE INDEX idx_audit_logs_org_id ON audit_logs (organization_id)")
    op.execute("CREATE INDEX idx_audit_logs_actor_id ON audit_logs (actor_id)")
    op.execute("CREATE INDEX idx_audit_logs_action ON audit_logs (action)")
    op.execute("CREATE INDEX idx_audit_logs_resource_type ON audit_logs (resource_type)")
    op.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at)")
    op.execute("""
        CREATE INDEX idx_audit_logs_org_action_created
        ON audit_logs (organization_id, action, created_at DESC)
    """)

    # ── Step 7: Re-apply INSERT-ONLY trigger ─────────────────
    # Note: On partitioned tables the trigger must be created on the parent
    op.execute("""
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()
    """)

    # ── Step 8: Re-apply RLS ─────────────────────────────────
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON audit_logs
        USING (organization_id = current_setting('app.current_org_id')::uuid)
    """)
    op.execute("""
        CREATE POLICY sa_bypass ON audit_logs
        USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')
    """)

    # ── Step 9: PL/pgSQL — monthly partition creator ─────────
    op.execute("""
        CREATE OR REPLACE FUNCTION create_audit_partition(target_date DATE)
        RETURNS TEXT AS $$
        DECLARE
            partition_name TEXT;
            start_date DATE;
            end_date DATE;
        BEGIN
            start_date := date_trunc('month', target_date)::DATE;
            end_date := (start_date + INTERVAL '1 month')::DATE;
            partition_name := 'audit_logs_' || to_char(start_date, 'YYYY_MM');

            -- Skip if partition already exists
            IF EXISTS (
                SELECT 1 FROM pg_class WHERE relname = partition_name
            ) THEN
                RETURN partition_name || ' already exists';
            END IF;

            EXECUTE format(
                'CREATE TABLE %I PARTITION OF audit_logs FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );

            -- Apply RLS on the new partition
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', partition_name);
            EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', partition_name);
            EXECUTE format(
                'CREATE POLICY tenant_isolation ON %I FOR ALL USING (organization_id = current_setting(''app.current_org_id'')::uuid)',
                partition_name
            );
            EXECUTE format(
                'CREATE POLICY sa_bypass ON %I FOR ALL USING (current_setting(''app.user_role'', true) = ''SYSTEM_ADMIN'')',
                partition_name
            );

            RETURN partition_name || ' created';
        END;
        $$ LANGUAGE plpgsql
    """)

    # ── Step 10: PL/pgSQL — old partition cleanup ────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_audit_partitions(
            retention_months INT DEFAULT 36
        )
        RETURNS TEXT AS $$
        DECLARE
            cutoff DATE;
            rec RECORD;
            dropped INT := 0;
        BEGIN
            cutoff := (NOW() - (retention_months || ' months')::INTERVAL)::DATE;

            FOR rec IN
                SELECT inhrelid::regclass::text AS partition_name,
                       pg_get_expr(relpartbound, inhrelid) AS bound_expr
                FROM pg_inherits
                JOIN pg_class ON pg_class.oid = inhrelid
                WHERE inhparent = 'audit_logs'::regclass
            LOOP
                -- Extract upper bound from partition expression
                -- Format: FOR VALUES FROM ('YYYY-MM-DD') TO ('YYYY-MM-DD')
                IF rec.bound_expr ~ 'TO .''(\\d{4}-\\d{2}-\\d{2})''' THEN
                    DECLARE
                        upper_bound DATE;
                    BEGIN
                        upper_bound := (regexp_match(rec.bound_expr, 'TO .''(\\d{4}-\\d{2}-\\d{2})'''))[1]::DATE;
                        IF upper_bound <= cutoff THEN
                            EXECUTE format('DROP TABLE %s', rec.partition_name);
                            dropped := dropped + 1;
                        END IF;
                    END;
                END IF;
            END LOOP;

            RETURN dropped || ' partitions dropped (cutoff: ' || cutoff || ')';
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    # Drop PL/pgSQL functions
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_audit_partitions(INT)")
    op.execute("DROP FUNCTION IF EXISTS create_audit_partition(DATE)")

    # Drop policies and trigger
    op.execute("DROP POLICY IF EXISTS sa_bypass ON audit_logs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")

    # Recreate as regular table
    op.execute("ALTER TABLE audit_logs RENAME TO audit_logs_partitioned")

    op.execute("""
        CREATE TABLE audit_logs (
            id              UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            actor_id        UUID REFERENCES users(id),
            actor_role      user_role,
            action          auditaction NOT NULL,
            resource_type   VARCHAR(50) NOT NULL,
            resource_id     UUID,
            changes         JSONB,
            ip_address      VARCHAR(45),
            user_agent      VARCHAR(500),
            request_id      UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("INSERT INTO audit_logs SELECT * FROM audit_logs_partitioned")
    op.execute("DROP TABLE audit_logs_partitioned CASCADE")

    # Re-create indexes
    op.execute("CREATE INDEX idx_audit_logs_org_id ON audit_logs (organization_id)")
    op.execute("CREATE INDEX idx_audit_logs_actor_id ON audit_logs (actor_id)")
    op.execute("CREATE INDEX idx_audit_logs_action ON audit_logs (action)")
    op.execute("CREATE INDEX idx_audit_logs_resource_type ON audit_logs (resource_type)")
    op.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at)")
    op.execute("""
        CREATE INDEX idx_audit_logs_org_action_created
        ON audit_logs (organization_id, action, created_at)
    """)

    # Re-apply trigger and RLS
    op.execute("""
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()
    """)
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON audit_logs
        USING (organization_id = current_setting('app.current_org_id')::uuid)
    """)
    op.execute("""
        CREATE POLICY sa_bypass ON audit_logs
        USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')
    """)

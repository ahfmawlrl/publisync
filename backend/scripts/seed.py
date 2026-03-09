"""Seed script -- create test accounts and organizations.

Usage:
    cd backend
    python -m scripts.seed          # insert seed data
    python -m scripts.seed --reset  # delete existing seed data and re-insert
"""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import sys
import uuid

from sqlalchemy import text

sys.path.insert(0, ".")

from app.core.database import sync_session_factory
from app.core.security import hash_password
from app.models.enums import OrgPlan, OrgStatus, UserRole, UserStatus

# Fixed UUIDs for idempotent re-runs
AGENCY_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
ORG1_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
ORG2_ID = uuid.UUID("b0000000-0000-0000-0000-000000000002")
USER_SA_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")
USER_AM_ID = uuid.UUID("c0000000-0000-0000-0000-000000000002")
USER_AO_ID = uuid.UUID("c0000000-0000-0000-0000-000000000003")
USER_CD_ID = uuid.UUID("c0000000-0000-0000-0000-000000000004")

PASSWORD = "demo1234!"
PASSWORD_HASH = hash_password(PASSWORD)


SEED_EMAILS = [
    "admin@publisync.kr",
    "manager@digitalsotong.kr",
    "operator@digitalsotong.kr",
    "director@seoul.go.kr",
]


def delete_seed(session) -> None:
    """Delete existing seed data using TRUNCATE CASCADE for clean removal."""
    org_ids = [str(ORG1_ID), str(ORG2_ID)]

    # Use raw connection to disable FK checks via TRUNCATE CASCADE on org-scoped data
    # First, delete all data referencing seed users/orgs
    session.execute(text("""
        DO $$
        DECLARE
            uid uuid;
        BEGIN
            -- Collect seed user IDs
            FOR uid IN SELECT id FROM users WHERE email = ANY(ARRAY[
                'admin@publisync.kr', 'manager@digitalsotong.kr',
                'operator@digitalsotong.kr', 'director@seoul.go.kr'
            ]) LOOP
                DELETE FROM ai_usage_logs WHERE user_id = uid;
                DELETE FROM approval_requests WHERE requested_by = uid OR reviewer_id = uid;
                DELETE FROM calendar_events WHERE created_by = uid;
                DELETE FROM channel_histories WHERE actor_id = uid;
                DELETE FROM comments WHERE processed_by = uid;
                DELETE FROM content_versions WHERE changed_by = uid;
                DELETE FROM contents WHERE author_id = uid;
                DELETE FROM media_assets WHERE created_by = uid;
                DELETE FROM notifications WHERE user_id = uid;
                DELETE FROM notification_settings WHERE user_id = uid;
                DELETE FROM reports WHERE created_by = uid;
                DELETE FROM invitations WHERE invited_by = uid;
                DELETE FROM system_announcements WHERE created_by = uid;
                DELETE FROM password_reset_tokens WHERE user_id = uid;
                DELETE FROM refresh_tokens WHERE user_id = uid;
                DELETE FROM user_organizations WHERE user_id = uid;
            END LOOP;

            -- Delete seed users
            DELETE FROM users WHERE email = ANY(ARRAY[
                'admin@publisync.kr', 'manager@digitalsotong.kr',
                'operator@digitalsotong.kr', 'director@seoul.go.kr'
            ]);

            -- Clean up org-scoped data for seed orgs
            DELETE FROM channels WHERE organization_id = ANY(ARRAY[
                'b0000000-0000-0000-0000-000000000001'::uuid,
                'b0000000-0000-0000-0000-000000000002'::uuid
            ]);
            DELETE FROM organizations WHERE id = ANY(ARRAY[
                'b0000000-0000-0000-0000-000000000001'::uuid,
                'b0000000-0000-0000-0000-000000000002'::uuid
            ]);
            DELETE FROM agencies WHERE id = 'a0000000-0000-0000-0000-000000000001'::uuid;
        END $$;
    """))
    session.commit()
    print("[seed] deleted existing seed data")


def insert_seed(session) -> None:
    # Agency
    session.execute(text("""
        INSERT INTO agencies (id, name, contact_email, contact_phone, is_active, created_at, updated_at)
        VALUES (:id, :name, :email, :phone, TRUE, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(AGENCY_ID), "name": "디지털소통", "email": "contact@digitalsotong.kr", "phone": "02-1234-5678"})

    # Organizations
    orgs = [
        (ORG1_ID, "서울특별시 디지털정책과", "seoul-digital", OrgPlan.PRO.value, "digital@seoul.go.kr", "02-2133-0000"),
        (ORG2_ID, "부산광역시 홍보담당관실", "busan-pr", OrgPlan.BASIC.value, "pr@busan.go.kr", "051-888-0000"),
    ]
    for oid, name, slug, plan, email, phone in orgs:
        session.execute(text("""
            INSERT INTO organizations (id, name, slug, status, plan, contact_email, contact_phone,
                                       settings, storage_used_bytes, storage_quota_bytes, agency_id,
                                       created_at, updated_at)
            VALUES (:id, :name, :slug, :status, :plan, :email, :phone,
                    '{}', 0, 53687091200, :agency_id, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": str(oid), "name": name, "slug": slug,
            "status": OrgStatus.ACTIVE.value, "plan": plan,
            "email": email, "phone": phone, "agency_id": str(AGENCY_ID),
        })

    # Users
    users = [
        (USER_SA_ID, "admin@publisync.kr", "김관리자", UserRole.SYSTEM_ADMIN.value, None),
        (USER_AM_ID, "manager@digitalsotong.kr", "이매니저", UserRole.AGENCY_MANAGER.value, ORG1_ID),
        (USER_AO_ID, "operator@digitalsotong.kr", "박실무자", UserRole.AGENCY_OPERATOR.value, ORG1_ID),
        (USER_CD_ID, "director@seoul.go.kr", "최담당자", UserRole.CLIENT_DIRECTOR.value, ORG1_ID),
    ]
    for uid, email, name, role, org_id in users:
        session.execute(text("""
            INSERT INTO users (id, email, password_hash, name, role, status,
                               organization_id, preferences, failed_login_count,
                               created_at, updated_at)
            VALUES (:id, :email, :pw, :name, :role, :status,
                    :org_id, '{}', 0, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                name = EXCLUDED.name,
                role = EXCLUDED.role,
                organization_id = EXCLUDED.organization_id,
                updated_at = NOW()
        """), {
            "id": str(uid), "email": email, "pw": PASSWORD_HASH,
            "name": name, "role": role, "status": UserStatus.ACTIVE.value,
            "org_id": str(org_id) if org_id else None,
        })

    # UserOrganization mappings
    mappings = [
        (USER_AM_ID, ORG1_ID, UserRole.AGENCY_MANAGER.value, True),
        (USER_AM_ID, ORG2_ID, UserRole.AGENCY_MANAGER.value, False),
        (USER_AO_ID, ORG1_ID, UserRole.AGENCY_OPERATOR.value, True),
        (USER_CD_ID, ORG1_ID, UserRole.CLIENT_DIRECTOR.value, True),
    ]
    for uid, oid, role, is_primary in mappings:
        mapping_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{uid}-{oid}"))
        session.execute(text("""
            INSERT INTO user_organizations (id, user_id, organization_id, role, is_primary, created_at)
            VALUES (:id, :uid, :oid, :role, :primary, NOW())
            ON CONFLICT DO NOTHING
        """), {"id": mapping_id, "uid": str(uid), "oid": str(oid), "role": role, "primary": is_primary})

    session.commit()
    print("[seed] inserted seed data")


def print_accounts() -> None:
    print()
    print("=" * 62)
    print("  PubliSync Test Accounts")
    print("=" * 62)
    fmt = "  {:<6} {:<30} {}"
    print(fmt.format("Role", "Email", "Password"))
    print("-" * 62)
    print(fmt.format("SA", "admin@publisync.kr", PASSWORD))
    print(fmt.format("AM", "manager@digitalsotong.kr", PASSWORD))
    print(fmt.format("AO", "operator@digitalsotong.kr", PASSWORD))
    print(fmt.format("CD", "director@seoul.go.kr", PASSWORD))
    print("-" * 62)
    print("  Orgs: 서울특별시 디지털정책과, 부산광역시 홍보담당관실")
    print("=" * 62)


def main() -> None:
    parser = argparse.ArgumentParser(description="PubliSync seed data")
    parser.add_argument("--reset", action="store_true", help="delete and re-insert seed data")
    args = parser.parse_args()

    with sync_session_factory() as session:
        if args.reset:
            delete_seed(session)
        insert_seed(session)

    print_accounts()


if __name__ == "__main__":
    main()

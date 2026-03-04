#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# PubliSync Database Backup Script
# Usage: ./docker/scripts/backup.sh [--retention-days N]
#
# Crontab example (daily at 03:00):
#   0 3 * * * /opt/publisync/docker/scripts/backup.sh >> /var/log/publisync-backup.log 2>&1
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_ROOT="${PROJECT_ROOT}/backups"
RETENTION_DAYS=30
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
DB_CONTAINER="publisync-postgres-1"
DB_USER="publisync"
DB_NAME="publisync"

# ── Parse arguments ──────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --retention-days)
            shift
            RETENTION_DAYS="$1"
            shift
            ;;
        --retention-days=*)
            RETENTION_DAYS="${arg#*=}"
            ;;
        --help|-h)
            echo "Usage: $0 [--retention-days N]"
            echo "  --retention-days N   Number of days to retain backups (default: 30)"
            exit 0
            ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────
log() {
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[${ts}] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

# ── Verify prerequisites ────────────────────────────────
if ! docker ps --format '{{.Names}}' | grep -q "${DB_CONTAINER}"; then
    # Try alternative container name pattern
    DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "postgres" | head -1)
    if [ -z "${DB_CONTAINER}" ]; then
        error "PostgreSQL container not found. Is the service running?"
    fi
    log "Using container: ${DB_CONTAINER}"
fi

# ── 1. Create backup directory ───────────────────────────
log "Creating backup directory: ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"

# ── 2. Run pg_dump ───────────────────────────────────────
DUMP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
log "Starting database backup..."

docker exec "${DB_CONTAINER}" \
    pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=custom \
        --compress=6 \
        --verbose \
        --file="/tmp/backup_${TIMESTAMP}.dump" \
    2>&1 | while read -r line; do log "pg_dump: ${line}"; done

# Copy the dump file out of the container
docker cp "${DB_CONTAINER}:/tmp/backup_${TIMESTAMP}.dump" "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" \
    || error "Failed to copy dump file from container."

# Also create a plain SQL backup (gzipped) for portability
log "Creating compressed SQL backup..."
docker exec "${DB_CONTAINER}" \
    pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
    | gzip > "${DUMP_FILE}" \
    || error "Failed to create SQL backup."

# Cleanup temp file inside container
docker exec "${DB_CONTAINER}" rm -f "/tmp/backup_${TIMESTAMP}.dump"

# ── 3. Verify backup ────────────────────────────────────
DUMP_SIZE=$(stat -c%s "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" 2>/dev/null || stat -f%z "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" 2>/dev/null || echo "0")
SQL_SIZE=$(stat -c%s "${DUMP_FILE}" 2>/dev/null || stat -f%z "${DUMP_FILE}" 2>/dev/null || echo "0")

if [ "${DUMP_SIZE}" -eq 0 ] && [ "${SQL_SIZE}" -eq 0 ]; then
    error "Backup files are empty. Backup may have failed."
fi

log "Backup created:"
log "  Custom format: ${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump ($(numfmt --to=iec "${DUMP_SIZE}" 2>/dev/null || echo "${DUMP_SIZE} bytes"))"
log "  SQL (gzipped): ${DUMP_FILE} ($(numfmt --to=iec "${SQL_SIZE}" 2>/dev/null || echo "${SQL_SIZE} bytes"))"

# ── 4. Create checksum ──────────────────────────────────
log "Generating checksums..."
cd "${BACKUP_DIR}"
sha256sum * > checksums.sha256 2>/dev/null || shasum -a 256 * > checksums.sha256 2>/dev/null
cd "${PROJECT_ROOT}"
log "Checksums saved to ${BACKUP_DIR}/checksums.sha256"

# ── 5. Cleanup old backups ──────────────────────────────
log "Removing backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=0
if [ -d "${BACKUP_ROOT}" ]; then
    while IFS= read -r -d '' old_backup; do
        rm -rf "${old_backup}"
        DELETED_COUNT=$((DELETED_COUNT + 1))
        log "Deleted old backup: $(basename "${old_backup}")"
    done < <(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -print0 2>/dev/null)
fi
log "Cleaned up ${DELETED_COUNT} old backup(s)."

# ── Summary ──────────────────────────────────────────────
TOTAL_BACKUPS=$(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "${BACKUP_ROOT}" 2>/dev/null | cut -f1)

log "========================================="
log "Backup completed successfully!"
log "  Backup location: ${BACKUP_DIR}"
log "  Total backups:   ${TOTAL_BACKUPS}"
log "  Total disk used: ${TOTAL_SIZE}"
log "  Retention:       ${RETENTION_DAYS} days"
log "========================================="

#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# PubliSync Production Deployment Script
# Usage: ./docker/scripts/deploy.sh [--skip-pull] [--skip-build-frontend]
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
HEALTH_URL="http://localhost/health"
HEALTH_RETRIES=30
HEALTH_INTERVAL=2
LOG_FILE="${PROJECT_ROOT}/deploy-$(date +%Y%m%d-%H%M%S).log"

# ── Helpers ──────────────────────────────────────────────
log() {
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[${timestamp}] $*" | tee -a "${LOG_FILE}"
}

error() {
    log "ERROR: $*"
    exit 1
}

# ── Parse arguments ──────────────────────────────────────
SKIP_PULL=false
SKIP_BUILD_FE=false

for arg in "$@"; do
    case $arg in
        --skip-pull)          SKIP_PULL=true ;;
        --skip-build-frontend) SKIP_BUILD_FE=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-pull] [--skip-build-frontend]"
            echo "  --skip-pull             Skip git pull"
            echo "  --skip-build-frontend   Skip frontend build (assumes dist/ exists)"
            exit 0
            ;;
        *) error "Unknown argument: ${arg}" ;;
    esac
done

cd "${PROJECT_ROOT}"
log "Starting deployment from ${PROJECT_ROOT}"

# ── 1. Pull latest code ─────────────────────────────────
if [ "${SKIP_PULL}" = false ]; then
    log "Step 1/7: Pulling latest code..."
    git pull --ff-only origin main || error "git pull failed. Resolve conflicts manually."
    log "Code updated successfully."
else
    log "Step 1/7: Skipping git pull (--skip-pull)."
fi

# ── 2. Build backend images ─────────────────────────────
log "Step 2/7: Building Docker images..."
docker compose ${COMPOSE_FILES} build --parallel || error "Docker build failed."
log "Docker images built successfully."

# ── 3. Build frontend ───────────────────────────────────
if [ "${SKIP_BUILD_FE}" = false ]; then
    log "Step 3/7: Building frontend..."
    if [ -f "${PROJECT_ROOT}/frontend/package.json" ]; then
        docker run --rm \
            -v "${PROJECT_ROOT}/frontend:/app" \
            -w /app \
            node:22-alpine \
            sh -c "corepack enable && pnpm install --frozen-lockfile && pnpm build"
        log "Frontend built successfully."
    else
        log "WARNING: frontend/package.json not found. Skipping frontend build."
    fi
else
    log "Step 3/7: Skipping frontend build (--skip-build-frontend)."
fi

# Verify frontend dist exists
if [ ! -d "${PROJECT_ROOT}/frontend/dist" ]; then
    error "frontend/dist/ directory not found. Build frontend first or use --skip-build-frontend if dist/ is pre-built."
fi

# ── 4. Run database migrations ───────────────────────────
log "Step 4/7: Running database migrations..."
# Start only the database first to run migrations
docker compose ${COMPOSE_FILES} up -d postgres redis
log "Waiting for PostgreSQL to be ready..."
sleep 5

docker compose ${COMPOSE_FILES} run --rm api \
    alembic upgrade head || error "Database migration failed."
log "Migrations completed successfully."

# ── 5. Start all services ────────────────────────────────
log "Step 5/7: Starting all services..."
docker compose ${COMPOSE_FILES} up -d || error "Failed to start services."
log "All services started."

# ── 6. Health check ──────────────────────────────────────
log "Step 6/7: Running health check..."
healthy=false
for i in $(seq 1 ${HEALTH_RETRIES}); do
    if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
        healthy=true
        break
    fi
    log "Health check attempt ${i}/${HEALTH_RETRIES}... waiting ${HEALTH_INTERVAL}s"
    sleep "${HEALTH_INTERVAL}"
done

if [ "${healthy}" = true ]; then
    log "Health check passed."
else
    log "WARNING: Health check failed after ${HEALTH_RETRIES} attempts."
    log "Checking service status..."
    docker compose ${COMPOSE_FILES} ps | tee -a "${LOG_FILE}"
    docker compose ${COMPOSE_FILES} logs --tail=50 api nginx | tee -a "${LOG_FILE}"
    error "Deployment health check failed. Services may not be running correctly."
fi

# ── 7. Cleanup ────────────────────────────────────────────
log "Step 7/7: Cleaning up old Docker images..."
docker image prune -f | tee -a "${LOG_FILE}"
log "Cleanup completed."

# ── Summary ──────────────────────────────────────────────
log "========================================="
log "Deployment completed successfully!"
log "Log file: ${LOG_FILE}"
log ""
log "Service status:"
docker compose ${COMPOSE_FILES} ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | tee -a "${LOG_FILE}"
log "========================================="

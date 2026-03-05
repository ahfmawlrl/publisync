from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import admin as admin_router
from app.api.v1 import ai as ai_router
from app.api.v1 import analytics as analytics_router
from app.api.v1 import approvals as approvals_router
from app.api.v1 import audit_logs as audit_logs_router
from app.api.v1 import auth as auth_router
from app.api.v1 import calendar as calendar_router
from app.api.v1 import channels as channels_router
from app.api.v1 import comments as comments_router
from app.api.v1 import contents as contents_router
from app.api.v1 import dashboard as dashboard_router
from app.api.v1 import media as media_router
from app.api.v1 import notifications as notifications_router
from app.api.v1 import organizations as org_router
from app.api.v1 import reply_templates as reply_templates_router
from app.api.v1 import reports as reports_router
from app.api.v1 import search as search_router
from app.api.v1 import settings_notifications as settings_notifications_router
from app.api.v1 import sse as sse_router
from app.api.v1 import users as users_router
from app.api.v1 import workspaces as workspaces_router
from app.core.config import settings
from app.core.exceptions import PubliSyncError, publisync_error_handler
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup / shutdown events."""
    # startup
    setup_logging(json_format=not settings.DEBUG)

    from app.core.database import engine
    from app.core.redis import redis_client

    await redis_client.ping()
    yield
    # shutdown
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="PubliSync API",
    version="0.1.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

logger = structlog.get_logger()


# ── Exception handlers ────────────────────────────────────
app.add_exception_handler(PubliSyncError, publisync_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력 데이터 검증에 실패했습니다.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다.",
            },
        },
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", error=str(exc), error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다.",
            },
        },
    )

# ── Middleware (순서: 아래→위로 실행, ③→②→① 순서로 등록) ──
# ③ CORS (가장 바깥)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ② RequestId
app.add_middleware(RequestIdMiddleware)
# ① RateLimit
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ── Health check ──────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "publisync-api"}


# ── Routers ───────────────────────────────────────────────
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(ai_router.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["users"])
app.include_router(users_router.roles_router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(workspaces_router.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(org_router.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(calendar_router.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(channels_router.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(comments_router.router, prefix="/api/v1/comments", tags=["comments"])
app.include_router(contents_router.router, prefix="/api/v1/contents", tags=["contents"])
app.include_router(approvals_router.router, prefix="/api/v1/approvals", tags=["approvals"])
app.include_router(dashboard_router.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(media_router.router, prefix="/api/v1/media", tags=["media"])
app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(
    settings_notifications_router.router,
    prefix="/api/v1/notification-settings",
    tags=["notification-settings"],
)
app.include_router(analytics_router.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(audit_logs_router.router, prefix="/api/v1/audit-logs", tags=["audit-logs"])
app.include_router(reply_templates_router.router, prefix="/api/v1/reply-templates", tags=["reply-templates"])
app.include_router(reports_router.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(search_router.router, prefix="/api/v1/search", tags=["search"])
app.include_router(sse_router.router, prefix="/api/v1/sse", tags=["sse"])

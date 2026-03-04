from fastapi import Request
from fastapi.responses import JSONResponse


class PubliSyncError(Exception):
    """Base exception for all PubliSync errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


# ── 401 Authentication ────────────────────────────────────
class AuthenticationError(PubliSyncError):
    status_code = 401
    detail = "Authentication failed"


class InvalidCredentialsError(AuthenticationError):
    detail = "Invalid email or password"


class TokenExpiredError(AuthenticationError):
    detail = "Token has expired"


class AccountLockedError(PubliSyncError):
    status_code = 423
    detail = "Account is locked due to multiple failed login attempts"


# ── 403 Authorization ─────────────────────────────────────
class AuthorizationError(PubliSyncError):
    status_code = 403
    detail = "Insufficient permissions"


class InsufficientRoleError(AuthorizationError):
    detail = "Your role does not have access to this resource"


class CrossTenantAccessError(AuthorizationError):
    detail = "Cannot access data from another organization"


# ── 404 Not Found ─────────────────────────────────────────
class NotFoundError(PubliSyncError):
    status_code = 404
    detail = "Resource not found"


class ContentNotFoundError(NotFoundError):
    detail = "Content not found"


class UserNotFoundError(NotFoundError):
    detail = "User not found"


class ChannelNotFoundError(NotFoundError):
    detail = "Channel not found"


# ── 409 Conflict ──────────────────────────────────────────
class ConflictError(PubliSyncError):
    status_code = 409
    detail = "Resource conflict"


class DuplicateEmailError(ConflictError):
    detail = "A user with this email already exists"


class WorkflowStateConflictError(ConflictError):
    detail = "Invalid workflow state transition"


# ── 400 Validation ────────────────────────────────────────
class ValidationError(PubliSyncError):
    status_code = 400
    detail = "Validation failed"


class PlatformConstraintError(ValidationError):
    detail = "Content does not meet platform constraints"


# ── 502 External Service ──────────────────────────────────
class ExternalServiceError(PubliSyncError):
    status_code = 502
    detail = "External service error"


class PlatformApiError(ExternalServiceError):
    detail = "Social media platform API error"


class AiServiceError(ExternalServiceError):
    detail = "AI service error or timeout"


class EmailDeliveryError(ExternalServiceError):
    detail = "Email delivery failed"


# ── 429 Rate Limit ────────────────────────────────────────
class RateLimitError(PubliSyncError):
    status_code = 429
    detail = "Too many requests"


class PlatformRateLimitError(RateLimitError):
    detail = "Platform API rate limit exceeded"


# ── Global exception handler ──────────────────────────────
async def publisync_error_handler(request: Request, exc: PubliSyncError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": type(exc).__name__,
                "message": exc.detail,
            },
        },
    )

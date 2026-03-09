"""SSE (Server-Sent Events) endpoint — real-time notifications."""

import asyncio
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context
from app.core.exceptions import AuthenticationError, CrossTenantAccessError
from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

router = APIRouter()
logger = structlog.get_logger()


async def _get_sse_context(
    request: Request,
    token: str | None = Query(None, description="JWT token (for EventSource clients)"),
    workspace: str | None = Query(None, alias="workspace", description="Workspace org ID"),
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceContext:
    """Resolve auth + workspace for SSE — supports query-param token for EventSource.

    EventSource API cannot set custom headers, so we accept the JWT token
    and workspace ID as query parameters as an alternative to the standard
    Authorization header + X-Workspace-Id header flow.
    """
    # Try Authorization header first, fall back to query param
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header.removeprefix("Bearer ")
    elif token:
        jwt_token = token
    else:
        raise AuthenticationError("인증 토큰이 필요합니다")

    payload = decode_access_token(jwt_token)

    # Redis blacklist check
    jti = payload.get("jti")
    if jti and await redis_client.exists(f"jwt:blacklist:{jti}"):
        raise AuthenticationError("Token has been revoked")

    user_id = UUID(payload["sub"])
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    if user.status.value != "ACTIVE":
        raise AuthenticationError("Account is not active")

    # Resolve workspace: X-Workspace-Id header or query param
    ws_id = request.headers.get("X-Workspace-Id") or workspace
    if not ws_id:
        raise CrossTenantAccessError("X-Workspace-Id header or workspace param is required")

    org_id = UUID(ws_id)

    # SA can access any workspace
    if user.role != UserRole.SYSTEM_ADMIN:
        is_member = await repo.is_org_member(user.id, org_id)
        if not is_member:
            raise CrossTenantAccessError()

    return WorkspaceContext(org_id=org_id, user=user)


async def _event_generator(request: Request, org_id: str, user_id: str):
    """Subscribe to Redis Pub/Sub channels and yield SSE events."""
    channel_name = f"sse:channel:{org_id}:{user_id}"
    org_channel = f"sse:channel:{org_id}:broadcast"

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name, org_channel)

    try:
        # Initial heartbeat
        yield {"event": "connected", "data": json.dumps({"status": "connected"})}

        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield {"event": "message", "data": data}

            # Send heartbeat every 30 seconds to keep connection alive
            yield {"event": "heartbeat", "data": ""}
            await asyncio.sleep(1)
    finally:
        await pubsub.unsubscribe(channel_name, org_channel)
        await pubsub.aclose()


@router.get("/events")
async def sse_events(
    request: Request,
    workspace: WorkspaceContext = Depends(_get_sse_context),
) -> EventSourceResponse:
    """SSE endpoint for real-time notifications.

    Supports authentication via:
    - Standard: Authorization header + X-Workspace-Id header
    - EventSource: ?token=<jwt>&workspace=<org_id> query parameters

    Events emitted:
    - publish_started: Content publishing has started
    - publish_completed: Content published successfully
    - publish_failed: Content publish failed
    - approval_requested: New approval request (for CD)
    - approval_completed: Approval/rejection completed (for AO)
    - channel_status_changed: Channel token expired/refreshed
    """
    return EventSourceResponse(
        _event_generator(request, str(workspace.org_id), str(workspace.user.id)),
        ping=30,
    )


# ── SSE Event Publisher (used by services/tasks) ─────────

async def publish_sse_event(org_id: str, user_id: str | None, event_type: str, data: dict) -> None:
    """Publish an SSE event via Redis Pub/Sub.

    Args:
        org_id: Target organization
        user_id: Target user (None for broadcast to all org users)
        event_type: Event type name
        data: Event payload
    """
    payload = json.dumps({"event": event_type, **data})

    if user_id:
        channel = f"sse:channel:{org_id}:{user_id}"
    else:
        channel = f"sse:channel:{org_id}:broadcast"

    await redis_client.publish(channel, payload)
    logger.debug("sse_event_published", org_id=org_id, event_type=event_type)

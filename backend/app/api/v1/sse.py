"""SSE (Server-Sent Events) endpoint — real-time notifications."""

import asyncio
import json

import structlog
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.deps import WorkspaceContext, get_workspace_context
from app.core.redis import redis_client

router = APIRouter()
logger = structlog.get_logger()


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
    workspace: WorkspaceContext = Depends(get_workspace_context),
) -> EventSourceResponse:
    """SSE endpoint for real-time notifications.

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

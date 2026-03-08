"""Channels API — 7 endpoints (S4, F12)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.channel import Channel, ChannelHistory
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.channel_repository import ChannelRepository
from app.schemas.channel import (
    ApiStatusResponse,
    ChannelConnectCallbackRequest,
    ChannelConnectInitiateRequest,
    ChannelConnectInitiateResponse,
    ChannelHistoryResponse,
    ChannelResponse,
)
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services.channel_service import ChannelService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> ChannelService:
    return ChannelService(ChannelRepository(db))


def _to_channel_response(ch: Channel) -> ChannelResponse:
    return ChannelResponse(
        id=str(ch.id),
        organization_id=str(ch.organization_id),
        platform=ch.platform.value,
        platform_account_id=ch.platform_account_id,
        name=ch.name,
        status=ch.status.value,
        token_expires_at=ch.token_expires_at.isoformat() if ch.token_expires_at else None,
        metadata=ch.metadata_,
        created_at=ch.created_at.isoformat(),
    )


def _to_history_response(h: ChannelHistory) -> ChannelHistoryResponse:
    return ChannelHistoryResponse(
        id=str(h.id),
        channel_id=str(h.channel_id),
        event_type=h.event_type.value,
        details=h.details,
        actor_id=str(h.actor_id) if h.actor_id else None,
        actor_name=h.actor.name if hasattr(h, "actor") and h.actor else None,
        created_at=h.created_at.isoformat(),
    )


# ── GET /channels ───────────────────────────────────────

@router.get("", response_model=PaginatedResponse[ChannelResponse])
async def list_channels(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    channels, total = await service.list_channels(workspace.org_id, page=page, limit=limit)
    return {
        "success": True,
        "data": [_to_channel_response(ch) for ch in channels],
        "meta": PaginationMeta(total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit),
    }


# ── POST /channels/connect/initiate ─────────────────────

@router.post("/connect/initiate", response_model=ApiResponse[ChannelConnectInitiateResponse])
async def connect_initiate(
    body: ChannelConnectInitiateRequest,
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    auth_url, state = await service.initiate_connect(body.platform, body.redirect_uri, workspace.org_id)
    return {
        "success": True,
        "data": ChannelConnectInitiateResponse(auth_url=auth_url, state=state),
    }


# ── POST /channels/connect/callback ─────────────────────

@router.post("/connect/callback", response_model=ApiResponse[ChannelResponse], status_code=201)
async def connect_callback(
    body: ChannelConnectCallbackRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    channel = await service.handle_callback(
        body.platform, body.code, body.state, body.redirect_uri,
        workspace.org_id, workspace.user.id,
    )
    return {"success": True, "data": _to_channel_response(channel)}


# ── DELETE /channels/:id ─────────────────────────────────

@router.delete("/{channel_id}", status_code=204)
async def disconnect_channel(
    channel_id: UUID,
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> None:
    await service.disconnect(channel_id, workspace.org_id, workspace.user.id)


# ── POST /channels/:id/refresh-token ────────────────────

@router.post("/{channel_id}/refresh-token", response_model=ApiResponse[ChannelResponse])
async def refresh_token(
    channel_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    channel = await service.refresh_channel_token(channel_id, workspace.org_id, workspace.user.id)
    return {"success": True, "data": _to_channel_response(channel)}


# ── GET /channels/:id/history ────────────────────────────

@router.get("/{channel_id}/history", response_model=PaginatedResponse[ChannelHistoryResponse])
async def get_channel_history(
    channel_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    histories, total = await service.get_channel_history(
        channel_id, workspace.org_id, page=page, limit=limit
    )
    return {
        "success": True,
        "data": [_to_history_response(h) for h in histories],
        "meta": PaginationMeta(total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit),
    }


# ── GET /channels/api-status ────────────────────────────

@router.get("/api-status", response_model=ApiResponse[list[ApiStatusResponse]])
async def get_api_status(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ChannelService = Depends(_get_service),
) -> dict:
    statuses = await service.get_api_status(workspace.org_id)
    return {"success": True, "data": statuses}

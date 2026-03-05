"""Channel integration business logic — S4 (F12)."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from app.core.encryption import decrypt_token, encrypt_token
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.integrations.platforms import get_adapter
from app.models.channel import Channel, ChannelHistory
from app.models.enums import ChannelEventType, ChannelStatus, PlatformType
from app.repositories.channel_repository import ChannelRepository

logger = structlog.get_logger()

# Redis key for OAuth state validation
OAUTH_STATE_PREFIX = "oauth:state:"
OAUTH_STATE_TTL = 600  # 10 minutes


class ChannelService:
    def __init__(self, repo: ChannelRepository) -> None:
        self._repo = repo

    async def list_channels(self, org_id: UUID, page: int = 1, limit: int = 20) -> tuple[list[Channel], int]:
        offset = (page - 1) * limit
        return await self._repo.list_channels(org_id, offset=offset, limit=limit)

    async def get_channel(self, channel_id: UUID, org_id: UUID) -> Channel:
        channel = await self._repo.get_by_id(channel_id)
        if channel is None or channel.organization_id != org_id:
            raise NotFoundError("Channel not found")
        return channel

    async def initiate_connect(
        self, platform: PlatformType, redirect_uri: str, org_id: UUID
    ) -> tuple[str, str]:
        """Start OAuth flow: return (auth_url, state)."""
        from app.core.redis import redis_client

        adapter = get_adapter(platform)
        state = secrets.token_urlsafe(32)

        # Store state→org_id mapping in Redis
        await redis_client.setex(
            f"{OAUTH_STATE_PREFIX}{state}", OAUTH_STATE_TTL, f"{org_id}:{platform.value}"
        )

        auth_url = await adapter.get_auth_url(redirect_uri, state)
        return auth_url, state

    async def handle_callback(
        self, platform: PlatformType, code: str, state: str, redirect_uri: str, org_id: UUID, actor_id: UUID
    ) -> Channel:
        """Handle OAuth callback: exchange code, create/update channel."""
        from app.core.redis import redis_client

        # Validate state
        stored = await redis_client.get(f"{OAUTH_STATE_PREFIX}{state}")
        if not stored:
            raise ExternalServiceError("OAuth state expired or invalid")
        await redis_client.delete(f"{OAUTH_STATE_PREFIX}{state}")

        adapter = get_adapter(platform)

        try:
            token_info = await adapter.exchange_code(code, redirect_uri)
            channel_info = await adapter.get_channel_info(token_info.access_token)
        except Exception as e:
            logger.error("oauth_callback_failed", platform=platform.value, error=str(e))
            raise ExternalServiceError(f"OAuth callback failed: {e}") from e

        # Check for existing channel
        existing = await self._repo.get_by_org_platform_account(
            org_id, platform.value, channel_info.platform_account_id
        )

        expires_at = None
        if token_info.expires_in:
            expires_at = datetime.now(UTC) + timedelta(seconds=token_info.expires_in)

        if existing:
            # Update tokens
            await self._repo.update(existing, {
                "name": channel_info.name,
                "status": ChannelStatus.ACTIVE,
                "access_token_enc": encrypt_token(token_info.access_token),
                "refresh_token_enc": (
                    encrypt_token(token_info.refresh_token)
                    if token_info.refresh_token else existing.refresh_token_enc
                ),
                "token_expires_at": expires_at,
                "metadata_": channel_info.metadata,
            })
            channel = existing
        else:
            channel = Channel(
                organization_id=org_id,
                platform=platform,
                platform_account_id=channel_info.platform_account_id,
                name=channel_info.name,
                status=ChannelStatus.ACTIVE,
                access_token_enc=encrypt_token(token_info.access_token),
                refresh_token_enc=encrypt_token(token_info.refresh_token) if token_info.refresh_token else None,
                token_expires_at=expires_at,
                metadata_=channel_info.metadata,
            )
            channel = await self._repo.create(channel)

        # Record history
        await self._repo.add_history(ChannelHistory(
            channel_id=channel.id,
            organization_id=org_id,
            event_type=ChannelEventType.CONNECTED,
            details={"platform_account_id": channel_info.platform_account_id, "name": channel_info.name},
            actor_id=actor_id,
        ))

        logger.info("channel_connected", channel_id=str(channel.id), platform=platform.value)
        return channel

    async def disconnect(self, channel_id: UUID, org_id: UUID, actor_id: UUID) -> None:
        channel = await self.get_channel(channel_id, org_id)

        await self._repo.add_history(ChannelHistory(
            channel_id=channel.id,
            organization_id=org_id,
            event_type=ChannelEventType.DISCONNECTED,
            actor_id=actor_id,
        ))

        await self._repo.delete(channel)
        logger.info("channel_disconnected", channel_id=str(channel_id))

    async def refresh_channel_token(self, channel_id: UUID, org_id: UUID, actor_id: UUID | None = None) -> Channel:
        """Manually refresh a channel's token."""
        channel = await self.get_channel(channel_id, org_id)

        if not channel.refresh_token_enc:
            raise ExternalServiceError("No refresh token available for this channel")

        adapter = get_adapter(channel.platform)
        refresh_tok = decrypt_token(channel.refresh_token_enc)

        try:
            token_info = await adapter.refresh_token(refresh_tok)
        except Exception as e:
            logger.error("token_refresh_failed", channel_id=str(channel_id), error=str(e))
            await self._repo.update(channel, {"status": ChannelStatus.EXPIRED})
            await self._repo.add_history(ChannelHistory(
                channel_id=channel.id,
                organization_id=org_id,
                event_type=ChannelEventType.TOKEN_EXPIRED,
                details={"error": str(e)},
                actor_id=actor_id,
            ))
            raise ExternalServiceError(f"Token refresh failed: {e}") from e

        expires_at = None
        if token_info.expires_in:
            expires_at = datetime.now(UTC) + timedelta(seconds=token_info.expires_in)

        await self._repo.update(channel, {
            "status": ChannelStatus.ACTIVE,
            "access_token_enc": encrypt_token(token_info.access_token),
            "refresh_token_enc": (
                encrypt_token(token_info.refresh_token)
                if token_info.refresh_token else channel.refresh_token_enc
            ),
            "token_expires_at": expires_at,
        })

        await self._repo.add_history(ChannelHistory(
            channel_id=channel.id,
            organization_id=org_id,
            event_type=ChannelEventType.TOKEN_REFRESHED,
            actor_id=actor_id,
        ))

        logger.info("channel_token_refreshed", channel_id=str(channel_id))
        return channel

    async def get_channel_history(
        self, channel_id: UUID, org_id: UUID, page: int = 1, limit: int = 50
    ) -> tuple[list[ChannelHistory], int]:
        # Verify channel belongs to org
        await self.get_channel(channel_id, org_id)
        offset = (page - 1) * limit
        return await self._repo.list_history(channel_id, offset=offset, limit=limit)

    async def get_api_status(self, org_id: UUID) -> list[dict]:
        """Get API rate limit status for all platforms."""
        from app.core.redis import redis_client

        statuses = []
        for platform in PlatformType:
            adapter = get_adapter(platform)
            config = adapter.get_rate_limit_config()
            key = f"ratelimit:{platform.value}:{org_id}"
            used = int(await redis_client.get(key) or 0)
            limit_val = config.get("requests_per_hour", config.get("daily_quota_units", 0))
            statuses.append({
                "platform": platform.value,
                "requests_used": used,
                "requests_limit": limit_val,
                "window": config.get("window", ""),
                "percentage_used": round((used / limit_val * 100) if limit_val else 0, 1),
            })
        return statuses

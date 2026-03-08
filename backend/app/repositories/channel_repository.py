"""Repository for Channel and ChannelHistory."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, ChannelHistory
from app.models.enums import ChannelStatus


class ChannelRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Channel ─────────────────────────────────────────

    async def get_by_id(self, channel_id: UUID) -> Channel | None:
        return await self._db.get(Channel, channel_id)

    async def list_channels(
        self, org_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Channel], int]:
        base = select(Channel).where(Channel.organization_id == org_id)
        count_q = select(func.count()).select_from(Channel).where(Channel.organization_id == org_id)

        total = (await self._db.execute(count_q)).scalar() or 0
        stmt = base.order_by(Channel.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_org_platform_account(
        self, org_id: UUID, platform: str, platform_account_id: str
    ) -> Channel | None:
        stmt = select(Channel).where(
            Channel.organization_id == org_id,
            Channel.platform == platform,
            Channel.platform_account_id == platform_account_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, channel: Channel) -> Channel:
        self._db.add(channel)
        await self._db.flush()
        return channel

    async def update(self, channel: Channel, data: dict) -> Channel:
        for key, value in data.items():
            setattr(channel, key, value)
        await self._db.flush()
        return channel

    async def delete(self, channel: Channel) -> None:
        await self._db.delete(channel)
        await self._db.flush()

    async def get_expiring_channels(self, before: datetime) -> list[Channel]:
        """Get channels whose tokens expire before given datetime."""
        stmt = select(Channel).where(
            Channel.status == ChannelStatus.ACTIVE,
            Channel.token_expires_at.isnot(None),
            Channel.token_expires_at < before,
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ── ChannelHistory ──────────────────────────────────

    async def add_history(self, history: ChannelHistory) -> None:
        self._db.add(history)
        await self._db.flush()

    async def list_history(
        self, channel_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[ChannelHistory], int]:
        base = select(ChannelHistory).where(ChannelHistory.channel_id == channel_id)
        count_q = select(func.count()).select_from(ChannelHistory).where(ChannelHistory.channel_id == channel_id)

        total = (await self._db.execute(count_q)).scalar() or 0
        stmt = (
            base.options(selectinload(ChannelHistory.actor))
            .order_by(ChannelHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

"""Platform adapter factory."""

from app.core.config import settings
from app.integrations.platforms.base import PlatformAdapter
from app.integrations.platforms.stub import StubAdapter
from app.integrations.platforms.youtube import YouTubeAdapter
from app.models.enums import PlatformType


def get_adapter(platform: PlatformType) -> PlatformAdapter:
    """Factory: return the appropriate adapter for the given platform."""
    if platform == PlatformType.YOUTUBE:
        return YouTubeAdapter(
            client_id=getattr(settings, "YOUTUBE_CLIENT_ID", ""),
            client_secret=getattr(settings, "YOUTUBE_CLIENT_SECRET", ""),
        )
    return StubAdapter(platform.value)

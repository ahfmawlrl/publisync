"""Platform adapter factory."""

from app.core.config import settings
from app.integrations.platforms.base import PlatformAdapter
from app.integrations.platforms.facebook import FacebookAdapter
from app.integrations.platforms.instagram import InstagramAdapter
from app.integrations.platforms.naver_blog import NaverBlogAdapter
from app.integrations.platforms.stub import StubAdapter
from app.integrations.platforms.x_twitter import XTwitterAdapter
from app.integrations.platforms.youtube import YouTubeAdapter
from app.models.enums import PlatformType


def get_adapter(platform: PlatformType) -> PlatformAdapter:
    """Factory: return the appropriate adapter for the given platform."""
    if platform == PlatformType.YOUTUBE:
        return YouTubeAdapter(
            client_id=getattr(settings, "YOUTUBE_CLIENT_ID", ""),
            client_secret=getattr(settings, "YOUTUBE_CLIENT_SECRET", ""),
        )
    if platform == PlatformType.INSTAGRAM:
        return InstagramAdapter(
            app_id=getattr(settings, "META_APP_ID", ""),
            app_secret=getattr(settings, "META_APP_SECRET", ""),
        )
    if platform == PlatformType.FACEBOOK:
        return FacebookAdapter(
            app_id=getattr(settings, "META_APP_ID", ""),
            app_secret=getattr(settings, "META_APP_SECRET", ""),
        )
    if platform == PlatformType.X:
        return XTwitterAdapter(
            client_id=getattr(settings, "X_CLIENT_ID", ""),
            client_secret=getattr(settings, "X_CLIENT_SECRET", ""),
        )
    if platform == PlatformType.NAVER_BLOG:
        return NaverBlogAdapter(
            client_id=getattr(settings, "NAVER_CLIENT_ID", ""),
            client_secret=getattr(settings, "NAVER_CLIENT_SECRET", ""),
        )
    return StubAdapter(platform.value)

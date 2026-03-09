"""Web Push notification integration using pywebpush (Phase 1-B, F13)."""

import json

import structlog
from pywebpush import WebPushException, webpush

from app.core.config import settings

logger = structlog.get_logger()


async def send_web_push(
    subscription_info: dict,
    title: str,
    message: str,
    url: str | None = None,
) -> bool:
    """Send a Web Push notification to a subscribed browser.

    Args:
        subscription_info: PushSubscription JSON from the browser
            (must contain endpoint, keys.p256dh, keys.auth).
        title: Notification title.
        message: Notification body text.
        url: Optional URL to open when clicked.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("webpush_skipped", reason="VAPID keys not configured")
        return False

    payload = json.dumps({
        "title": title,
        "body": message,
        "url": url,
        "icon": "/logo-192.png",
    })

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"},
        )
        logger.info("webpush_sent", endpoint=subscription_info.get("endpoint", "")[:60])
        return True
    except WebPushException as exc:
        status_code = getattr(exc, "response", None)
        status = status_code.status_code if status_code else None
        logger.error(
            "webpush_error",
            status=status,
            detail=str(exc)[:200],
        )
        return False
    except Exception:
        logger.exception("webpush_unexpected_error")
        return False

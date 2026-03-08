"""Telegram Bot API integration — S10 (F07).

Simple wrapper for sending messages via Telegram Bot API.
Uses httpx for async HTTP requests.
"""

import structlog
import httpx

from app.core.config import settings

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to a Telegram chat.

    Args:
        chat_id: Telegram chat ID or username.
        text: Message text (HTML formatting supported).
        parse_mode: Message parse mode (default: HTML).

    Returns:
        True if message was sent successfully, False otherwise.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("telegram_send_skipped", reason="TELEGRAM_BOT_TOKEN not configured")
        return False

    url = f"{TELEGRAM_API_BASE.format(token=token)}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info("telegram_message_sent", chat_id=chat_id)
                return True
            else:
                logger.error(
                    "telegram_api_error",
                    chat_id=chat_id,
                    error_code=result.get("error_code"),
                    description=result.get("description"),
                )
                return False
    except httpx.HTTPStatusError as e:
        logger.error(
            "telegram_http_error",
            chat_id=chat_id,
            status_code=e.response.status_code,
            detail=str(e),
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "telegram_request_error",
            chat_id=chat_id,
            detail=str(e),
        )
        return False

"""Email sending service using FastAPI-Mail."""

import structlog
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

logger = structlog.get_logger()

_mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,
    USE_CREDENTIALS=bool(settings.MAIL_USERNAME),
)

_fast_mail = FastMail(_mail_config)


async def send_password_reset_email(email: str, token: str) -> None:
    """Send password reset email with the reset link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_body = f"""\
<div style="font-family: 'Pretendard', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1677ff;">PubliSync 비밀번호 재설정</h2>
  <p>비밀번호 재설정을 요청하셨습니다.</p>
  <p>아래 버튼을 클릭하여 새 비밀번호를 설정해 주세요.</p>
  <div style="text-align: center; margin: 32px 0;">
    <a href="{reset_url}"
       style="display: inline-block; padding: 12px 32px; background-color: #1677ff;
              color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600;">
      비밀번호 재설정
    </a>
  </div>
  <p style="color: #666; font-size: 14px;">
    이 링크는 1시간 동안 유효합니다.<br/>
    본인이 요청하지 않은 경우 이 메일을 무시해 주세요.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
  <p style="color: #999; font-size: 12px;">PubliSync — 공공기관 소셜 미디어 통합 관리 플랫폼</p>
</div>"""

    message = MessageSchema(
        subject="[PubliSync] 비밀번호 재설정",
        recipients=[email],
        body=html_body,
        subtype=MessageType.html,
    )

    try:
        await _fast_mail.send_message(message)
        logger.info("password_reset_email_sent", email=email[:3] + "***")
    except Exception:
        logger.error("password_reset_email_failed", email=email[:3] + "***", exc_info=True)

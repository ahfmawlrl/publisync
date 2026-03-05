"""JWT token creation/verification and password hashing."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationError, TokenExpiredError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# ── Password helpers ──────────────────────────────────────


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token helpers (refresh / reset / invite) ──────────────


def generate_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """SHA-256 hash for storing tokens in DB."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── JWT ───────────────────────────────────────────────────


def create_access_token(
    user_id: UUID,
    role: str,
    extra: dict | None = None,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    remember_me: bool = False,
) -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at)."""
    raw = generate_token()
    hashed = hash_token(raw)
    days = 30 if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
    expires_at = datetime.now(UTC) + timedelta(days=days)
    return raw, hashed, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token. Raises on invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise TokenExpiredError() from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    return payload

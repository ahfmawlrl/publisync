"""Fernet symmetric encryption for OAuth tokens."""

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.OAUTH_ENCRYPTION_KEY.encode()
        _fernet = Fernet(key)
    return _fernet


def encrypt_token(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    return _get_fernet().decrypt(cipher.encode()).decode()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── App ────────────────────────────────────────────────
    DEBUG: bool = False
    APP_NAME: str = "PubliSync"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ───────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://publisync:publisync@localhost:5432/publisync"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OAuth Token Encryption ─────────────────────────────
    OAUTH_ENCRYPTION_KEY: str = "change-me-in-production"

    # ── MinIO ──────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "publisync-media"
    MINIO_SECURE: bool = False

    # ── Email ──────────────────────────────────────────────
    MAIL_FROM: str = "noreply@publisync.kr"
    MAIL_SERVER: str = "localhost"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    FRONTEND_URL: str = "http://localhost:5173"

    # ── CORS ───────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Celery ─────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Telegram ──────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""

    # ── Sentry ─────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Platform OAuth — YouTube ────────────────────────────
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""

    # ── Platform OAuth — Instagram / Facebook (Meta) ──────
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""

    # ── Platform OAuth — X (Twitter) ──────────────────────
    X_CLIENT_ID: str = ""
    X_CLIENT_SECRET: str = ""

    # ── Platform OAuth — Naver Blog ───────────────────────
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # ── Platform — OAuth Redirect ─────────────────────────
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:5173/channels/callback"

    # ── AI (litellm) ────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    AI_DEFAULT_MODEL: str = "gpt-4o-mini"
    AI_FALLBACK_MODELS: list[str] = ["claude-sonnet-4-6", "gemini-1.5-flash"]
    AI_MAX_TOKENS: int = 2000
    AI_TIMEOUT: int = 30

    # ── Meilisearch ──────────────────────────────────────────
    MEILI_URL: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str = ""

    # ── Web Push (VAPID) ────────────────────────────────────
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIM_EMAIL: str = "admin@publisync.kr"


settings = Settings()

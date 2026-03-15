"""Celery app configuration — 3 queues: publish, ai, system."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "publisync",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_routes={
        "app.tasks.publish.*": {"queue": "publish"},
        "app.tasks.ai.*": {"queue": "ai"},
        "app.tasks.comment.*": {"queue": "system"},
        "app.tasks.notification.*": {"queue": "system"},
        "app.tasks.system.*": {"queue": "system"},
        "app.tasks.search.*": {"queue": "system"},
        "app.tasks.report.*": {"queue": "ai"},
    },
    task_default_queue="publish",
    broker_connection_retry_on_startup=True,
)

# Celery Beat schedule
celery_app.conf.beat_schedule = {
    # Check for scheduled content ready to publish (every 1 minute)
    "check-scheduled-contents": {
        "task": "app.tasks.publish.check_scheduled_contents",
        "schedule": 60.0,
    },
    # Dashboard cache refresh (every 5 minutes)
    "refresh-dashboard-cache": {
        "task": "app.tasks.system.refresh_dashboard_cache",
        "schedule": 300.0,
    },
    # Token expiry check (every 1 hour)
    "check-token-expiry": {
        "task": "app.tasks.system.check_token_expiry",
        "schedule": 3600.0,
    },
    # Clean expired sessions (every 6 hours)
    "clean-expired-sessions": {
        "task": "app.tasks.system.clean_expired_sessions",
        "schedule": 21600.0,
    },
    # Collect comments from platforms (every 5 minutes)
    "collect-comments": {
        "task": "app.tasks.comment.collect_comments",
        "schedule": 300.0,
    },
    # Sentiment analysis batch (every 10 minutes)
    "analyze-sentiment-batch": {
        "task": "app.tasks.ai.analyze_sentiment_batch",
        "schedule": 600.0,
    },
    # Clean soft-deleted media after 30 days (daily)
    "clean-deleted-media": {
        "task": "app.tasks.system.clean_deleted_media",
        "schedule": 86400.0,
    },
    # Check storage quota usage per organization (daily)
    "check-storage-quota": {
        "task": "app.tasks.system.check_storage_quota",
        "schedule": 86400.0,
    },
    # Meilisearch full reindex — contents (every 1 hour)
    "sync-search-contents": {
        "task": "app.tasks.search.sync_search_index",
        "schedule": 3600.0,
        "args": ["contents"],
    },
    # Meilisearch full reindex — comments (every 1 hour)
    "sync-search-comments": {
        "task": "app.tasks.search.sync_search_index",
        "schedule": 3600.0,
        "args": ["comments"],
    },
    # Meilisearch full reindex — media_assets (every 1 hour)
    "sync-search-media": {
        "task": "app.tasks.search.sync_search_index",
        "schedule": 3600.0,
        "args": ["media_assets"],
    },
    # Create next month's audit_logs partition (daily, idempotent)
    "create-monthly-partition": {
        "task": "app.tasks.system.create_monthly_partition",
        "schedule": 86400.0,
    },
    # Drop audit_logs partitions older than 3 years (daily, idempotent)
    "cleanup-old-partitions": {
        "task": "app.tasks.system.cleanup_old_partitions",
        "schedule": 86400.0,
    },
    # Sync analytics snapshots per organization (every 1 hour)
    "sync-analytics-snapshots": {
        "task": "app.tasks.system.sync_analytics_snapshots",
        "schedule": 3600.0,
    },
}

# Explicitly import all task modules so Celery registers every @task
import app.tasks.ai  # noqa: F401, E402
import app.tasks.publish  # noqa: F401, E402
import app.tasks.comment  # noqa: F401, E402
import app.tasks.system  # noqa: F401, E402
import app.tasks.search  # noqa: F401, E402
import app.tasks.report  # noqa: F401, E402

# Initialize Sentry for Celery workers (workers don't import main.py)
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

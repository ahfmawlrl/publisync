"""Search index sync tasks — full reindex via Celery system queue."""

import structlog
from celery import shared_task

logger = structlog.get_logger()

# ── Row serializers per index ─────────────────────────────


def _serialize_contents(rows: list) -> list[dict]:
    """Serialize Content ORM rows to Meilisearch documents."""
    docs = []
    for row in rows:
        docs.append({
            "id": str(row.id),
            "title": row.title,
            "body": row.body or "",
            "organization_id": str(row.organization_id),
            "status": row.status.value if row.status else "",
            "platforms": row.platforms or [],
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        })
    return docs


def _serialize_comments(rows: list) -> list[dict]:
    """Serialize Comment ORM rows to Meilisearch documents."""
    docs = []
    for row in rows:
        docs.append({
            "id": str(row.id),
            "text": row.text or "",
            "author_name": row.author_name or "",
            "organization_id": str(row.organization_id),
            "platform": row.platform.value if row.platform else "",
            "sentiment": row.sentiment.value if row.sentiment else "",
            "status": row.status.value if row.status else "",
            "created_at": row.created_at.isoformat() if row.created_at else "",
        })
    return docs


def _serialize_media_assets(rows: list) -> list[dict]:
    """Serialize MediaAsset ORM rows to Meilisearch documents."""
    docs = []
    for row in rows:
        docs.append({
            "id": str(row.id),
            "file_name": row.filename or "",
            "original_name": row.original_filename or "",
            "tags": row.tags or [],
            "organization_id": str(row.organization_id),
            "media_type": row.media_type.value if row.media_type else "",
            "folder_id": str(row.folder_id) if row.folder_id else "",
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "file_size": row.file_size or 0,
        })
    return docs


_SERIALIZERS = {
    "contents": _serialize_contents,
    "comments": _serialize_comments,
    "media_assets": _serialize_media_assets,
}


@shared_task(name="app.tasks.search.sync_search_index")
def sync_search_index(index_name: str) -> dict:
    """Full reindex of a single Meilisearch index from the source table.

    Args:
        index_name: One of 'contents', 'comments', 'media_assets'.

    Returns:
        dict with indexed document count or error info.
    """
    from app.core.database import sync_session_factory
    from app.integrations.search import bulk_index, ensure_indexes

    if index_name not in _SERIALIZERS:
        logger.error("sync_search_index_unknown_index", index_name=index_name)
        return {"error": f"Unknown index: {index_name}", "indexed": 0}

    logger.info("sync_search_index_start", index_name=index_name)

    try:
        # Ensure Meilisearch indexes exist with correct settings
        ensure_indexes()

        # Import model dynamically to avoid circular imports
        model_cls = _get_model_class(index_name)

        with sync_session_factory() as session:
            rows = session.query(model_cls).all()
            serializer = _SERIALIZERS[index_name]
            documents = serializer(rows)

        if documents:
            bulk_index(index_name, documents)

        logger.info(
            "sync_search_index_complete",
            index_name=index_name,
            document_count=len(documents),
        )
        return {"index": index_name, "indexed": len(documents)}

    except Exception as exc:
        logger.error(
            "sync_search_index_failed",
            index_name=index_name,
            error=str(exc),
        )
        return {"index": index_name, "indexed": 0, "error": str(exc)}


def _get_model_class(index_name: str):
    """Lazy-import the ORM model class for a given index name."""
    if index_name == "contents":
        from app.models.content import Content
        return Content
    elif index_name == "comments":
        from app.models.comment import Comment
        return Comment
    elif index_name == "media_assets":
        from app.models.media import MediaAsset
        return MediaAsset
    else:
        raise ValueError(f"No model mapping for index: {index_name}")

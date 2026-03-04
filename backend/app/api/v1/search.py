"""Search API — 1 endpoint (S7).

Meilisearch primary with PostgreSQL ILIKE fallback.
"""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context
from app.models.content import Content
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.dashboard import SearchResultItem

logger = structlog.get_logger()

router = APIRouter()


def _meili_hit_to_item(hit: dict, result_type: str) -> SearchResultItem:
    """Convert a single Meilisearch hit to a SearchResultItem."""
    if result_type == "content":
        body = hit.get("body", "") or ""
        snippet = (body[:100] + "...") if len(body) > 100 else body
        return SearchResultItem(
            id=hit.get("id", ""),
            type="content",
            title=hit.get("title", ""),
            snippet=snippet or None,
            status=hit.get("status", ""),
            created_at=hit.get("created_at", ""),
        )
    elif result_type == "comment":
        text = hit.get("text", "") or ""
        snippet = (text[:100] + "...") if len(text) > 100 else text
        return SearchResultItem(
            id=hit.get("id", ""),
            type="comment",
            title=hit.get("author_name", "Comment"),
            snippet=snippet or None,
            status=hit.get("status", ""),
            created_at=hit.get("created_at", ""),
        )
    else:  # media
        return SearchResultItem(
            id=hit.get("id", ""),
            type="media",
            title=hit.get("original_name", hit.get("file_name", "")),
            snippet=None,
            status="",
            created_at=hit.get("created_at", ""),
        )


def _search_meilisearch(
    query: str, org_id: str, limit: int, offset: int
) -> tuple[list[SearchResultItem], int] | None:
    """Try Meilisearch across all indexes. Returns (items, total) or None on failure."""
    try:
        from app.integrations.search import search as meili_search

        org_filter = f'organization_id = "{org_id}"'
        items: list[SearchResultItem] = []
        total = 0

        # Search contents
        content_result = meili_search(
            "contents", query, filters=org_filter, limit=limit, offset=offset
        )
        total += content_result.get("estimatedTotalHits", 0)
        for hit in content_result.get("hits", []):
            items.append(_meili_hit_to_item(hit, "content"))

        # Search comments
        comment_result = meili_search(
            "comments", query, filters=org_filter, limit=limit, offset=offset
        )
        total += comment_result.get("estimatedTotalHits", 0)
        for hit in comment_result.get("hits", []):
            items.append(_meili_hit_to_item(hit, "comment"))

        # Search media assets
        media_result = meili_search(
            "media_assets", query, filters=org_filter, limit=limit, offset=offset
        )
        total += media_result.get("estimatedTotalHits", 0)
        for hit in media_result.get("hits", []):
            items.append(_meili_hit_to_item(hit, "media"))

        # Sort combined results by created_at descending, then trim to limit
        items.sort(key=lambda x: x.created_at, reverse=True)
        items = items[:limit]

        logger.info(
            "search_meilisearch_success",
            query=query,
            total=total,
            returned=len(items),
        )
        return items, total

    except Exception as exc:
        logger.warning("search_meilisearch_fallback", error=str(exc))
        return None


async def _search_ilike(
    query: str, workspace: WorkspaceContext, db: AsyncSession, limit: int, offset: int
) -> tuple[list[SearchResultItem], int]:
    """Fallback: PostgreSQL ILIKE search on contents only."""
    pattern = f"%{query}%"

    base = select(Content).where(
        Content.organization_id == workspace.org_id,
        Content.deleted_at.is_(None),
        Content.title.ilike(pattern),
    )
    count_q = (
        select(func.count())
        .select_from(Content)
        .where(
            Content.organization_id == workspace.org_id,
            Content.deleted_at.is_(None),
            Content.title.ilike(pattern),
        )
    )

    total = (await db.execute(count_q)).scalar() or 0
    stmt = base.order_by(Content.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)

    items = [
        SearchResultItem(
            id=str(c.id),
            type="content",
            title=c.title,
            snippet=(c.body[:100] + "...") if c.body and len(c.body) > 100 else c.body,
            status=c.status.value,
            created_at=c.created_at.isoformat(),
        )
        for c in result.scalars().all()
    ]
    return items, total


# ── GET /search ──────────────────────────────────────────
@router.get("", response_model=PaginatedResponse[SearchResultItem])
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Unified search across contents, comments, and media.

    Tries Meilisearch first; falls back to PostgreSQL ILIKE if Meilisearch is
    unavailable or not configured.
    """
    offset = (page - 1) * limit

    # Try Meilisearch first
    meili_result = _search_meilisearch(q, str(workspace.org_id), limit, offset)

    if meili_result is not None:
        items, total = meili_result
    else:
        # Fallback to PostgreSQL ILIKE (content-only)
        items, total = await _search_ilike(q, workspace, db, limit, offset)

    return {
        "success": True,
        "data": items,
        "meta": PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=(total + limit - 1) // limit if total > 0 else 0,
        ),
    }

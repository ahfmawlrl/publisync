"""Meilisearch 검색 클라이언트"""

import meilisearch
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_client: meilisearch.Client | None = None


def get_client() -> meilisearch.Client:
    global _client
    if _client is None:
        _client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
    return _client


INDEX_CONFIGS = {
    "contents": {
        "searchableAttributes": ["title", "body"],
        "filterableAttributes": ["organization_id", "status", "platforms"],
        "sortableAttributes": ["created_at", "updated_at"],
    },
    "comments": {
        "searchableAttributes": ["text", "author_name"],
        "filterableAttributes": ["organization_id", "platform", "sentiment", "status"],
        "sortableAttributes": ["created_at"],
    },
    "media_assets": {
        "searchableAttributes": ["file_name", "original_name", "tags"],
        "filterableAttributes": ["organization_id", "media_type", "folder_id"],
        "sortableAttributes": ["created_at", "file_size"],
    },
}


def ensure_indexes():
    """인덱스 생성 및 설정 적용"""
    client = get_client()
    for index_name, config in INDEX_CONFIGS.items():
        try:
            client.create_index(index_name, {"primaryKey": "id"})
        except Exception:  # noqa: S110
            pass  # index already exists
        index = client.index(index_name)
        index.update_searchable_attributes(config["searchableAttributes"])
        index.update_filterable_attributes(config["filterableAttributes"])
        index.update_sortable_attributes(config["sortableAttributes"])
    logger.info("meilisearch_indexes_configured", indexes=list(INDEX_CONFIGS.keys()))


def search(
    index_name: str,
    query: str,
    *,
    filters: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Meilisearch 검색 실행"""
    client = get_client()
    index = client.index(index_name)
    params = {"limit": limit, "offset": offset}
    if filters:
        params["filter"] = filters
    return index.search(query, params)


def index_document(index_name: str, document: dict):
    """단일 문서 인덱싱"""
    client = get_client()
    index = client.index(index_name)
    index.add_documents([document])


def delete_document(index_name: str, doc_id: str):
    """문서 삭제"""
    client = get_client()
    index = client.index(index_name)
    index.delete_document(doc_id)


def bulk_index(index_name: str, documents: list[dict]):
    """벌크 인덱싱"""
    client = get_client()
    index = client.index(index_name)
    index.add_documents(documents)

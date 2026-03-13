"""Local storage file serving routes (development only).

These endpoints serve files from the local filesystem when
STORAGE_BACKEND=local. In production (MinIO/S3), files are served
through the /storage proxy or presigned URLs.
"""

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter()


@router.get("/files/{file_path:path}")
async def serve_local_file(file_path: str):
    """Serve a file from local storage.

    Only active when STORAGE_BACKEND=local.
    """
    if settings.STORAGE_BACKEND.lower() != "local":
        return JSONResponse(
            status_code=404,
            content={"error": "Local file serving is disabled in this environment."},
        )

    from app.integrations.storage import get_storage
    from app.integrations.storage.local import LocalStorageBackend

    storage = get_storage()
    if not isinstance(storage, LocalStorageBackend):
        return JSONResponse(
            status_code=404,
            content={"error": "Local file serving is disabled."},
        )

    path = storage.get_file_path(file_path)
    if not path.is_file():
        return JSONResponse(
            status_code=404,
            content={"error": f"File not found: {file_path}"},
        )

    return FileResponse(path)


@router.put("/upload")
async def upload_local_file(
    request: Request,
    object_key: str,
):
    """Accept a file upload for local storage (presigned URL substitute).

    The client PUTs the file body to this endpoint with the object_key
    query parameter that was returned from presigned_upload_url().
    Only active when STORAGE_BACKEND=local.
    """
    if settings.STORAGE_BACKEND.lower() != "local":
        return JSONResponse(
            status_code=404,
            content={"error": "Local upload is disabled in this environment."},
        )

    from app.integrations.storage import get_storage
    from app.integrations.storage.local import LocalStorageBackend

    storage = get_storage()
    if not isinstance(storage, LocalStorageBackend):
        return JSONResponse(
            status_code=404,
            content={"error": "Local upload is disabled."},
        )

    body = await request.body()
    path = storage.get_file_path(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as f:
        f.write(body)

    logger.info("local_file_uploaded_via_api", object_key=object_key, size=len(body))
    return {"success": True, "object_key": object_key}

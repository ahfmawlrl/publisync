"""Reports API — 7 endpoints (S18, F19).

GET    /reports                  — list reports (SA, AM, CD)
POST   /reports/generate         — AI generate report (AM, AO) → 202
GET    /reports/{id}             — report detail (SA, AM, CD)
PUT    /reports/{id}             — edit report (AM, AO)
POST   /reports/{id}/finalize    — finalize report (AM)
GET    /reports/{id}/download    — download PDF (SA, AM, CD)
DELETE /reports/{id}             — delete draft report (AM)
"""

from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.report_repository import ReportRepository
from app.schemas.common import ApiResponse
from app.schemas.report import (
    ReportGenerateRequest,
    ReportListItem,
    ReportResponse,
    ReportUpdateRequest,
)
from app.services.report_service import ReportService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> ReportService:
    return ReportService(ReportRepository(db))


# ── GET /reports ──────────────────────────────────────
@router.get("/", response_model=ApiResponse[list[ReportListItem]])
async def list_reports(
    period: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(
        require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)
    ),
    service: ReportService = Depends(_get_service),
) -> dict:
    reports, total = await service.list_reports(
        workspace.org_id, period=period, status=status_filter, page=page, limit=limit,
    )
    return {
        "success": True,
        "data": [
            ReportListItem(
                id=str(r.id),
                title=r.title,
                period=r.period.value if hasattr(r.period, "value") else str(r.period),
                period_start=r.period_start,
                period_end=r.period_end,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                generated_by=r.generated_by,
                created_at=r.created_at,
                finalized_at=r.finalized_at,
            )
            for r in reports
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


# ── POST /reports/generate ────────────────────────────
@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    body: ReportGenerateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: ReportService = Depends(_get_service),
) -> dict:
    report, job = await service.generate_report(
        org_id=workspace.org_id,
        user_id=workspace.user.id,
        period=body.period,
        period_start=body.period_start,
        period_end=body.period_end,
        include_sections=body.include_sections,
    )
    return {
        "success": True,
        "data": {
            "report_id": str(report.id),
            "job_id": str(job.id),
            "job_type": "REPORT",
            "status": "PENDING",
            "message": "리포트 생성 작업이 대기열에 추가되었습니다.",
        },
    }


# ── GET /reports/{report_id} ──────────────────────────
@router.get("/{report_id}")
async def get_report(
    report_id: str,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(
        require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)
    ),
    service: ReportService = Depends(_get_service),
) -> dict:
    report = await service.get_report(PyUUID(report_id), workspace.org_id)
    if not report:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": "REPORT_NOT_FOUND", "message": "리포트를 찾을 수 없습니다."},
            },
        )
    return {
        "success": True,
        "data": ReportResponse(
            id=str(report.id),
            organization_id=str(report.organization_id),
            title=report.title,
            period=report.period.value if hasattr(report.period, "value") else str(report.period),
            period_start=report.period_start,
            period_end=report.period_end,
            status=report.status.value if hasattr(report.status, "value") else str(report.status),
            content=report.content or {},
            pdf_url=report.pdf_url,
            generated_by=report.generated_by,
            created_by=str(report.created_by),
            finalized_at=report.finalized_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
        ).model_dump(mode="json"),
    }


# ── PUT /reports/{report_id} ─────────────────────────
@router.put("/{report_id}")
async def update_report(
    report_id: str,
    body: ReportUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: ReportService = Depends(_get_service),
) -> dict:
    report = await service.update_report(
        PyUUID(report_id), workspace.org_id, title=body.title, content=body.content,
    )
    if not report:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": "리포트를 찾을 수 없거나 수정할 수 없습니다.",
                },
            },
        )
    return {
        "success": True,
        "data": {
            "id": str(report.id),
            "status": report.status.value if hasattr(report.status, "value") else str(report.status),
        },
    }


# ── POST /reports/{report_id}/finalize ────────────────
@router.post("/{report_id}/finalize")
async def finalize_report(
    report_id: str,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    service: ReportService = Depends(_get_service),
) -> dict:
    report = await service.finalize_report(PyUUID(report_id), workspace.org_id)
    if not report:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": "리포트를 찾을 수 없거나 확정할 수 없습니다.",
                },
            },
        )
    return {"success": True, "data": {"id": str(report.id), "status": "FINALIZED"}}


# ── GET /reports/{report_id}/download ─────────────────
@router.get("/{report_id}/download", response_model=None)
async def download_report(
    report_id: str,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(
        require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)
    ),
    service: ReportService = Depends(_get_service),
):
    pdf_url = await service.get_pdf_url(PyUUID(report_id), workspace.org_id)
    if not pdf_url:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": "PDF_NOT_FOUND", "message": "PDF가 아직 생성되지 않았습니다."},
            },
        )

    try:
        from app.core.config import settings
        from app.integrations.storage import get_minio_client

        minio_client = get_minio_client()
        response = minio_client.get_object(settings.MINIO_BUCKET, pdf_url)
        return StreamingResponse(
            response.stream(32 * 1024),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'},
        )
    except Exception:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": "PDF_NOT_FOUND", "message": "PDF 파일을 불러올 수 없습니다."},
            },
        )


# ── DELETE /reports/{report_id} ──────────────────────
@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    service: ReportService = Depends(_get_service),
) -> None:
    """Delete a draft report. Finalized reports cannot be deleted."""
    deleted = await service.delete_report(PyUUID(report_id), workspace.org_id)
    if not deleted:
        return JSONResponse(  # type: ignore[return-value]
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": "리포트를 찾을 수 없거나 삭제할 수 없습니다.",
                },
            },
        )

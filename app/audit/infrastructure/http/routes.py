from fastapi import APIRouter, Depends

from app.audit.application.dto import GetAuditLogsInput
from app.audit.application.use_cases.get_audit_logs import GetAuditLogsUseCase
from app.audit.infrastructure.composition import get_audit_logs_use_case
from app.audit.infrastructure.http.schemas import AuditLogResponse
from app.auth.infrastructure.http.dependencies import require_super_user
from app.core.types import TokenPayload

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    _payload: TokenPayload = Depends(require_super_user),
    use_case: GetAuditLogsUseCase = Depends(get_audit_logs_use_case),
) -> list[AuditLogResponse]:
    result = await use_case.execute(
        GetAuditLogsInput(page=page, page_size=page_size)
    )
    return [
        AuditLogResponse(
            id=item.id,
            actor_id=item.actor_id,
            action=item.action,
            entity_id=item.entity_id,
            entity_type=item.entity_type,
            payload=item.payload,
            created_at=item.created_at,  # type: ignore[arg-type]
        )
        for item in result.items
    ]

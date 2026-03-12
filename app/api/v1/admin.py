from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_super_user
from app.core.exceptions import (
    AlreadyAssignedError,
    NotFoundError,
    SystemRoleError,
    UniquenessError,
)
from app.db.session import get_db
from app.schemas.role import (
    AssignRoleRequest,
    AuditLogResponse,
    PermissionCreate,
    RoleCreate,
    RoleResponse,
)
from app.services import rbac_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        role = await rbac_service.create_role(db, data, actor_id)
        return RoleResponse.model_validate(role)
    except UniquenessError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        await rbac_service.delete_role(db, role_id, actor_id)
        return
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SystemRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/roles/{role_id}/permissions", status_code=status.HTTP_201_CREATED)
async def assign_permission(
    role_id: str,
    data: PermissionCreate,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        await rbac_service.assign_permission(db, role_id, data, actor_id)
        return
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AlreadyAssignedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/roles/{role_id}/permissions/{scope}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_permission(
    role_id: str,
    scope: str,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        await rbac_service.revoke_permission(db, role_id, scope, actor_id)
        return
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: str,
    data: AssignRoleRequest,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        await rbac_service.assign_role_to_user(db, user_id, data.role_id, actor_id)
        return
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_role_from_user(
    user_id: str,
    role_id: str,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        actor_id = payload.get("sub")
        await rbac_service.revoke_role_from_user(db, user_id, role_id, actor_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    payload: dict = Depends(require_super_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        audit_log = await rbac_service.get_audit_logs(db, page, page_size)
        return [AuditLogResponse.model_validate(log) for log in audit_log]
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

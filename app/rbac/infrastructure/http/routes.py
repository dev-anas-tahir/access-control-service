from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.domain.ports.token_verifier import TokenPayload
from app.auth.infrastructure.http.dependencies import require_super_user
from app.rbac.application.dto import (
    AssignPermissionInput,
    AssignRoleToUserInput,
    CreateRoleInput,
    DeleteRoleInput,
    RevokePermissionInput,
    RevokeRoleFromUserInput,
)
from app.rbac.application.use_cases.assign_permission import AssignPermissionUseCase
from app.rbac.application.use_cases.assign_role_to_user import AssignRoleToUserUseCase
from app.rbac.application.use_cases.create_role import CreateRoleUseCase
from app.rbac.application.use_cases.delete_role import DeleteRoleUseCase
from app.rbac.application.use_cases.revoke_permission import RevokePermissionUseCase
from app.rbac.application.use_cases.revoke_role_from_user import (
    RevokeRoleFromUserUseCase,
)
from app.rbac.infrastructure.composition import (
    get_assign_permission_use_case,
    get_assign_role_to_user_use_case,
    get_create_role_use_case,
    get_delete_role_use_case,
    get_revoke_permission_use_case,
    get_revoke_role_from_user_use_case,
)
from app.rbac.infrastructure.http.schemas import (
    AssignRoleRequest,
    PermissionCreate,
    RoleCreate,
    RolePermissionResponse,
    RoleResponse,
    UserRoleResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED
)
async def create_role(
    data: RoleCreate,
    payload: TokenPayload = Depends(require_super_user),
    use_case: CreateRoleUseCase = Depends(get_create_role_use_case),
) -> RoleResponse:
    result = await use_case.execute(
        CreateRoleInput(
            name=data.name,
            description=data.description,
            actor_id=UUID(str(payload["sub"])),
        )
    )
    return RoleResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        is_system=result.is_system,
        created_by=result.created_by,
        created_at=result.created_at,  # type: ignore[arg-type]
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    payload: TokenPayload = Depends(require_super_user),
    use_case: DeleteRoleUseCase = Depends(get_delete_role_use_case),
) -> None:
    await use_case.execute(
        DeleteRoleInput(role_id=role_id, actor_id=UUID(str(payload["sub"])))
    )


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RolePermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_permission(
    role_id: UUID,
    data: PermissionCreate,
    payload: TokenPayload = Depends(require_super_user),
    use_case: AssignPermissionUseCase = Depends(get_assign_permission_use_case),
) -> RolePermissionResponse:
    result = await use_case.execute(
        AssignPermissionInput(
            role_id=role_id,
            resource=data.resource,
            action=data.action,
            actor_id=UUID(str(payload["sub"])),
        )
    )
    return RolePermissionResponse(
        role_id=result.role_id, permission_id=result.permission_id
    )


@router.delete(
    "/roles/{role_id}/permissions/{scope}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_permission(
    role_id: UUID,
    scope: str,
    payload: TokenPayload = Depends(require_super_user),
    use_case: RevokePermissionUseCase = Depends(get_revoke_permission_use_case),
) -> None:
    await use_case.execute(
        RevokePermissionInput(
            role_id=role_id,
            scope_key=scope,
            actor_id=UUID(str(payload["sub"])),
        )
    )


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_role_to_user(
    user_id: UUID,
    data: AssignRoleRequest,
    payload: TokenPayload = Depends(require_super_user),
    use_case: AssignRoleToUserUseCase = Depends(get_assign_role_to_user_use_case),
) -> UserRoleResponse:
    result = await use_case.execute(
        AssignRoleToUserInput(
            user_id=user_id,
            role_id=data.role_id,
            actor_id=UUID(str(payload["sub"])),
        )
    )
    return UserRoleResponse(user_id=result.user_id, role_id=result.role_id)


@router.delete(
    "/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_role_from_user(
    user_id: UUID,
    role_id: UUID,
    payload: TokenPayload = Depends(require_super_user),
    use_case: RevokeRoleFromUserUseCase = Depends(
        get_revoke_role_from_user_use_case
    ),
) -> None:
    await use_case.execute(
        RevokeRoleFromUserInput(
            user_id=user_id,
            role_id=role_id,
            actor_id=UUID(str(payload["sub"])),
        )
    )

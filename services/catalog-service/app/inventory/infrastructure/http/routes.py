import uuid

from fastapi import APIRouter, Depends, status

from app.catalog.infrastructure.http.dependencies import require_catalog_write
from app.inventory.application.dto import (
    ReleaseReservationInput,
    ReserveStockInput,
    RestockInput,
)
from app.inventory.application.use_cases.get_inventory import GetInventoryUseCase
from app.inventory.application.use_cases.release_reservation import (
    ReleaseReservationUseCase,
)
from app.inventory.application.use_cases.reserve_stock import ReserveStockUseCase
from app.inventory.application.use_cases.restock import RestockUseCase
from app.inventory.infrastructure.composition import (
    get_get_inventory_use_case,
    get_release_reservation_use_case,
    get_reserve_stock_use_case,
    get_restock_use_case,
)
from app.inventory.infrastructure.http.schemas import (
    InventoryResponse,
    ReleaseRequest,
    ReserveRequest,
    RestockRequest,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/variants/{variant_id}", response_model=InventoryResponse)
async def get_inventory(
    variant_id: uuid.UUID,
    use_case: GetInventoryUseCase = Depends(get_get_inventory_use_case),
) -> InventoryResponse:
    result = await use_case.execute(variant_id)
    return InventoryResponse(**result.__dict__)


@router.post(
    "/variants/{variant_id}/restock",
    response_model=InventoryResponse,
    status_code=status.HTTP_200_OK,
)
async def restock(
    variant_id: uuid.UUID,
    data: RestockRequest,
    payload: dict = Depends(require_catalog_write),
    use_case: RestockUseCase = Depends(get_restock_use_case),
) -> InventoryResponse:
    result = await use_case.execute(
        RestockInput(
            variant_id=variant_id,
            quantity=data.quantity,
            actor_id=uuid.UUID(str(payload["sub"])),
        )
    )
    return InventoryResponse(**result.__dict__)


@router.post("/variants/{variant_id}/reserve", response_model=InventoryResponse)
async def reserve_stock(
    variant_id: uuid.UUID,
    data: ReserveRequest,
    payload: dict = Depends(require_catalog_write),
    use_case: ReserveStockUseCase = Depends(get_reserve_stock_use_case),
) -> InventoryResponse:
    result = await use_case.execute(
        ReserveStockInput(
            variant_id=variant_id,
            quantity=data.quantity,
            actor_id=uuid.UUID(str(payload["sub"])),
        )
    )
    return InventoryResponse(**result.__dict__)


@router.post("/variants/{variant_id}/release", response_model=InventoryResponse)
async def release_reservation(
    variant_id: uuid.UUID,
    data: ReleaseRequest,
    payload: dict = Depends(require_catalog_write),
    use_case: ReleaseReservationUseCase = Depends(get_release_reservation_use_case),
) -> InventoryResponse:
    result = await use_case.execute(
        ReleaseReservationInput(
            variant_id=variant_id,
            quantity=data.quantity,
            actor_id=uuid.UUID(str(payload["sub"])),
        )
    )
    return InventoryResponse(**result.__dict__)

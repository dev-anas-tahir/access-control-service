from app.inventory.application.use_cases.get_inventory import GetInventoryUseCase
from app.inventory.application.use_cases.release_reservation import (
    ReleaseReservationUseCase,
)
from app.inventory.application.use_cases.reserve_stock import ReserveStockUseCase
from app.inventory.application.use_cases.restock import RestockUseCase
from app.inventory.infrastructure.unit_of_work import SqlAlchemyInventoryUnitOfWork
from app.shared.infrastructure.db.session import async_session_factory


def _uow_factory() -> SqlAlchemyInventoryUnitOfWork:
    return SqlAlchemyInventoryUnitOfWork(session_factory=async_session_factory)


def get_get_inventory_use_case() -> GetInventoryUseCase:
    return GetInventoryUseCase(uow_factory=_uow_factory)


def get_restock_use_case() -> RestockUseCase:
    return RestockUseCase(uow_factory=_uow_factory)


def get_reserve_stock_use_case() -> ReserveStockUseCase:
    return ReserveStockUseCase(uow_factory=_uow_factory)


def get_release_reservation_use_case() -> ReleaseReservationUseCase:
    return ReleaseReservationUseCase(uow_factory=_uow_factory)

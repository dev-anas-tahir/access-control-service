import uuid

import pytest

from app.catalog.application.dto import SetProductStatusInput
from app.catalog.application.use_cases.set_product_status import SetProductStatusUseCase
from app.catalog.domain.entities.product import ProductStatus
from app.catalog.domain.events import ProductPublished
from app.catalog.domain.exceptions import ProductNotFoundError
from tests.unit.catalog.fakes import (
    FakeCatalogUnitOfWork,
    FakeProductRepository,
    make_product,
)


@pytest.fixture
def inactive_product():
    return make_product(status=ProductStatus.INACTIVE)


@pytest.fixture
def active_product():
    return make_product(status=ProductStatus.ACTIVE)


async def test_activating_inactive_product_fires_published_event(inactive_product):
    uow = FakeCatalogUnitOfWork(
        products=FakeProductRepository(products=[inactive_product])
    )
    use_case = SetProductStatusUseCase(uow_factory=lambda: uow)

    result = await use_case.execute(
        SetProductStatusInput(
            product_id=inactive_product.id,
            active=True,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.status == ProductStatus.ACTIVE
    assert len(uow.emitted_events) == 1
    assert isinstance(uow.emitted_events[0], ProductPublished)
    assert uow.emitted_events[0].product_id == inactive_product.id


async def test_activating_already_active_product_does_not_fire_event(active_product):
    uow = FakeCatalogUnitOfWork(
        products=FakeProductRepository(products=[active_product])
    )
    use_case = SetProductStatusUseCase(uow_factory=lambda: uow)

    await use_case.execute(
        SetProductStatusInput(
            product_id=active_product.id,
            active=True,
            actor_id=uuid.uuid4(),
        )
    )

    assert uow.emitted_events == []


async def test_deactivating_product_sets_inactive(active_product):
    uow = FakeCatalogUnitOfWork(
        products=FakeProductRepository(products=[active_product])
    )
    use_case = SetProductStatusUseCase(uow_factory=lambda: uow)

    result = await use_case.execute(
        SetProductStatusInput(
            product_id=active_product.id,
            active=False,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.status == ProductStatus.INACTIVE


async def test_raises_when_product_not_found():
    uow = FakeCatalogUnitOfWork()
    use_case = SetProductStatusUseCase(uow_factory=lambda: uow)

    with pytest.raises(ProductNotFoundError):
        await use_case.execute(
            SetProductStatusInput(
                product_id=uuid.uuid4(),
                active=True,
                actor_id=uuid.uuid4(),
            )
        )

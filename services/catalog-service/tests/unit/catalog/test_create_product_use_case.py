import uuid

import pytest

from app.catalog.application.dto import CreateProductInput
from app.catalog.application.use_cases.create_product import CreateProductUseCase
from app.catalog.domain.entities.product import ProductStatus
from app.catalog.domain.exceptions import CategoryNotFoundError
from tests.unit.catalog.fakes import (
    FakeCatalogUnitOfWork,
    FakeCategoryRepository,
    make_category,
)


@pytest.fixture
def category():
    return make_category()


@pytest.fixture
def uow(category):
    return FakeCatalogUnitOfWork(
        categories=FakeCategoryRepository(categories=[category])
    )


async def test_creates_product_as_inactive(uow, category):
    use_case = CreateProductUseCase(uow_factory=lambda: uow)
    result = await use_case.execute(
        CreateProductInput(
            name="Gaming Laptop",
            description="High-end",
            category_id=category.id,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.name == "Gaming Laptop"
    assert result.status == ProductStatus.INACTIVE
    assert result.category_id == category.id
    assert uow.committed


async def test_raises_when_category_not_found():
    uow = FakeCatalogUnitOfWork()
    use_case = CreateProductUseCase(uow_factory=lambda: uow)

    with pytest.raises(CategoryNotFoundError):
        await use_case.execute(
            CreateProductInput(
                name="X",
                description=None,
                category_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
            )
        )

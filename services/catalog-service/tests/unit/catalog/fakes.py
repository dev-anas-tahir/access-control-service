"""In-memory fakes for catalog ports — use in unit tests."""

import uuid
from datetime import datetime, timezone

from app.catalog.domain.entities.category import Category
from app.catalog.domain.entities.product import Product, ProductStatus, ProductVariant
from app.catalog.domain.events import CatalogEvent


def make_category(name: str = "Electronics", slug: str = "electronics") -> Category:
    return Category(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
        parent_id=None,
        created_at=datetime.now(timezone.utc),
    )


def make_product(
    name: str = "Laptop",
    status: ProductStatus = ProductStatus.INACTIVE,
    category_id: uuid.UUID | None = None,
) -> Product:
    return Product(
        id=uuid.uuid4(),
        name=name,
        description=None,
        category_id=category_id or uuid.uuid4(),
        status=status,
        created_by=uuid.uuid4(),
        variants=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_variant(
    product_id: uuid.UUID | None = None,
    sku: str = "SKU-001",
    price: float = 99.99,
) -> ProductVariant:
    return ProductVariant(
        id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        sku=sku,
        price=price,
        attributes={},
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class FakeProductRepository:
    def __init__(
        self,
        products: list[Product] | None = None,
        variants: list[ProductVariant] | None = None,
    ) -> None:
        self._products: dict[uuid.UUID, Product] = {p.id: p for p in (products or [])}
        self._variants: dict[uuid.UUID, ProductVariant] = {
            v.id: v for v in (variants or [])
        }

    async def find_by_id(self, id: uuid.UUID) -> Product | None:
        return self._products.get(id)

    async def list_active(self, limit: int, offset: int) -> list[Product]:
        active = [
            p for p in self._products.values() if p.status == ProductStatus.ACTIVE
        ]
        return active[offset : offset + limit]

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        category_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Product:
        product = Product(
            id=uuid.uuid4(),
            name=name,
            description=description,
            category_id=category_id,
            status=ProductStatus.INACTIVE,
            created_by=created_by,
            variants=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._products[product.id] = product
        return product

    async def save(self, product: Product) -> None:
        self._products[product.id] = product

    async def add_variant(
        self,
        *,
        product_id: uuid.UUID,
        sku: str,
        price: float,
        attributes: dict,
    ) -> ProductVariant:
        variant = make_variant(product_id=product_id, sku=sku, price=price)
        variant.attributes = attributes
        self._variants[variant.id] = variant
        return variant

    async def sku_exists(self, sku: str) -> bool:
        return any(v.sku == sku for v in self._variants.values())

    async def find_variant_by_id(self, variant_id: uuid.UUID) -> ProductVariant | None:
        return self._variants.get(variant_id)

    async def save_variant(self, variant: ProductVariant) -> None:
        self._variants[variant.id] = variant

    async def delete_variant(self, variant_id: uuid.UUID) -> None:
        self._variants.pop(variant_id, None)


class FakeCategoryRepository:
    def __init__(self, categories: list[Category] | None = None) -> None:
        self._by_id: dict[uuid.UUID, Category] = {c.id: c for c in (categories or [])}
        self._by_slug: dict[str, Category] = {c.slug: c for c in (categories or [])}

    async def find_by_id(self, id: uuid.UUID) -> Category | None:
        return self._by_id.get(id)

    async def find_by_slug(self, slug: str) -> Category | None:
        return self._by_slug.get(slug)

    async def list_all(self) -> list[Category]:
        return list(self._by_id.values())

    async def add(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
    ) -> Category:
        cat = Category(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[cat.id] = cat
        self._by_slug[cat.slug] = cat
        return cat


class FakeCatalogUnitOfWork:
    def __init__(
        self,
        products: FakeProductRepository | None = None,
        categories: FakeCategoryRepository | None = None,
    ) -> None:
        self.products = products or FakeProductRepository()
        self.categories = categories or FakeCategoryRepository()
        self.committed = False
        self._events: list[CatalogEvent] = []
        self.emitted_events: list[CatalogEvent] = []

    async def __aenter__(self) -> "FakeCatalogUnitOfWork":
        self._events = []
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            self._events.clear()

    async def commit(self) -> None:
        self.committed = True
        self.emitted_events.extend(self._events)
        self._events.clear()

    async def rollback(self) -> None:
        self._events.clear()

    def add_event(self, event: CatalogEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[CatalogEvent]:
        events = self._events[:]
        self._events.clear()
        return events

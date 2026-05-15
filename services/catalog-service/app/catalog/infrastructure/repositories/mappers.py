from app.catalog.domain.entities.category import Category
from app.catalog.domain.entities.product import Product, ProductVariant
from app.catalog.infrastructure.orm.category import Category as CategoryORM
from app.catalog.infrastructure.orm.product import Product as ProductORM
from app.catalog.infrastructure.orm.product import ProductVariant as VariantORM


def _variant_orm_to_domain(orm: VariantORM) -> ProductVariant:
    return ProductVariant(
        id=orm.id,
        product_id=orm.product_id,
        sku=orm.sku,
        price=float(orm.price),
        attributes=orm.attributes or {},
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _product_orm_to_domain(orm: ProductORM) -> Product:
    return Product(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        category_id=orm.category_id,
        status=orm.status,
        created_by=orm.created_by,
        variants=[_variant_orm_to_domain(v) for v in orm.variants],
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _category_orm_to_domain(orm: CategoryORM) -> Category:
    return Category(
        id=orm.id,
        name=orm.name,
        slug=orm.slug,
        parent_id=orm.parent_id,
        created_at=orm.created_at,
    )

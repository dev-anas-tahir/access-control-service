import uuid

from fastapi import APIRouter, Depends, status

from app.catalog.application.dto import (
    CreateCategoryInput,
    CreateProductInput,
    CreateVariantInput,
    SetProductStatusInput,
    UpdateProductInput,
    UpdateVariantInput,
)
from app.catalog.application.use_cases.create_category import CreateCategoryUseCase
from app.catalog.application.use_cases.create_product import CreateProductUseCase
from app.catalog.application.use_cases.create_variant import CreateVariantUseCase
from app.catalog.application.use_cases.delete_variant import DeleteVariantUseCase
from app.catalog.application.use_cases.get_product import GetProductUseCase
from app.catalog.application.use_cases.list_categories import ListCategoriesUseCase
from app.catalog.application.use_cases.list_products import ListProductsUseCase
from app.catalog.application.use_cases.set_product_status import SetProductStatusUseCase
from app.catalog.application.use_cases.update_product import UpdateProductUseCase
from app.catalog.application.use_cases.update_variant import UpdateVariantUseCase
from app.catalog.infrastructure.composition import (
    get_create_category_use_case,
    get_create_product_use_case,
    get_create_variant_use_case,
    get_delete_variant_use_case,
    get_get_product_use_case,
    get_list_categories_use_case,
    get_list_products_use_case,
    get_set_product_status_use_case,
    get_update_product_use_case,
    get_update_variant_use_case,
)
from app.catalog.infrastructure.http.dependencies import require_catalog_write
from app.catalog.infrastructure.http.schemas import (
    CategoryCreate,
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
    ProductVariantResponse,
    VariantCreate,
    VariantUpdate,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _actor_id(payload: dict) -> uuid.UUID:
    return uuid.UUID(str(payload["sub"]))


# ── Products (public reads) ─────────────────────────────────────────────────


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    limit: int = 20,
    offset: int = 0,
    use_case: ListProductsUseCase = Depends(get_list_products_use_case),
) -> list[ProductResponse]:
    results = await use_case.execute(limit=limit, offset=offset)
    return [ProductResponse(**r.__dict__) for r in results]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    use_case: GetProductUseCase = Depends(get_get_product_use_case),
) -> ProductResponse:
    result = await use_case.execute(product_id)
    return ProductResponse(**result.__dict__)


# ── Products (writes require catalog:write) ─────────────────────────────────


@router.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
async def create_product(
    data: ProductCreate,
    payload: dict = Depends(require_catalog_write),
    use_case: CreateProductUseCase = Depends(get_create_product_use_case),
) -> ProductResponse:
    result = await use_case.execute(
        CreateProductInput(
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            actor_id=_actor_id(payload),
        )
    )
    return ProductResponse(**result.__dict__)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    payload: dict = Depends(require_catalog_write),
    use_case: UpdateProductUseCase = Depends(get_update_product_use_case),
) -> ProductResponse:
    result = await use_case.execute(
        UpdateProductInput(
            product_id=product_id,
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            actor_id=_actor_id(payload),
        )
    )
    return ProductResponse(**result.__dict__)


@router.patch("/products/{product_id}/status", response_model=ProductResponse)
async def set_product_status(
    product_id: uuid.UUID,
    data: ProductStatusUpdate,
    payload: dict = Depends(require_catalog_write),
    use_case: SetProductStatusUseCase = Depends(get_set_product_status_use_case),
) -> ProductResponse:
    result = await use_case.execute(
        SetProductStatusInput(
            product_id=product_id,
            active=data.active,
            actor_id=_actor_id(payload),
        )
    )
    return ProductResponse(**result.__dict__)


# ── Variants ─────────────────────────────────────────────────────────────────


@router.post(
    "/products/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variant(
    product_id: uuid.UUID,
    data: VariantCreate,
    payload: dict = Depends(require_catalog_write),
    use_case: CreateVariantUseCase = Depends(get_create_variant_use_case),
) -> ProductVariantResponse:
    result = await use_case.execute(
        CreateVariantInput(
            product_id=product_id,
            sku=data.sku,
            price=data.price,
            attributes=data.attributes,
            actor_id=_actor_id(payload),
        )
    )
    return ProductVariantResponse(**result.__dict__)


@router.patch("/variants/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    variant_id: uuid.UUID,
    data: VariantUpdate,
    payload: dict = Depends(require_catalog_write),
    use_case: UpdateVariantUseCase = Depends(get_update_variant_use_case),
) -> ProductVariantResponse:
    result = await use_case.execute(
        UpdateVariantInput(
            variant_id=variant_id,
            price=data.price,
            attributes=data.attributes,
            is_active=data.is_active,
            actor_id=_actor_id(payload),
        )
    )
    return ProductVariantResponse(**result.__dict__)


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    variant_id: uuid.UUID,
    payload: dict = Depends(require_catalog_write),
    use_case: DeleteVariantUseCase = Depends(get_delete_variant_use_case),
) -> None:
    await use_case.execute(variant_id)


# ── Categories ────────────────────────────────────────────────────────────────


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    use_case: ListCategoriesUseCase = Depends(get_list_categories_use_case),
) -> list[CategoryResponse]:
    results = await use_case.execute()
    return [CategoryResponse(**r.__dict__) for r in results]


@router.post(
    "/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    data: CategoryCreate,
    payload: dict = Depends(require_catalog_write),
    use_case: CreateCategoryUseCase = Depends(get_create_category_use_case),
) -> CategoryResponse:
    result = await use_case.execute(
        CreateCategoryInput(
            name=data.name,
            slug=data.slug,
            parent_id=data.parent_id,
            actor_id=_actor_id(payload),
        )
    )
    return CategoryResponse(**result.__dict__)

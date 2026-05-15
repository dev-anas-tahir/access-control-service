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
from app.catalog.infrastructure.unit_of_work import SqlAlchemyCatalogUnitOfWork
from app.shared.infrastructure.db.session import async_session_factory


def _uow_factory() -> SqlAlchemyCatalogUnitOfWork:
    return SqlAlchemyCatalogUnitOfWork(session_factory=async_session_factory)


def get_create_product_use_case() -> CreateProductUseCase:
    return CreateProductUseCase(uow_factory=_uow_factory)


def get_update_product_use_case() -> UpdateProductUseCase:
    return UpdateProductUseCase(uow_factory=_uow_factory)


def get_set_product_status_use_case() -> SetProductStatusUseCase:
    return SetProductStatusUseCase(uow_factory=_uow_factory)


def get_get_product_use_case() -> GetProductUseCase:
    return GetProductUseCase(uow_factory=_uow_factory)


def get_list_products_use_case() -> ListProductsUseCase:
    return ListProductsUseCase(uow_factory=_uow_factory)


def get_create_category_use_case() -> CreateCategoryUseCase:
    return CreateCategoryUseCase(uow_factory=_uow_factory)


def get_list_categories_use_case() -> ListCategoriesUseCase:
    return ListCategoriesUseCase(uow_factory=_uow_factory)


def get_create_variant_use_case() -> CreateVariantUseCase:
    return CreateVariantUseCase(uow_factory=_uow_factory)


def get_update_variant_use_case() -> UpdateVariantUseCase:
    return UpdateVariantUseCase(uow_factory=_uow_factory)


def get_delete_variant_use_case() -> DeleteVariantUseCase:
    return DeleteVariantUseCase(uow_factory=_uow_factory)

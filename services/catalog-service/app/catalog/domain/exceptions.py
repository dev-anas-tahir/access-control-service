class ProductNotFoundError(Exception):
    def __str__(self) -> str:
        return "Product not found"


class ProductVariantNotFoundError(Exception):
    def __str__(self) -> str:
        return "Product variant not found"


class SkuAlreadyExistsError(Exception):
    def __init__(self, sku: str) -> None:
        self.sku = sku

    def __str__(self) -> str:
        return f"SKU '{self.sku}' already exists"


class CategoryNotFoundError(Exception):
    def __str__(self) -> str:
        return "Category not found"


class CategorySlugAlreadyExistsError(Exception):
    def __str__(self) -> str:
        return "Category slug already exists"

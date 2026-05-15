class InventoryNotFoundError(Exception):
    def __str__(self) -> str:
        return "Inventory record not found for variant"


class InsufficientStockError(Exception):
    def __init__(self, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested

    def __str__(self) -> str:
        return f"Insufficient stock: {self.available} available, {self.requested} requested"

"""Compound ID utilities for Rappi cart operations."""


def make_compound_id(store_id: int, product_id: int) -> str:
    """Build the cart compound ID: 'storeId_productId'."""
    return f"{store_id}_{product_id}"


def parse_compound_id(compound_id: str) -> tuple[int, int]:
    """Parse a compound ID back into (store_id, product_id)."""
    store_id, product_id = compound_id.split("_", 1)
    return int(store_id), int(product_id)

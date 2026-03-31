"""Session state for the interactive ordering flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from rappi.models.address import Address
from rappi.models.cart import Cart
from rappi.models.store import CatalogStore, Corridor, Product, SearchStore, StoreDetail


@dataclass
class SessionState:
    """Mutable state carried across all interactive steps."""

    # Address
    active_address: Address | None = None

    # Current store context
    current_store: StoreDetail | None = None

    # Cart snapshot (refreshed after mutations)
    carts: list[Cart] = field(default_factory=list)

    # Search/browse results cache (for numbered selection)
    last_search_stores: list[SearchStore] = field(default_factory=list)
    last_catalog_stores: list[CatalogStore] = field(default_factory=list)

    @property
    def cart_item_count(self) -> int:
        return sum(p.units for c in self.carts for s in c.stores for p in s.products)

    @property
    def cart_total(self) -> float:
        return sum(c.sub_total for c in self.carts)

    @property
    def store_name(self) -> str:
        if self.current_store and self.current_store.name:
            return self.current_store.name
        return "Restaurant"

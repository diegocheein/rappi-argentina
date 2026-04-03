"""Models for account features — favorites, credits."""

from pydantic import BaseModel


class FavoriteStoreInfo(BaseModel):
    """A favorite store from Rappi's API."""
    store_id: int | None = None
    name: str | None = None
    logo: str | None = None
    store_type: str | None = None


class RappiCredits(BaseModel):
    """Rappi credits/wallet balance."""
    balance: float = 0
    currency: str = "COP"

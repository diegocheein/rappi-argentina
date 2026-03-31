"""User profile and Prime status models."""

from pydantic import BaseModel


class LoyaltyInfo(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None


class UserProfile(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    country_code: str | None = None
    country_code_name: str | None = None
    vip: bool = False
    loyalty: LoyaltyInfo | None = None


class PrimeStatus(BaseModel):
    is_prime: bool = False

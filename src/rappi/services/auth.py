"""Authentication and user profile services."""

from rappi.client import RappiClient
from rappi.config import ConfigManager
from rappi.constants import Endpoints
from rappi.models.user import PrimeStatus, UserProfile


async def get_profile(client: RappiClient) -> UserProfile:
    """Fetch the authenticated user's profile."""
    data = await client.get(Endpoints.USER_PROFILE)
    return UserProfile(**data)


async def is_prime(client: RappiClient) -> PrimeStatus:
    """Check if the user has Rappi Prime."""
    data = await client.get(Endpoints.IS_PRIME)
    return PrimeStatus(**data)


def set_token(config_manager: ConfigManager, token: str, device_id: str | None = None) -> None:
    """Save a Bearer token (and optionally deviceId) to the config."""
    updates: dict = {"token": token}
    if device_id:
        updates["device_id"] = device_id
    config_manager.update(**updates)

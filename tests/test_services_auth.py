"""Tests for rappi.services.auth — profile, prime status, and token management."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.auth import get_profile, is_prime, set_token
from rappi.models.user import UserProfile, PrimeStatus


class TestGetProfile:
    async def test_returns_user_profile(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": 42}'
        mock_response.json.return_value = {
            "id": 42,
            "first_name": "Gabriel",
            "last_name": "Garavit",
            "email": "g@test.com",
            "vip": False,
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        profile = await get_profile(mock_client)
        assert isinstance(profile, UserProfile)
        assert profile.id == 42
        assert profile.first_name == "Gabriel"
        assert profile.email == "g@test.com"


class TestIsPrime:
    async def test_returns_prime_status(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"is_prime": true}'
        mock_response.json.return_value = {"is_prime": True}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        status = await is_prime(mock_client)
        assert isinstance(status, PrimeStatus)
        assert status.is_prime is True

    async def test_not_prime(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"is_prime": false}'
        mock_response.json.return_value = {"is_prime": False}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        status = await is_prime(mock_client)
        assert status.is_prime is False


class TestSetToken:
    def test_saves_token(self, tmp_config):
        cm, config_file = tmp_config
        set_token(cm, "new-token")
        loaded = cm.load()
        assert loaded.token == "new-token"

    def test_saves_token_and_device_id(self, tmp_config):
        cm, _ = tmp_config
        set_token(cm, "tok-123", device_id="dev-456")
        loaded = cm.load()
        assert loaded.token == "tok-123"
        assert loaded.device_id == "dev-456"

    def test_token_only_preserves_device_id(self, tmp_config):
        from rappi.config import RappiConfig
        cm, _ = tmp_config
        cm.save(RappiConfig(device_id="original-device"))
        set_token(cm, "new-tok")
        loaded = cm.load()
        assert loaded.token == "new-tok"
        assert loaded.device_id == "original-device"

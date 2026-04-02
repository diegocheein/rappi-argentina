"""Tests for rappi.services.address — list addresses, set active, reverse geocode."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.address import list_addresses, set_active_address
from rappi.models.address import Address


class TestListAddresses:
    async def test_returns_addresses(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"addresses": []}'
        mock_response.json.return_value = {
            "addresses": [
                {"id": 1, "address": "Calle 100", "active": True, "lat": 4.6, "lng": -74.0},
                {"id": 2, "address": "Carrera 15", "active": False, "lat": 4.7, "lng": -74.1},
            ]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        addresses = await list_addresses(mock_client)
        assert len(addresses) == 2
        assert addresses[0].active is True
        assert addresses[1].address == "Carrera 15"

    async def test_empty_addresses(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"addresses": []}'
        mock_response.json.return_value = {"addresses": []}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        addresses = await list_addresses(mock_client)
        assert addresses == []


class TestSetActiveAddress:
    async def test_updates_config_coordinates(self, mock_client):
        # First call: PUT to set active, second call: GET to list addresses
        responses = []

        # Response for PUT (set active address)
        put_response = MagicMock()
        put_response.status_code = 200
        put_response.content = b'{}'
        put_response.json.return_value = {}
        responses.append(put_response)

        # Response for GET (list addresses)
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.content = b'{"addresses": []}'
        get_response.json.return_value = {
            "addresses": [
                {"id": 5, "address": "New Place", "active": True, "lat": 10.0, "lng": -75.0},
            ]
        }
        responses.append(get_response)

        mock_client._http.request = AsyncMock(side_effect=responses)

        await set_active_address(mock_client, 5)

        # Verify config was updated
        loaded = mock_client.config_manager.load()
        assert loaded.lat == pytest.approx(10.0)
        assert loaded.lng == pytest.approx(-75.0)
        assert loaded.active_address_id == 5

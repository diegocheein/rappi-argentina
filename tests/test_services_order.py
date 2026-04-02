"""Tests for rappi.services.order — order listing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.order import get_orders
from rappi.models.order import OrdersResponse


class TestGetOrders:
    async def test_returns_active_and_cancelled(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "active_orders": [
                {
                    "id": 1001,
                    "total": 45000,
                    "state": "in_store",
                    "store": {"id": 100, "name": "Burger Place"},
                    "tip": 3000,
                },
            ],
            "cancel_orders": [
                {
                    "id": 1002,
                    "total": 30000,
                    "state": "cancelled",
                    "store": {"id": 200, "name": "Pizza Place"},
                },
            ],
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await get_orders(mock_client)
        assert isinstance(result, OrdersResponse)
        assert len(result.active_orders) == 1
        assert result.active_orders[0].total == 45000
        assert result.active_orders[0].store.name == "Burger Place"
        assert len(result.cancel_orders) == 1
        assert result.cancel_orders[0].state == "cancelled"

    async def test_empty_orders(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "active_orders": [],
            "cancel_orders": [],
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await get_orders(mock_client)
        assert result.active_orders == []
        assert result.cancel_orders == []

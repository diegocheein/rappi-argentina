"""Tests for rappi.services.search — unified search with memory recording."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.search import search
from rappi.models.store import SearchStore


class TestSearch:
    async def test_returns_stores(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "stores": [
                {
                    "store_id": 100,
                    "store_name": "Burger Joint",
                    "store_type": "restaurant",
                    "products": [
                        {"name": "Burger", "price": 15000, "product_id": 1, "in_stock": True},
                        {"name": "Fries", "price": 8000, "product_id": 2, "in_stock": True},
                    ],
                },
                {
                    "store_id": 200,
                    "store_name": "Pizza Place",
                    "products": [
                        {"name": "Margherita", "price": 25000, "product_id": 10},
                    ],
                },
            ]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        stores = await search(mock_client, "hamburguesa")
        assert len(stores) == 2
        assert stores[0].store_name == "Burger Joint"
        assert len(stores[0].products) == 2
        assert stores[0].products[0].price == 15000

    async def test_filter_by_store_id(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "stores": [
                {"store_id": 100, "store_name": "A", "products": []},
                {"store_id": 200, "store_name": "B", "products": []},
            ]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        stores = await search(mock_client, "test", store_id=200)
        assert len(stores) == 1
        assert stores[0].store_id == 200

    async def test_empty_results(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {"stores": []}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        stores = await search(mock_client, "nonexistent")
        assert stores == []

    async def test_records_to_memory(self, mock_client):
        """When memory is attached, search results are recorded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "stores": [{"store_id": 1, "store_name": "Test", "products": []}]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        mock_memory = AsyncMock()
        mock_client._memory = mock_memory

        await search(mock_client, "pizza")
        mock_memory.record_search_results.assert_called_once()

    async def test_memory_error_is_swallowed(self, mock_client):
        """Memory recording failures should not break search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "stores": [{"store_id": 1, "store_name": "Test", "products": []}]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        mock_memory = AsyncMock()
        mock_memory.record_search_results.side_effect = Exception("DB error")
        mock_client._memory = mock_memory

        # Should not raise
        stores = await search(mock_client, "test")
        assert len(stores) == 1

"""Tests for rappi.services.store — detail, menu, toppings, catalog."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.store import (
    get_store_detail,
    get_product_toppings,
    get_restaurant_catalog,
    _search_results_to_corridors,
)
from rappi.models.store import SearchProduct, SearchStore, StoreDetail


class TestGetStoreDetail:
    async def test_restaurant_with_menu(self, mock_client):
        """Restaurant stores should have menu corridors populated."""
        responses = []

        # Response for store detail
        detail_resp = MagicMock()
        detail_resp.status_code = 200
        detail_resp.content = b'{}'
        detail_resp.json.return_value = {
            "store_id": 100,
            "name": "Burger Place",
            "store_type_id": "restaurant",
            "status": {"status": "open"},
        }
        responses.append(detail_resp)

        # Response for menu
        menu_resp = MagicMock()
        menu_resp.status_code = 200
        menu_resp.content = b'{}'
        menu_resp.json.return_value = {
            "corridors": [
                {
                    "id": 1,
                    "name": "Burgers",
                    "products": [
                        {"id": 10, "name": "Classic Burger", "price": 18000, "real_price": 18000},
                    ],
                },
            ]
        }
        responses.append(menu_resp)

        mock_client._http.request = AsyncMock(side_effect=responses)

        store = await get_store_detail(mock_client, 100)
        assert isinstance(store, StoreDetail)
        assert store.name == "Burger Place"
        assert store.is_restaurant is True
        assert len(store.corridors) == 1
        assert store.corridors[0].name == "Burgers"

    async def test_turbo_store_empty_menu(self, mock_client):
        """Non-restaurant stores return empty corridors from menu endpoint."""
        responses = []

        detail_resp = MagicMock()
        detail_resp.status_code = 200
        detail_resp.content = b'{}'
        detail_resp.json.return_value = {
            "store_id": 200,
            "name": "Turbo Store",
            "store_type_id": "turbo",
        }
        responses.append(detail_resp)

        menu_resp = MagicMock()
        menu_resp.status_code = 200
        menu_resp.content = b'{}'
        menu_resp.json.return_value = {"corridors": []}
        responses.append(menu_resp)

        mock_client._http.request = AsyncMock(side_effect=responses)

        store = await get_store_detail(mock_client, 200)
        assert store.is_restaurant is False
        assert store.effective_store_type == "turbo"
        assert len(store.corridors) == 0


class TestSearchResultsToCorridors:
    def test_groups_by_category(self):
        store = SearchStore(
            store_id=1,
            store_name="Test",
            products=[
                SearchProduct(name="Coca Cola", price=3000, product_id=1, category_name="Drinks"),
                SearchProduct(name="Water", price=2000, product_id=2, category_name="Drinks"),
                SearchProduct(name="Chips", price=5000, product_id=3, category_name="Snacks"),
            ],
        )
        corridors = _search_results_to_corridors(store)
        assert len(corridors) == 2

        drinks = next(c for c in corridors if c.name == "Drinks")
        assert len(drinks.products) == 2

        snacks = next(c for c in corridors if c.name == "Snacks")
        assert len(snacks.products) == 1

    def test_default_category(self):
        store = SearchStore(
            store_id=1,
            store_name="Test",
            products=[
                SearchProduct(name="Item", price=1000, product_id=1, category_name=None),
            ],
        )
        corridors = _search_results_to_corridors(store)
        assert corridors[0].name == "Products"

    def test_empty_products(self):
        store = SearchStore(store_id=1, store_name="Test", products=[])
        corridors = _search_results_to_corridors(store)
        assert corridors == []


class TestGetProductToppings:
    async def test_returns_toppings(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "categories": [
                {
                    "id": 1,
                    "description": "Sauces",
                    "min_toppings_for_categories": 1,
                    "max_toppings_for_categories": 3,
                    "toppings": [
                        {"id": 10, "description": "Ketchup", "price": 0},
                        {"id": 11, "description": "Mayo", "price": 500},
                    ],
                },
            ]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await get_product_toppings(mock_client, 100, 10)
        assert len(result.categories) == 1
        assert result.categories[0].min_toppings_for_categories == 1
        assert len(result.categories[0].toppings) == 2

    async def test_empty_toppings(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {"categories": []}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await get_product_toppings(mock_client, 100, 10)
        assert result.categories == []


class TestGetRestaurantCatalog:
    async def test_returns_catalog(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "stores": [
                {"store_id": 1, "name": "Restaurant A", "score": 4.5, "is_available": True},
                {"store_id": 2, "name": "Restaurant B", "score": 3.8, "is_available": False},
            ]
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        catalog = await get_restaurant_catalog(mock_client)
        assert len(catalog) == 2
        assert catalog[0].name == "Restaurant A"
        assert catalog[1].is_available is False

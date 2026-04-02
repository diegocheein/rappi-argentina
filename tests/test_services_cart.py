"""Tests for rappi.services.cart — add, remove, get, recalculate, and payload building."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.cart import (
    _build_topping_payload,
    _build_add_payload,
    add_to_cart,
    get_carts,
    remove_from_cart,
    recalculate_cart,
)
from rappi.models.store import Product, Topping
from rappi.models.cart import Cart


# ---------------------------------------------------------------------------
# Payload building (§7 — compound IDs, three price fields, topping format)
# ---------------------------------------------------------------------------

class TestBuildToppingPayload:
    def test_format(self):
        toppings = [
            Topping(id=10, description="Ketchup", price=0),
            Topping(id=11, description="Extra Cheese", price=3000),
        ]
        payload = _build_topping_payload(toppings)
        assert len(payload) == 2
        assert payload[0] == {"id": 10, "description": "Ketchup", "units": 1, "price": 0}
        assert payload[1]["price"] == 3000

    def test_empty_description(self):
        toppings = [Topping(id=1, description=None, price=0)]
        payload = _build_topping_payload(toppings)
        assert payload[0]["description"] == ""


class TestBuildAddPayload:
    def test_compound_id(self):
        product = Product(id=456, name="Burger", price=15000, real_price=15000)
        payload = _build_add_payload(store_id=100, product=product)
        assert payload[0]["products"][0]["id"] == "100_456"

    def test_three_price_fields(self):
        """API requires price, real_price, and markup_price."""
        product = Product(id=1, name="Test", price=10000, real_price=12000)
        payload = _build_add_payload(store_id=1, product=product)
        p = payload[0]["products"][0]
        assert p["price"] == 10000
        assert p["real_price"] == 12000
        assert p["markup_price"] == 10000

    def test_quantity(self):
        product = Product(id=1, name="Test", price=5000)
        payload = _build_add_payload(store_id=1, product=product, quantity=3)
        assert payload[0]["products"][0]["units"] == 3

    def test_with_toppings(self):
        product = Product(id=1, name="Test", price=5000)
        toppings = [Topping(id=10, description="Extra", price=1000)]
        payload = _build_add_payload(store_id=1, product=product, toppings=toppings)
        assert len(payload[0]["products"][0]["toppings"]) == 1
        assert payload[0]["products"][0]["toppings"][0]["id"] == 10

    def test_no_toppings(self):
        product = Product(id=1, name="Test", price=5000)
        payload = _build_add_payload(store_id=1, product=product)
        assert payload[0]["products"][0]["toppings"] == []

    def test_real_price_fallback(self):
        """If real_price is 0, should fall back to price."""
        product = Product(id=1, name="Test", price=8000, real_price=0)
        payload = _build_add_payload(store_id=1, product=product)
        p = payload[0]["products"][0]
        assert p["real_price"] == 8000  # falls back to price


# ---------------------------------------------------------------------------
# Cart operations (§7, §8, §9)
# ---------------------------------------------------------------------------

class TestAddToCart:
    async def test_returns_carts(self, mock_client):
        product = Product(id=1, name="Burger", price=15000, real_price=15000)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'[{}]'
        mock_response.json.return_value = [
            {"id": "cart-1", "store_type": "restaurant", "stores": [], "product_total": 15000}
        ]
        mock_client._http.request = AsyncMock(return_value=mock_response)

        carts = await add_to_cart(mock_client, 100, product)
        assert len(carts) == 1
        assert isinstance(carts[0], Cart)

    async def test_single_dict_response(self, mock_client):
        """API sometimes returns a single dict instead of a list."""
        product = Product(id=1, name="Test", price=5000)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "id": "cart-1", "store_type": "restaurant", "stores": []
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        carts = await add_to_cart(mock_client, 1, product)
        assert len(carts) == 1


class TestGetCarts:
    async def test_returns_carts(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'[{}]'
        mock_response.json.return_value = [
            {
                "id": "c1", "store_type": "restaurant",
                "stores": [
                    {"id": 100, "name": "Test", "products": [{"id": "100_1", "name": "Burger", "price": 15000}]}
                ],
            }
        ]
        mock_client._http.request = AsyncMock(return_value=mock_response)

        carts = await get_carts(mock_client)
        assert len(carts) == 1
        assert len(carts[0].stores) == 1

    async def test_empty_response(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        carts = await get_carts(mock_client)
        assert carts == []


class TestRemoveFromCart:
    async def test_calls_delete(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await remove_from_cart(mock_client, "100_200", store_type="restaurant")
        mock_client._http.request.assert_called_once()
        call_args = mock_client._http.request.call_args
        assert call_args[0][0] == "DELETE"
        assert "100_200" in call_args[0][1]


class TestRecalculateCart:
    async def test_returns_cart(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "id": "c1", "store_type": "restaurant", "stores": [],
            "product_total": 30000, "sub_total": 35000,
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        cart = await recalculate_cart(mock_client)
        assert isinstance(cart, Cart)
        assert cart.product_total == 30000

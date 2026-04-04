"""Tests for rappi.services.cart — add, remove, get, recalculate, and payload building."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.cart import (
    _build_topping_payload,
    _new_product_payload,
    _cart_product_to_payload,
    add_to_cart,
    get_carts,
    remove_from_cart,
    recalculate_cart,
)
from rappi.models.store import Product, Topping
from rappi.models.cart import Cart, CartProduct, CartTopping


# ---------------------------------------------------------------------------
# Payload building (§7 — compound IDs, topping format)
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


class TestNewProductPayload:
    def test_compound_id(self):
        product = Product(id=456, name="Burger", price=15000, real_price=15000)
        payload = _new_product_payload(store_id=100, product=product)
        assert payload["id"] == "100_456"

    def test_quantity(self):
        product = Product(id=1, name="Test", price=5000)
        payload = _new_product_payload(store_id=1, product=product, quantity=3)
        assert payload["units"] == 3

    def test_with_toppings(self):
        product = Product(id=1, name="Test", price=5000)
        toppings = [Topping(id=10, description="Extra", price=1000)]
        payload = _new_product_payload(store_id=1, product=product, toppings=toppings)
        assert len(payload["toppings"]) == 1
        assert payload["toppings"][0]["id"] == 10

    def test_no_toppings(self):
        product = Product(id=1, name="Test", price=5000)
        payload = _new_product_payload(store_id=1, product=product)
        assert payload["toppings"] == []

    def test_sale_type(self):
        product = Product(id=1, name="Test", price=5000)
        payload = _new_product_payload(store_id=1, product=product)
        assert payload["sale_type"] == "U"


class TestCartProductToPayload:
    def test_round_trip(self):
        cp = CartProduct(id="100_1", name="Burger", units=2, price=15000, toppings=[
            CartTopping(id=10, description="Cheese", units=1, price=2000),
        ])
        payload = _cart_product_to_payload(cp)
        assert payload["id"] == "100_1"
        assert payload["units"] == 2
        assert len(payload["toppings"]) == 1
        assert payload["toppings"][0]["id"] == 10


# ---------------------------------------------------------------------------
# Cart operations — add uses GET+merge+PUT, remove uses PUT with remaining
# ---------------------------------------------------------------------------

class TestAddToCart:
    async def test_returns_carts(self, mock_client):
        product = Product(id=1, name="Burger", price=15000, real_price=15000)

        # Mock get_carts (POST to CART_GET_ALL) → empty cart
        # Mock add (PUT to CART_ADD) → cart with product
        call_count = 0
        async def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            if "get" in url:
                # get_carts returns empty
                resp.content = b'[]'
                resp.json.return_value = []
            else:
                # PUT returns cart with item
                resp.content = b'[{}]'
                resp.json.return_value = [
                    {"id": "cart-1", "store_type": "restaurant", "stores": [], "product_total": 15000}
                ]
            return resp

        mock_client._http.request = mock_request
        carts = await add_to_cart(mock_client, 100, product)
        assert len(carts) == 1
        assert isinstance(carts[0], Cart)


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
    async def test_uses_put_with_remaining(self, mock_client):
        """Remove uses PUT with all products minus the removed one (not DELETE)."""
        call_count = 0
        put_payload = None
        async def mock_request(method, url, **kwargs):
            nonlocal call_count, put_payload
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            if "get" in url:
                # Existing cart has 2 items
                resp.content = b'[{}]'
                resp.json.return_value = [
                    {
                        "id": "c1", "store_type": "restaurant",
                        "stores": [{
                            "id": 100, "products": [
                                {"id": "100_1", "name": "Burger", "units": 1, "price": 15000},
                                {"id": "100_2", "name": "Fries", "units": 1, "price": 5000},
                            ]
                        }],
                    }
                ]
            else:
                # PUT returns updated cart
                if kwargs.get("json"):
                    put_payload = kwargs["json"]
                resp.content = b'[{}]'
                resp.json.return_value = [
                    {"id": "c1", "store_type": "restaurant", "stores": [{"id": 100, "products": [{"id": "100_2", "name": "Fries", "units": 1}]}]}
                ]
            return resp

        mock_client._http.request = mock_request
        carts = await remove_from_cart(mock_client, 100, "100_1", store_type="restaurant")

        # Should have sent PUT with only the Fries remaining
        assert put_payload is not None
        assert len(put_payload[0]["products"]) == 1
        assert put_payload[0]["products"][0]["id"] == "100_2"


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

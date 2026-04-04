"""Tests for rappi.services.checkout — detail, tip, payment method."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rappi.services.checkout import get_checkout_detail, set_tip
from rappi.models.order import CheckoutDetail


class TestGetCheckoutDetail:
    async def test_returns_checkout_detail(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "return_key": "<b>key123</b>",
            "summary": [
                {
                    "header": {"title": "Order Summary"},
                    "details": [
                        {"type": "text", "key": "Subtotal", "value": "$15.000"},
                        {"type": "text", "key": "Delivery", "value": "$3.500"},
                        {"type": "text", "key": "Total", "value": "$18.500"},
                    ],
                }
            ],
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        detail = await get_checkout_detail(mock_client)
        assert isinstance(detail, CheckoutDetail)
        # HTML should be stripped from return_key
        assert detail.return_key == "key123"
        assert "<b>" not in (detail.return_key or "")
        assert len(detail.summary) == 1
        assert len(detail.summary[0].details) == 3

    async def test_no_html_tags_in_summary_values(self, mock_client):
        """Verify that return_key with nested tags is cleaned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {
            "return_key": '<font color="red">abc</font>',
            "summary": [],
        }
        mock_client._http.request = AsyncMock(return_value=mock_response)

        detail = await get_checkout_detail(mock_client)
        assert detail.return_key == "abc"

    async def test_none_return_key(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {"summary": []}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        detail = await get_checkout_detail(mock_client)
        assert detail.return_key is None


class TestSetTip:
    async def test_calls_put_then_recalculate(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await set_tip(mock_client, 5000)
        # set_tip now makes 2 calls: PUT tip + POST recalculate
        assert mock_client._http.request.call_count == 2
        first_call = mock_client._http.request.call_args_list[0]
        assert first_call[0][0] == "PUT"
        assert first_call[1]["json"] == {"tip": 5000}
        second_call = mock_client._http.request.call_args_list[1]
        assert second_call[0][0] == "POST"
        assert "recalculate" in second_call[0][1]

    async def test_zero_tip(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await set_tip(mock_client, 0)
        first_call = mock_client._http.request.call_args_list[0]
        assert first_call[1]["json"] == {"tip": 0}

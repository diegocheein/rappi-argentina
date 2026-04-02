"""Tests for rappi.client — RappiClient context manager, error handling, and HTTP delegation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from rappi.client import RappiClient, RappiAPIError, TokenExpiredError
from rappi.config import ConfigManager, RappiConfig


class TestTokenExpiredError:
    def test_message(self):
        err = TokenExpiredError("Token expired")
        assert "Token expired" in str(err)


class TestRappiAPIError:
    def test_status_and_detail(self):
        err = RappiAPIError(404, "Not found")
        assert err.status_code == 404
        assert err.detail == "Not found"
        assert "404" in str(err)


class TestRappiClientInit:
    def test_default_config_manager(self):
        client = RappiClient()
        assert client.config_manager is not None

    def test_custom_config(self, sample_config, tmp_config):
        cm, _ = tmp_config
        client = RappiClient(config=sample_config, config_manager=cm)
        assert client.config.token == "test-token-abc123"

    def test_memory_property(self):
        client = RappiClient(memory=MagicMock())
        assert client.memory is not None


class TestRappiClientContextManager:
    async def test_raises_without_token(self, tmp_config):
        cm, _ = tmp_config
        cfg = RappiConfig(token=None)
        cm.save(cfg)
        client = RappiClient(config=cfg, config_manager=cm)
        with pytest.raises(TokenExpiredError, match="No token"):
            async with client:
                pass

    async def test_creates_http_client_with_token(self, tmp_config):
        cm, _ = tmp_config
        cfg = RappiConfig(token="valid-token", device_id="dev-1")
        cm.save(cfg)
        client = RappiClient(config=cfg, config_manager=cm)
        async with client:
            assert client._http is not None
        # After exit, http should be closed (no error)


class TestRappiClientRequest:
    async def test_401_raises_token_expired(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client._http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenExpiredError):
            await mock_client.get("/some-path")

    async def test_400_raises_api_error(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_client._http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(RappiAPIError) as exc_info:
            await mock_client.get("/some-path")
        assert exc_info.value.status_code == 400

    async def test_500_raises_api_error(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_client._http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(RappiAPIError) as exc_info:
            await mock_client.post("/path")
        assert exc_info.value.status_code == 500

    async def test_empty_response_returns_dict(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await mock_client.get("/path")
        assert result == {}

    async def test_json_response(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        result = await mock_client.get("/path")
        assert result == {"key": "value"}

    async def test_get_delegates(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"ok":true}'
        mock_response.json.return_value = {"ok": True}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await mock_client.get("/test")
        mock_client._http.request.assert_called_once_with("GET", "/test")

    async def test_post_delegates(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await mock_client.post("/test", json={"data": 1})
        mock_client._http.request.assert_called_once_with("POST", "/test", json={"data": 1})

    async def test_put_delegates(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await mock_client.put("/test", json={})
        mock_client._http.request.assert_called_once_with("PUT", "/test", json={})

    async def test_delete_delegates(self, mock_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_client._http.request = AsyncMock(return_value=mock_response)

        await mock_client.delete("/test")
        mock_client._http.request.assert_called_once_with("DELETE", "/test")

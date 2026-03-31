"""Async HTTP client for the Rappi API with automatic header injection and error handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from rappi.config import ConfigManager, RappiConfig
from rappi.constants import BASE_URL, build_headers

if TYPE_CHECKING:
    from rappi.memory.manager import MemoryManager


class TokenExpiredError(Exception):
    """Raised when the API returns 401, indicating the token has expired."""


class RappiAPIError(Exception):
    """Raised for non-2xx responses from the Rappi API."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class RappiClient:
    """Async HTTP client that injects auth headers and handles common errors."""

    def __init__(
        self,
        config: RappiConfig | None = None,
        config_manager: ConfigManager | None = None,
        memory: MemoryManager | None = None,
    ):
        self._config_manager = config_manager or ConfigManager()
        self._config = config or self._config_manager.load()
        self._http: httpx.AsyncClient | None = None
        self._memory = memory

    @property
    def config(self) -> RappiConfig:
        return self._config

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def memory(self) -> MemoryManager | None:
        return self._memory

    async def __aenter__(self) -> RappiClient:
        if not self._config.token:
            raise TokenExpiredError("No token configured. Run: rappi auth login --token <your-token>")
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=build_headers(self._config.token, self._config.device_id),
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http:
            await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        assert self._http is not None, "Use 'async with RappiClient() as client:'"
        response = await self._http.request(method, path, **kwargs)
        if response.status_code == 401:
            raise TokenExpiredError("Token expired. Run: rappi auth login --token <new-token>")
        if response.status_code >= 400:
            raise RappiAPIError(response.status_code, response.text[:500])
        if not response.content:
            return {}
        return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Any:
        return await self._request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self._request("DELETE", path, **kwargs)

# Contributing to Rappi Claude Plugin

Thanks for your interest in contributing! This project is a Claude plugin for ordering from Rappi.

## Quick Start

```bash
git clone https://github.com/garavitgabriel/rappi-claude-plugin.git
cd rappi-claude-plugin
uv sync --group dev
uv run pytest tests/ -q    # 196 tests, all should pass
```

## Project Structure

```
src/rappi/
├── mcp/server.py       # 39 MCP tools — the plugin's interface
├── services/           # Business logic (one file per domain)
├── models/             # Pydantic data models
├── memory/             # SQLite persistence + intelligence engine
├── cli/                # Terminal interface
├── constants.py        # ALL API endpoints, headers, country config
├── config.py           # User config (~/.rappi/config.json)
└── client.py           # HTTP client with auth injection
```

## Common Contributions

### Add a New Country

Add one entry to `COUNTRIES` in `src/rappi/constants.py`:

```python
COUNTRIES = {
    "co": {"domain": "www.rappi.com.co", "api_prefix": "", "name": "Colombia"},
    "mx": {"domain": "www.rappi.com.mx", "api_prefix": "mx", "name": "Mexico"},
    "br": {"domain": "www.rappi.com.br", "api_prefix": "br", "name": "Brazil"},  # Add this
}
```

The API base URL pattern is `services.{prefix}grability.rappi.com`. Test with `RAPPI_COUNTRY=br uv run rappi auth login`.

### Add a New MCP Tool

1. **Add endpoint** to `src/rappi/constants.py` (Endpoints class)
2. **Add service function** in the appropriate `src/rappi/services/*.py` file
3. **Add the tool** in `src/rappi/mcp/server.py`:

```python
@mcp.tool()
async def my_new_tool(param: str) -> dict:
    """Description for Claude.

    When to use: ...
    Next step: ...
    """
    async with _client_synced() as client:
        result = await _my_service_function(client, param)
        return {"key": result}
```

4. **Run tests**: `uv run pytest tests/ -q`

### Add a New API Endpoint

Check `API_ENDPOINTS.md` first — the endpoint may already be documented. If adding a new one:

1. Add the path to `src/rappi/constants.py` (Endpoints class)
2. Note which `x-application-id` header it needs (see `HEADERS_BROWSE`, `HEADERS_CHECKOUT` in constants.py)
3. Create the service function
4. Some endpoints need specific headers — pass them via `headers=HEADERS_BROWSE` in the service call

### Update the `app-version` Header

Rappi deploys new versions regularly. If you start getting 403 errors:

1. Open rappi.com.co (or .mx) in Chrome DevTools
2. Look at any API request's `app-version` header
3. Update `APP_VERSION` in `src/rappi/constants.py`

## Code Style

- Async everywhere (services, MCP tools)
- Services return Pydantic models or dicts
- MCP tools always return `dict` (never raw models)
- Memory operations are best-effort (wrapped in try/except, never block ordering)
- Use `_client_synced()` for tools that need location, `_client_with_memory()` when caching data

## Testing

```bash
uv run pytest tests/ -q                    # All automated tests
uv run pytest tests/test_services_cart.py  # Specific test file

# Live API test (requires auth)
uv run python -c "
import asyncio
from rappi.mcp.server import explore_verticals
r = asyncio.run(explore_verticals())
print(r)
"
```

## Pull Requests

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run `uv run pytest tests/ -q` — all tests must pass
5. Submit a PR with a clear description

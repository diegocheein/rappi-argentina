"""Browser-based authentication — opens Rappi login and intercepts the Bearer token."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from rappi.constants import USER_AGENT


LOGIN_URL = "https://www.rappi.com.co/login"
AUTH_ENDPOINT = "/ms/application-user/auth"
TIMEOUT_MS = 5 * 60 * 1000  # 5 minutes


@dataclass
class CapturedCredentials:
    token: str
    device_id: str
    user_name: str | None = None
    email: str | None = None


async def login_with_browser(
    headless: bool = False,
    on_status: callable | None = None,
) -> CapturedCredentials:
    """Launch a browser for the user to log in, intercept the auth token.

    Args:
        headless: If True, run in headless mode (mainly for testing).
        on_status: Optional callback(message: str) for progress updates.

    Returns:
        CapturedCredentials with token and device_id.

    Raises:
        TimeoutError: If the user doesn't complete login within 5 minutes.
        RuntimeError: If Playwright browsers aren't installed.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required for browser login. "
            "Run: uv run playwright install chromium"
        )

    def _status(msg: str) -> None:
        if on_status:
            on_status(msg)

    result: CapturedCredentials | None = None
    done_event = asyncio.Event()

    async with async_playwright() as pw:
        _status("Launching browser...")
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 420, "height": 800},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()

        async def _on_response(response):
            nonlocal result
            # We're looking for a successful GET to the auth endpoint
            if AUTH_ENDPOINT not in response.url:
                return
            if response.status != 200:
                return

            try:
                body = await response.json()
            except Exception:
                return

            # Verify it's a real auth response (has user id and email)
            if not body.get("id") or not body.get("email"):
                return

            # Extract token from the request headers
            request = response.request
            auth_header = request.headers.get("authorization", "")
            device_id = request.headers.get("deviceid", "")

            if not auth_header.startswith("Bearer ft."):
                return

            token = auth_header.removeprefix("Bearer ").strip()
            result = CapturedCredentials(
                token=token,
                device_id=device_id,
                user_name=body.get("name"),
                email=body.get("email"),
            )
            _status(f"Token captured for {result.user_name or result.email}!")
            done_event.set()

        page.on("response", _on_response)

        _status("Opening Rappi login page...")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        _status("Please log in with your phone number and OTP...")

        # Wait for the token to be captured or timeout
        try:
            await asyncio.wait_for(done_event.wait(), timeout=TIMEOUT_MS / 1000)
        except asyncio.TimeoutError:
            await browser.close()
            raise TimeoutError(
                "Login timed out after 5 minutes. Please try again."
            )

        await browser.close()

    if result is None:
        raise RuntimeError("Failed to capture authentication token.")

    return result

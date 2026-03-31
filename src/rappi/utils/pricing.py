"""Price formatting utilities for COP (Colombian Pesos)."""

import re


def format_cop(amount: int | float) -> str:
    """Format a price in COP with dot separators. E.g. 35500 -> '$35.500'."""
    return f"${int(amount):,.0f}".replace(",", ".")


def strip_html(text: str | None) -> str | None:
    """Strip HTML tags from API response text."""
    if not text:
        return None
    return re.sub(r"<[^>]+>", "", text).strip() or None

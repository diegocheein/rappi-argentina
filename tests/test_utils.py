"""Tests for rappi.utils — compound IDs, COP formatting, and HTML stripping."""

import pytest

from rappi.utils.ids import make_compound_id, parse_compound_id
from rappi.utils.pricing import format_cop, strip_html


# ---------------------------------------------------------------------------
# Compound ID tests (§7 Cart — Add Item)
# ---------------------------------------------------------------------------

class TestCompoundId:
    def test_make_compound_id(self):
        assert make_compound_id(900123, 456) == "900123_456"

    def test_parse_compound_id(self):
        store_id, product_id = parse_compound_id("900123_456")
        assert store_id == 900123
        assert product_id == 456

    def test_round_trip(self):
        original_store, original_product = 12345, 67890
        compound = make_compound_id(original_store, original_product)
        store_id, product_id = parse_compound_id(compound)
        assert store_id == original_store
        assert product_id == original_product

    def test_parse_with_underscores_in_product_id(self):
        """Only splits on first underscore."""
        store_id, product_id = parse_compound_id("100_200_300")
        assert store_id == 100
        # "200_300" should fail int() — this tests the edge case
        with pytest.raises(ValueError):
            parse_compound_id("abc_def")


# ---------------------------------------------------------------------------
# COP formatting tests (§10 Checkout)
# ---------------------------------------------------------------------------

class TestFormatCop:
    def test_basic_price(self):
        assert format_cop(35500) == "$35.500"

    def test_zero(self):
        assert format_cop(0) == "$0"

    def test_large_price(self):
        assert format_cop(1500000) == "$1.500.000"

    def test_small_price(self):
        assert format_cop(500) == "$500"

    def test_float_price(self):
        result = format_cop(35500.99)
        assert result == "$35.500"  # int() truncates

    def test_negative_price(self):
        # Should handle gracefully even if unusual
        result = format_cop(-5000)
        assert "-" in result


# ---------------------------------------------------------------------------
# HTML stripping tests (§10 No HTML in checkout output)
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_strips_bold_tags(self):
        assert strip_html("<b>hello</b>") == "hello"

    def test_strips_font_tags(self):
        assert strip_html('<font color="red">text</font>') == "text"

    def test_strips_nested_tags(self):
        assert strip_html("<b><i>nested</i></b>") == "nested"

    def test_preserves_plain_text(self):
        assert strip_html("no tags here") == "no tags here"

    def test_none_input(self):
        assert strip_html(None) is None

    def test_empty_string(self):
        assert strip_html("") is None

    def test_only_tags(self):
        assert strip_html("<br><br>") is None

    def test_mixed_content(self):
        result = strip_html("Price: <b>$35.500</b> COP")
        assert result == "Price: $35.500 COP"

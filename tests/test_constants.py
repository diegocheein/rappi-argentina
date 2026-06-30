"""Tests for rappi.constants — headers, endpoints, and image URLs."""

from rappi.constants import (
    APP_VERSION,
    BASE_URL,
    IMAGES_BASE_URL,
    Endpoints,
    _country_code,
    build_headers,
    resolve_image_url,
)

# AR's gateway rejects the CO/MX headers — see build_headers() in constants.py
_IS_AR = _country_code == "ar"


class TestBuildHeaders:
    def test_contains_authorization(self):
        headers = build_headers("my-token", "my-device")
        assert headers["authorization"] == "Bearer my-token"

    def test_contains_device_id(self):
        headers = build_headers("t", "dev-123")
        assert headers["deviceid"] == "dev-123"

    def test_contains_required_headers(self):
        headers = build_headers("t", "d")
        # Common to every country
        for key in ["authorization", "deviceid", "accept", "accept-language",
                    "referer", "user-agent"]:
            assert key in headers, f"Missing header: {key}"
        # CO/MX also send these; AR must NOT (gateway returns empty 200 otherwise)
        co_mx_only = ["app-version", "origin", "vendor", "x-application-id"]
        for key in co_mx_only:
            assert (key in headers) is (not _IS_AR), f"{key} presence wrong for country={_country_code}"

    def test_app_version_header(self):
        headers = build_headers("t", "d")
        if _IS_AR:
            assert "app-version" not in headers
        else:
            assert headers["app-version"] == APP_VERSION

    def test_accept_json(self):
        headers = build_headers("t", "d")
        assert headers["accept"] == "application/json"

    def test_vendor_is_rappi(self):
        headers = build_headers("t", "d")
        if _IS_AR:
            assert "vendor" not in headers
        else:
            assert headers["vendor"] == "rappi"


class TestResolveImageUrl:
    def test_relative_path_products(self):
        result = resolve_image_url("abc123.jpg", "products")
        assert result == f"{IMAGES_BASE_URL}/products/abc123.jpg"

    def test_relative_path_restaurants_logo(self):
        result = resolve_image_url("logo.png", "restaurants_logo")
        assert result == f"{IMAGES_BASE_URL}/restaurants_logo/logo.png"

    def test_absolute_url_passthrough(self):
        url = "https://cdn.example.com/image.jpg"
        assert resolve_image_url(url) == url

    def test_http_url_passthrough(self):
        url = "http://example.com/img.png"
        assert resolve_image_url(url) == url

    def test_none_returns_none(self):
        assert resolve_image_url(None) is None

    def test_empty_string_returns_none(self):
        assert resolve_image_url("") is None

    def test_default_prefix_is_products(self):
        result = resolve_image_url("test.jpg")
        assert "/products/test.jpg" in result


class TestEndpoints:
    def test_store_detail_has_trailing_slash(self):
        path = Endpoints.STORE_DETAIL.format(store_id=123)
        assert path.endswith("/")

    def test_product_toppings_has_trailing_slash(self):
        path = Endpoints.PRODUCT_TOPPINGS.format(store_id=1, product_id=2)
        assert path.endswith("/")

    def test_cart_add_uses_store_type(self):
        path = Endpoints.CART_ADD.format(store_type="restaurant")
        assert "restaurant" in path

    def test_cart_remove_uses_compound_id(self):
        path = Endpoints.CART_REMOVE.format(store_type="turbo", compound_product_id="100_200")
        assert "100_200" in path
        assert "turbo" in path

    def test_store_menu_format(self):
        path = Endpoints.STORE_MENU.format(store_id=999)
        assert "999" in path
        assert "menu" in path

    def test_checkout_detail_format(self):
        path = Endpoints.CHECKOUT_DETAIL.format(store_type="restaurant")
        assert "restaurant" in path
        assert "checkout" in path

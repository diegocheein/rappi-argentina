"""Base URL, endpoints, and header templates for the Rappi API."""

BASE_URL = "https://services.grability.rappi.com"
IMAGES_BASE_URL = "https://images.rappi.com"

# Default coordinates (Bogota)
DEFAULT_LAT = 4.624335
DEFAULT_LNG = -74.063644

# Mobile user agent matching the Rappi web app
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
)

APP_VERSION = "e1de6be43aa29091011474615d7ac0810051c36a"


def build_headers(token: str, device_id: str) -> dict[str, str]:
    """Build the full header set required by every Rappi API request."""
    headers = {
        "authorization": f"Bearer {token}",
        "deviceid": device_id,
        "accept": "application/json",
        "accept-language": "es-CO",
        "app-version": APP_VERSION,
        "needappsflyerid": "false",
        "origin": "https://www.rappi.com.co",
        "referer": "https://www.rappi.com.co/",
        "user-agent": USER_AGENT,
        "vendor": "rappi",
        "x-application-id": f"rappi-microfront-web/{APP_VERSION}",
        "sec-ch-ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
    }
    return headers


# --- Endpoint paths ---

class Endpoints:
    # Auth / User
    USER_PROFILE = "/ms/application-user/auth"
    IS_PRIME = "/api/ms/rappi-prime/is-prime"

    # Address
    REVERSE_GEOCODE = "/api/ms/address/reverse-geocode"
    LIST_ADDRESSES = "/api/ms/users-address/addresses"
    SET_ACTIVE_ADDRESS = "/api/ms/users-address/addresses/{address_id}/active"

    # Search
    UNIFIED_SEARCH = "/api/pns-global-search-api/v1/unified-search"

    # Stores
    RESTAURANT_CATALOG = "/api/restaurant-bus/stores/catalog-paged/home"
    STORE_DETAIL = "/api/web-gateway/web/stores-router/id/{store_id}/"  # trailing slash required
    STORE_MENU = "/api/restaurant-bus/store/{store_id}/menu"  # separate endpoint for menu corridors
    PRODUCT_TOPPINGS = "/api/web-gateway/web/restaurants-bus/products/toppings/{store_id}/{product_id}/"  # trailing slash required

    # Cart
    CART_ADD = "/api/ms/shopping-cart/v2/{store_type}/store"
    CART_GET_ALL = "/api/ms/shopping-cart/v1/all/get"
    CART_REMOVE = "/api/ms/shopping-cart/v2/{store_type}/product/{compound_product_id}"
    CART_RECALCULATE = "/api/ms/shopping-cart/v1/{store_type}/recalculate"

    # Checkout
    CHECKOUT_DETAIL = "/api/ms/shopping-cart/v1/{store_type}/checkout/detail"
    CHECKOUT_WIDGETS = "/api/ms/checkout-component/{store_type}"
    SET_TIP = "/api/ms/shopping-cart/v1/{store_type}/tip"
    SET_PAYMENT_METHOD = "/api/ms/shopping-cart/v1/{store_type}/payment-method"
    PLACE_ORDER = "/api/ms/shopping-cart-proxy/{store_type}/checkout"

    # Orders
    GET_ORDERS = "/api/user-order-home/orders"


def resolve_image_url(path: str | None, prefix: str = "products") -> str | None:
    """Resolve a relative image path to a full URL."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{IMAGES_BASE_URL}/{prefix}/{path}"

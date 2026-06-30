"""Base URL, endpoints, and header templates for the Rappi Argentina API."""

IMAGES_BASE_URL = "https://images.rappi.com"

# Rappi Argentina
RAPPI_DOMAIN = "www.rappi.com.ar"
BASE_URL = "https://services.rappi.com.ar"
ACCEPT_LANGUAGE = "es-AR"

# Default coordinates (0,0 — auto-synced from active address at runtime)
DEFAULT_LAT = 0.0
DEFAULT_LNG = 0.0

# Mobile user agent matching the Rappi web app
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
)

def build_headers(token: str, device_id: str) -> dict[str, str]:
    """Build the minimal header set Rappi Argentina's API requires.

    AR's gateway returns an empty 200 (no body) if the extra headers other
    Rappi markets send (app-version, x-application-id, vendor, origin,
    sec-fetch-*) are present, so we send only what the AR web app sends.
    """
    return {
        "authorization": f"Bearer {token}",
        "deviceid": device_id,
        "accept": "application/json",
        "accept-language": ACCEPT_LANGUAGE,
        "needappsflyerid": "false",
        "referer": f"https://{RAPPI_DOMAIN}/",
        "user-agent": USER_AGENT,
        "sec-ch-ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Android"',
    }


# Context overrides — AR keeps only the useful context flags (no app-version /
# x-application-id, which would trigger the empty-200 behaviour).
HEADERS_BROWSE = {
    "include_context_info": "true",
    "language": "es",
}
HEADERS_CHECKOUT = {}

HEADERS_FAVORITES = {
    "content-type": "application/json; charset=UTF-8",
}


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
    TIP_SUGGESTIONS = "/api/ms/core-tip/user-segmentation"
    SET_PAYMENT_METHOD = "/api/ms/shopping-cart/v1/{store_type}/payment-method"
    PLACE_ORDER = "/api/ms/shopping-cart-proxy/{store_type}/checkout"

    # Orders
    GET_ORDERS = "/api/user-order-home/orders"
    ACTIVE_ORDERS_V3 = "/api/user-order-home/v3/orders"
    ORDER_RESUME = "/order-resume/fully/{order_id}"
    ORDER_REALTIME_STATE = "/api/ms/user-order-state/auth/{order_id}"
    ORDER_PRODUCTS = "/api/support-order-cost/orders/{order_id}/products"
    ORDER_COST_BREAKDOWN = "/api/support-order-cost/orders/{order_id}/costs-and-discounts"

    # Homepage / Verticals
    HOME_VERTICALS = "/home/high/"
    STORE_TYPE_HIERARCHY = "/api/web-gateway/web/stores-router/available/principal/"

    # Dynamic Content (store browsing — aisles, categories, store info)
    DYNAMIC_CONTENT = "/api/web-gateway/web/dynamic/context/content/"

    # CPG In-Store Search (Turbo, markets — richer than unified search)
    CPG_PRODUCT_SEARCH = "/api/cpgs/search/v2/store/{store_id}/products"

    # Payment
    DEFAULT_PAYMENT_METHOD = "/api/ms/payment-method/default-payment-method"

    # Account
    FAVORITE_STORES_API = "/api/pns-global-search-api/v1/unified-favorite-stores"
    RAPPI_CREDITS = "/api/ms/rappi-credits-mongo/"


def resolve_image_url(path: str | None, prefix: str = "products") -> str | None:
    """Resolve a relative image path to a full URL."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{IMAGES_BASE_URL}/{prefix}/{path}"

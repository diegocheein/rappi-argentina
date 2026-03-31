"""Rappi CLI — main Typer app and subcommand registration."""

import typer

from rappi.cli.address import app as address_app
from rappi.cli.auth import app as auth_app
from rappi.cli.cart import app as cart_app
from rappi.cli.favorites import app as favorites_app
from rappi.cli.history import app as history_app
from rappi.cli.interactive import launch_interactive
from rappi.cli.order import app as order_app
from rappi.cli.prefs import app as prefs_app
from rappi.cli.search import app as search_app
from rappi.cli.store import app as store_app

app = typer.Typer(
    name="rappi",
    help="Rappi food delivery from your terminal. Run 'rappi go' for interactive ordering.",
    no_args_is_help=True,
)

app.add_typer(auth_app, name="auth", help="Authentication commands")
app.add_typer(address_app, name="address", help="Delivery address management")
app.add_typer(search_app, name="search", help="Search products and stores")
app.add_typer(store_app, name="store", help="Browse stores and menus")
app.add_typer(cart_app, name="cart", help="Shopping cart management")
app.add_typer(order_app, name="order", help="Checkout and order tracking")
app.add_typer(history_app, name="history", help="Order history")
app.add_typer(favorites_app, name="favorites", help="Manage favorite stores")
app.add_typer(prefs_app, name="prefs", help="User preferences")


@app.command()
def go() -> None:
    """Start an interactive ordering session — the easiest way to order."""
    launch_interactive()


def main() -> None:
    app()

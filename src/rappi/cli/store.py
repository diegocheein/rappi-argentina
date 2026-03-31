"""CLI commands for store browsing."""

import asyncio

import typer
from rich.console import Console

from rappi.cli.formatters import render_catalog, render_menu, render_store_detail, render_toppings
from rappi.client import RappiClient
from rappi.services.store import get_product_toppings, get_restaurant_catalog, get_store_detail

app = typer.Typer()
console = Console()


@app.command("browse")
def browse_cmd(
    offset: int = typer.Option(0, "--offset", "-o", help="Pagination offset"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of results"),
) -> None:
    """Browse nearby restaurants."""

    async def _run():
        async with RappiClient() as client:
            return await get_restaurant_catalog(client, offset=offset, limit=limit)

    stores = asyncio.run(_run())
    if not stores:
        console.print("[yellow]No restaurants found nearby.[/yellow]")
        return
    console.print(render_catalog(stores))


@app.command("detail")
def detail_cmd(store_id: int = typer.Argument(..., help="Store ID")) -> None:
    """Get store info and full menu."""

    async def _run():
        async with RappiClient() as client:
            return await get_store_detail(client, store_id)

    store = asyncio.run(_run())
    render_store_detail(store)
    render_menu(store.corridors)


@app.command("toppings")
def toppings_cmd(
    store_id: int = typer.Argument(..., help="Store ID"),
    product_id: int = typer.Argument(..., help="Product ID"),
) -> None:
    """View toppings/customizations for a product."""

    async def _run():
        async with RappiClient() as client:
            return await get_product_toppings(client, store_id, product_id)

    result = asyncio.run(_run())
    render_toppings(result.categories)

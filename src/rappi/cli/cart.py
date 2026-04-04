"""CLI commands for cart management."""

import asyncio

import typer
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from rappi.cli.formatters import render_toppings
from rappi.client import RappiClient
from rappi.models.store import Topping
from rappi.services.cart import add_to_cart, get_carts, recalculate_cart, remove_from_cart
from rappi.services.store import get_product_toppings, get_store_detail
from rappi.utils.ids import make_compound_id
from rappi.utils.pricing import format_cop

app = typer.Typer()
console = Console()


def _render_carts(carts):
    if not carts:
        console.print("[yellow]Your cart is empty.[/yellow]")
        return
    for cart in carts:
        for store in cart.stores:
            table = Table(title=f"{store.name or 'Store'} (ID: {store.id})")
            table.add_column("Product", style="bold")
            table.add_column("Qty", justify="center")
            table.add_column("Price", justify="right")
            table.add_column("Total", justify="right")
            table.add_column("Cart ID", style="dim")
            for p in store.products:
                table.add_row(
                    p.name or "—",
                    str(p.units),
                    format_cop(p.price),
                    format_cop(p.total),
                    p.id,
                )
            table.add_section()
            table.add_row("", "", "[bold]Products[/bold]", f"[bold]{format_cop(store.product_total)}[/bold]", "")
            for charge in store.charges:
                table.add_row("", "", charge.charge_type or "Fee", format_cop(charge.total), "")
            table.add_row("", "", "[bold]Total[/bold]", f"[bold]{format_cop(store.total)}[/bold]", "")
            console.print(table)
            if not store.is_open:
                console.print("[red]This store is currently closed.[/red]")


@app.command("show")
def show_cmd() -> None:
    """Show current cart contents."""

    async def _run():
        async with RappiClient() as client:
            return await get_carts(client)

    carts = asyncio.run(_run())
    _render_carts(carts)


@app.command("add")
def add_cmd(
    store_id: int = typer.Argument(..., help="Store ID"),
    product_id: int = typer.Argument(..., help="Product ID"),
    quantity: int = typer.Option(1, "--qty", "-q", help="Quantity"),
) -> None:
    """Add a product to the cart (with interactive topping selection)."""

    async def _run():
        async with RappiClient() as client:
            # Fetch store detail to get the product info (need real price)
            store = await get_store_detail(client, store_id)
            product = None
            for corridor in store.corridors:
                for p in corridor.products:
                    if p.id == product_id:
                        product = p
                        break
                if product:
                    break

            if not product:
                console.print(f"[red]Product {product_id} not found in store {store_id}.[/red]")
                raise typer.Exit(1)

            console.print(f"Adding [bold]{product.name}[/bold] — {format_cop(product.price)}")

            # Handle toppings
            selected_toppings: list[Topping] = []
            if product.has_toppings:
                toppings_resp = await get_product_toppings(client, store_id, product_id)
                if toppings_resp.categories:
                    render_toppings(toppings_resp.categories)
                    console.print()

                    for cat in toppings_resp.categories:
                        required = cat.min_toppings_for_categories > 0
                        label = "[red](required)[/red]" if required else "(optional)"
                        console.print(f"\n[bold]{cat.description or f'Category {cat.id}'}[/bold] {label}")

                        available = [t for t in cat.toppings if t.is_available]
                        for i, t in enumerate(available):
                            price = f" +{format_cop(t.price)}" if t.price > 0 else ""
                            console.print(f"  {i + 1}. {t.description or '—'}{price}")

                        if not available:
                            continue

                        if cat.max_toppings_for_categories == 1:
                            # Single selection
                            if required:
                                choice = IntPrompt.ask(
                                    "Select option",
                                    choices=[str(i + 1) for i in range(len(available))],
                                )
                                selected_toppings.append(available[choice - 1])
                            else:
                                choice_str = Prompt.ask(
                                    "Select option (or press Enter to skip)",
                                    default="",
                                )
                                if choice_str:
                                    idx = int(choice_str) - 1
                                    if 0 <= idx < len(available):
                                        selected_toppings.append(available[idx])
                        else:
                            # Multi selection
                            choices_str = Prompt.ask(
                                f"Select options (comma-separated, max {cat.max_toppings_for_categories}, or Enter to skip)",
                                default="",
                            )
                            if choices_str:
                                for part in choices_str.split(","):
                                    idx = int(part.strip()) - 1
                                    if 0 <= idx < len(available):
                                        selected_toppings.append(available[idx])

            result = await add_to_cart(client, store_id, product, selected_toppings, quantity)
            return result

    carts = asyncio.run(_run())
    console.print("[green]Added to cart![/green]")
    _render_carts(carts)


@app.command("remove")
def remove_cmd(
    store_id: int = typer.Argument(..., help="Store ID"),
    product_id: int = typer.Argument(..., help="Product ID"),
) -> None:
    """Remove a product from the cart."""
    compound_id = make_compound_id(store_id, product_id)

    async def _run():
        async with RappiClient() as client:
            return await remove_from_cart(client, store_id, compound_id)

    carts = asyncio.run(_run())
    console.print(f"[green]Removed {compound_id} from cart.[/green]")


@app.command("recalculate")
def recalculate_cmd() -> None:
    """Recalculate cart totals."""

    async def _run():
        async with RappiClient() as client:
            return await recalculate_cart(client)

    cart = asyncio.run(_run())
    _render_carts([cart])

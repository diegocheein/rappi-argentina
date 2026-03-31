"""CLI commands for checkout and order tracking."""

import asyncio
import time

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

from rappi.client import RappiClient
from rappi.services.cart import get_carts, recalculate_cart
from rappi.services.checkout import get_checkout_detail, place_order, set_tip
from rappi.services.order import get_orders
from rappi.utils.pricing import format_cop, strip_html

app = typer.Typer()
console = Console()


@app.command("checkout")
def checkout_cmd(
    tip: int | None = typer.Option(None, "--tip", "-t", help="Tip amount in COP"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Complete checkout and place order."""

    async def _run():
        async with RappiClient() as client:
            # Recalculate cart
            console.print("[dim]Recalculating cart...[/dim]")
            await recalculate_cart(client)

            # Set tip if provided
            if tip is not None:
                console.print(f"[dim]Setting tip to {format_cop(tip)}...[/dim]")
                await set_tip(client, tip)

            # Get checkout detail
            detail = await get_checkout_detail(client)

            # Display summary
            for summary in detail.summary:
                if summary.header:
                    console.print(f"\n[bold]{strip_html(summary.header.title) or 'Order'}[/bold]")
                for item in summary.details:
                    key = strip_html(item.key)
                    value = strip_html(item.value)
                    if not key or not value:
                        continue
                    if item.type == "total":
                        console.print(f"  [bold]{key}: {value}[/bold]")
                    else:
                        console.print(f"  {key}: {value}")

            if not detail.return_key:
                console.print("[red]No return_key received — cannot place order.[/red]")
                raise typer.Exit(1)

            # Confirm
            if not yes:
                if not Confirm.ask("\nPlace this order?"):
                    console.print("[yellow]Order cancelled.[/yellow]")
                    raise typer.Exit(0)

            # Place order
            console.print("[dim]Placing order...[/dim]")
            result = await place_order(client, detail.return_key)
            console.print(Panel("[green][bold]Order placed![/bold][/green]", title="Success"))
            return result

    asyncio.run(_run())


@app.command("list")
def orders_cmd() -> None:
    """View active and recent orders."""

    async def _run():
        async with RappiClient() as client:
            return await get_orders(client)

    result = asyncio.run(_run())

    if result.active_orders:
        table = Table(title="Active Orders")
        table.add_column("ID", style="dim")
        table.add_column("Store", style="bold")
        table.add_column("Status")
        table.add_column("Total", justify="right")
        table.add_column("ETA")
        table.add_column("Tip", justify="right")
        for order in result.active_orders:
            state_colors = {
                "created": "yellow",
                "in_store": "cyan",
                "on_the_way": "blue",
                "delivered": "green",
            }
            color = state_colors.get(order.state or "", "white")
            store_name = order.store.name if order.store else "—"
            table.add_row(
                str(order.id),
                store_name,
                f"[{color}]{order.state}[/{color}]",
                format_cop(order.total),
                f"{order.eta} min" if order.eta else "—",
                format_cop(order.tip) if order.tip else "—",
            )
        console.print(table)
    else:
        console.print("[dim]No active orders.[/dim]")

    if result.cancel_orders:
        console.print()
        table = Table(title="Cancelled Orders")
        table.add_column("ID", style="dim")
        table.add_column("Store", style="bold")
        for order in result.cancel_orders:
            store_name = order.store.name if order.store else "—"
            table.add_row(str(order.id), store_name)
        console.print(table)


@app.command("track")
def track_cmd(
    interval: int = typer.Option(10, "--interval", "-i", help="Refresh interval in seconds"),
) -> None:
    """Live-track active orders (auto-refreshes)."""

    async def _fetch():
        async with RappiClient() as client:
            return await get_orders(client)

    def _build_display(orders_resp):
        if not orders_resp.active_orders:
            return Panel("[dim]No active orders to track.[/dim]", title="Order Tracker")
        lines = []
        for order in orders_resp.active_orders:
            state_icons = {
                "created": "[ ]",
                "in_store": "[*]",
                "on_the_way": "[>]",
                "delivered": "[v]",
            }
            icon = state_icons.get(order.state or "", "[?]")
            store_name = order.store.name if order.store else "Unknown"
            eta = f"ETA: {order.eta} min" if order.eta else ""
            lines.append(f"{icon} #{order.id} {store_name} — {order.state} {eta}")
        return Panel("\n".join(lines), title="Order Tracker", subtitle="Press Ctrl+C to stop")

    try:
        with Live(console=console, refresh_per_second=0.5) as live:
            while True:
                result = asyncio.run(_fetch())
                live.update(_build_display(result))
                if not result.active_orders:
                    break
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("[dim]Stopped tracking.[/dim]")

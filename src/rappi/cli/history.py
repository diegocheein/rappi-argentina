"""CLI commands for order history."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from rappi.memory import MemoryManager
from rappi.utils.pricing import format_cop

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def list_cmd(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of orders to show"),
) -> None:
    """Show recent order history."""

    async def _run():
        async with MemoryManager() as memory:
            return await memory.orders.list_recent(limit=limit)

    orders = asyncio.run(_run())

    if not orders:
        console.print("[yellow]No order history yet.[/yellow] Place an order with [bold]rappi go[/bold].")
        return

    table = Table(title="Order History")
    table.add_column("ID", style="dim")
    table.add_column("Store", style="bold")
    table.add_column("Items")
    table.add_column("Total", justify="right")
    table.add_column("Tip", justify="right")
    table.add_column("Date")
    table.add_column("Status")

    for order in orders:
        items_str = ""
        if order.items:
            names = [f"{i['quantity']}x {i['name']}" for i in order.items[:3]]
            items_str = ", ".join(names)
            if len(order.items) > 3:
                items_str += f" +{len(order.items) - 3} more"

        table.add_row(
            str(order.id) if order.id else "—",
            order.store_name or "—",
            items_str or "—",
            format_cop(order.total),
            format_cop(order.tip) if order.tip else "—",
            order.placed_at[:10] if order.placed_at else "—",
            order.state or "—",
        )

    console.print(table)


@app.command("detail")
def detail_cmd(order_id: int = typer.Argument(..., help="Order ID")) -> None:
    """Show details for a specific order."""

    async def _run():
        async with MemoryManager() as memory:
            return await memory.orders.get_by_id(order_id)

    order = asyncio.run(_run())

    if not order:
        console.print(f"[red]Order {order_id} not found in history.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Order #{order.id}[/bold] — {order.store_name or '—'}")
    console.print(f"Date: {order.placed_at}")
    console.print(f"Status: {order.state}")
    console.print(f"Total: [green]{format_cop(order.total)}[/green]")
    if order.tip:
        console.print(f"Tip: {format_cop(order.tip)}")

    if order.items:
        console.print("\n[bold]Items:[/bold]")
        for item in order.items:
            toppings = ""
            if item.get("toppings"):
                names = [t.get("description", "") for t in item["toppings"] if t.get("description")]
                if names:
                    toppings = f" [dim]({', '.join(names)})[/dim]"
            console.print(f"  {item['quantity']}x {item['name']}  {format_cop(item['total_price'])}{toppings}")


@app.command("stores")
def frequent_stores_cmd() -> None:
    """Show your most-ordered-from stores."""

    async def _run():
        async with MemoryManager() as memory:
            return await memory.orders.get_frequent_stores()

    stores = asyncio.run(_run())

    if not stores:
        console.print("[yellow]No order history yet.[/yellow]")
        return

    table = Table(title="Frequent Stores")
    table.add_column("Store", style="bold")
    table.add_column("Orders", justify="right")
    table.add_column("Last Order")
    table.add_column("Type", style="dim")

    for s in stores:
        table.add_row(
            s["store_name"] or "—",
            str(s["order_count"]),
            s["last_ordered"][:10] if s["last_ordered"] else "—",
            s["store_type"] or "—",
        )

    console.print(table)

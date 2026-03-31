"""Rich formatting helpers for CLI output."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from rappi.models.address import Address
from rappi.models.store import (
    CatalogStore,
    Corridor,
    Product,
    SearchStore,
    StoreDetail,
    ToppingCategory,
)
from rappi.utils.pricing import format_cop

console = Console()


def render_addresses(addresses: list[Address]) -> Table:
    table = Table(title="Delivery Addresses")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Address")
    table.add_column("Active", justify="center")
    table.add_column("Orders", justify="right")
    for addr in addresses:
        active = "[green]***[/green]" if addr.active else ""
        table.add_row(
            str(addr.id),
            addr.title or addr.tag or "—",
            addr.address or "—",
            active,
            str(addr.count_orders),
        )
    return table


def render_search_results(stores: list[SearchStore]) -> None:
    if not stores:
        console.print("[yellow]No results found.[/yellow]")
        return
    for store in stores:
        table = Table(
            title=f"{store.store_name} (ID: {store.store_id})",
            caption=f"ETA: {store.eta or '?'} | Delivery: {format_cop(store.shipping_cost)}",
        )
        table.add_column("Product", style="bold")
        table.add_column("Price", justify="right")
        table.add_column("ID", style="dim")
        table.add_column("Stock", justify="center")
        for p in store.products:
            stock = "[green]Yes[/green]" if p.in_stock else "[red]No[/red]"
            price = format_cop(p.price) if p.price > 0 else "[dim]$0[/dim]"
            table.add_row(p.name, price, str(p.product_id), stock)
        console.print(table)
        console.print()


def render_catalog(stores: list[CatalogStore]) -> Table:
    table = Table(title="Nearby Restaurants")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Rating", justify="center")
    table.add_column("ETA")
    table.add_column("Delivery", justify="right")
    table.add_column("Open", justify="center")
    for s in stores:
        available = "[green]Yes[/green]" if s.is_available else "[red]No[/red]"
        score = f"{s.score:.1f}" if s.score else "—"
        table.add_row(
            str(s.store_id),
            s.name or "—",
            score,
            s.eta or "—",
            format_cop(s.shipping_cost),
            available,
        )
    return table


def render_store_detail(store: StoreDetail) -> None:
    status = store.status.status if store.status else "unknown"
    status_color = "green" if status == "open" else "red"
    info = (
        f"[bold]{store.name}[/bold]\n"
        f"Address: {store.address or '—'}\n"
        f"Status: [{status_color}]{status}[/{status_color}]\n"
        f"Cooking time: {store.min_cooking_time or '?'}–{store.max_cooking_time or '?'} min"
    )
    if store.brand and store.brand.name:
        info += f"\nBrand: {store.brand.name}"
    console.print(Panel(info, title=f"Store {store.store_id}"))


def render_menu(corridors: list[Corridor]) -> None:
    if not corridors:
        console.print("[yellow]No menu items found.[/yellow]")
        return
    for corridor in corridors:
        table = Table(title=f"[bold]{corridor.name}[/bold]")
        table.add_column("ID", style="dim")
        table.add_column("Product", style="bold")
        table.add_column("Price", justify="right")
        table.add_column("Stock", justify="center")
        table.add_column("Toppings", justify="center")
        for p in corridor.products:
            stock = "[green]Yes[/green]" if p.in_stock else "[red]No[/red]"
            toppings = "[cyan]Yes[/cyan]" if p.has_toppings else "—"
            price = format_cop(p.price) if p.price > 0 else "[dim]$0[/dim]"
            table.add_row(str(p.id), p.name, price, stock, toppings)
        console.print(table)
        console.print()


def render_toppings(categories: list[ToppingCategory]) -> None:
    if not categories:
        console.print("[yellow]No toppings available.[/yellow]")
        return
    tree = Tree("[bold]Toppings[/bold]")
    for cat in categories:
        required = f" [red](required: {cat.min_toppings_for_categories}–{cat.max_toppings_for_categories})[/red]" if cat.min_toppings_for_categories > 0 else ""
        branch = tree.add(f"[bold]{cat.description or f'Category {cat.id}'}[/bold]{required}")
        for t in cat.toppings:
            available = "" if t.is_available else " [red](unavailable)[/red]"
            price = f" +{format_cop(t.price)}" if t.price > 0 else ""
            branch.add(f"[{t.id}] {t.description or '—'}{price}{available}")
    console.print(tree)


# --- Interactive mode formatters ---


def render_numbered_stores(con: Console, stores: list[SearchStore] | list[CatalogStore]) -> None:
    """Render stores as a numbered list for interactive selection."""
    for i, store in enumerate(stores, 1):
        # Handle both SearchStore and CatalogStore
        if isinstance(store, SearchStore):
            name = store.store_name or "—"
            eta = store.eta or "?"
            shipping = format_cop(store.shipping_cost)
            con.print(f"  [bold cyan]{i}.[/bold cyan] [bold]{name}[/bold]  [dim]ETA: {eta} | Delivery: {shipping}[/dim]")
            for p in store.products[:3]:  # show top 3 products
                price = format_cop(p.price) if p.price > 0 else "[dim]$0[/dim]"
                stock = "" if p.in_stock else " [red](out of stock)[/red]"
                con.print(f"       - {p.name}  {price}{stock}")
        else:
            name = store.name or "—"
            eta = store.eta or "?"
            shipping = format_cop(store.shipping_cost)
            score = f" ({store.score:.1f})" if store.score else ""
            available = "" if store.is_available else " [red](closed)[/red]"
            con.print(f"  [bold cyan]{i}.[/bold cyan] [bold]{name}[/bold]{score}  [dim]ETA: {eta} | Delivery: {shipping}[/dim]{available}")
        con.print()


def render_corridor_list(con: Console, corridors: list[Corridor]) -> None:
    """Render menu categories as a numbered list with item counts."""
    for i, corridor in enumerate(corridors, 1):
        count = len(corridor.products)
        in_stock = sum(1 for p in corridor.products if p.in_stock)
        con.print(f"  [bold cyan]{i}.[/bold cyan] [bold]{corridor.name}[/bold] [dim]({in_stock}/{count} available)[/dim]")


def render_numbered_products(con: Console, products: list[Product]) -> None:
    """Render products in a corridor as a numbered list."""
    for i, p in enumerate(products, 1):
        price = format_cop(p.price) if p.price > 0 else "[dim]$0[/dim]"
        if not p.in_stock:
            con.print(f"  [dim]{i}. {p.name}  {price}  [red]Out of stock[/red][/dim]")
        else:
            topping_hint = " [cyan]*[/cyan]" if p.has_toppings else ""
            con.print(f"  [bold cyan]{i}.[/bold cyan] {p.name}  [green]{price}[/green]{topping_hint}")


def render_cart_summary_bar(con: Console, item_count: int, total: float) -> None:
    """One-line cart status bar."""
    if item_count == 0:
        return
    con.print(Panel(
        f"[bold]Cart:[/bold] {item_count} item{'s' if item_count != 1 else ''} — [green]{format_cop(total)}[/green]",
        style="blue",
        expand=False,
    ))

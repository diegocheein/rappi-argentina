"""Interactive ordering session — guided flow through search, browse, cart, and checkout."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from rappi.cli.formatters import (
    render_cart_summary_bar,
    render_corridor_list,
    render_numbered_products,
    render_numbered_stores,
)
from rappi.cli.session import SessionState
from rappi.client import RappiClient, RappiAPIError, TokenExpiredError
from rappi.memory import MemoryManager
from rappi.models.store import Product, Topping
from rappi.services.address import list_addresses, set_active_address
from rappi.services.auth import get_profile, is_prime
from rappi.services.cart import add_to_cart, get_carts, recalculate_cart
from rappi.services.checkout import get_checkout_detail, place_order, set_tip
from rappi.services.order import get_orders
from rappi.services.search import search
from rappi.services.store import (
    get_product_toppings,
    get_restaurant_catalog,
    get_store_detail,
    search_store_products,
)
from rappi.utils.pricing import format_cop, strip_html


class InteractiveSession:
    """Guided interactive ordering flow."""

    def __init__(self) -> None:
        self.state = SessionState()
        self.con = Console()

    async def __aenter__(self) -> InteractiveSession:
        self._memory_ctx = MemoryManager()
        self._memory = await self._memory_ctx.__aenter__()
        self._client_ctx = RappiClient(memory=self._memory)
        self.client = await self._client_ctx.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client_ctx.__aexit__(*exc)
        await self._memory_ctx.__aexit__(*exc)

    async def run(self) -> None:
        """Main interactive flow."""
        try:
            await self.step_welcome()
            await self.step_address()

            # Find and pick a store
            await self.step_find_store()

            # If reorder already added items, skip to post-add
            skip_first_browse = self.state.cart_item_count > 0

            # Menu loop: browse, add items, repeat
            while True:
                if skip_first_browse:
                    skip_first_browse = False
                else:
                    await self.step_browse_menu()
                action = await self.step_post_add()
                if action == "checkout":
                    break
                elif action == "new_store":
                    await self.step_find_store()
                # "continue" stays in the loop with same store

            await self.step_checkout()
            await self.step_track()

        except TokenExpiredError:
            self.con.print("\n[red]Token expired.[/red] Run: [bold]rappi auth login[/bold]")
        except KeyboardInterrupt:
            self.con.print("\n[dim]Goodbye![/dim]")
        except RappiAPIError as e:
            self.con.print(f"\n[red]API Error:[/red] {e}")

    # --- Steps ---

    async def step_welcome(self) -> None:
        """Fetch profile, show greeting with memory context."""
        profile = await get_profile(self.client)
        prime = await is_prime(self.client)
        prime_badge = " | [green]Prime[/green]" if prime.is_prime else ""

        # Memory context
        memory_line = ""
        try:
            summary = await self._memory.get_memory_summary()
            if summary.get("last_order"):
                lo = summary["last_order"]
                memory_line = f"\nLast order: [dim]{lo['store']} — {format_cop(lo['total'])}[/dim]"
            if summary.get("order_count", 0) > 0:
                memory_line += f"\n[dim]{summary['order_count']} orders in history[/dim]"
        except Exception:
            pass

        self.con.print()
        self.con.print(Panel(
            f"[bold]Welcome, {profile.first_name or profile.name}![/bold]{prime_badge}{memory_line}",
            title="Rappi CLI",
            style="cyan",
            expand=False,
        ))

    async def step_address(self) -> None:
        """Show addresses, let user switch if needed."""
        addresses = await list_addresses(self.client)
        if not addresses:
            self.con.print("[yellow]No saved addresses found. Using default location.[/yellow]")
            return

        active = next((a for a in addresses if a.active), addresses[0])
        self.state.active_address = active

        self.con.print(f"Delivering to: [bold]{active.title or active.tag or 'Address'}[/bold] — {active.address or '—'}")

        if len(addresses) > 1:
            if Confirm.ask("Switch address?", default=False):
                self.con.print()
                for i, addr in enumerate(addresses, 1):
                    marker = " [green](active)[/green]" if addr.active else ""
                    self.con.print(f"  [bold cyan]{i}.[/bold cyan] {addr.title or addr.tag or 'Address'} — {addr.address or '—'}{marker}")
                self.con.print()
                choice = IntPrompt.ask("Deliver to", choices=[str(i) for i in range(1, len(addresses) + 1)])
                picked = addresses[choice - 1]
                if picked.id != active.id:
                    await set_active_address(self.client, picked.id)
                    self.state.active_address = picked
                    self.con.print(f"[green]Switched to {picked.title or picked.address}[/green]")
        self.con.print()

    async def step_find_store(self) -> None:
        """Search or browse, then pick a store."""
        self.con.print("[bold]What are you looking for?[/bold]")
        self.con.print("  [bold cyan]1.[/bold cyan] Search (restaurants, stores, products)")
        self.con.print("  [bold cyan]2.[/bold cyan] Browse nearby restaurants")

        # Show extra options if memory has data
        has_history = False
        has_favorites = False
        try:
            order_count = await self._memory.orders.count()
            fav_ids = await self._memory.preferences.get_favorite_store_ids()
            has_history = order_count > 0
            has_favorites = len(fav_ids) > 0
        except Exception:
            pass

        choices = ["1", "2"]
        if has_history:
            self.con.print("  [bold cyan]3.[/bold cyan] Reorder from history")
            choices.append("3")
        if has_favorites:
            self.con.print("  [bold cyan]4.[/bold cyan] Pick a favorite")
            choices.append("4")

        self.con.print()
        mode = Prompt.ask("Choice", choices=choices, default="1")

        if mode == "1":
            stores = await self._search_flow()
        elif mode == "2":
            stores = await self._browse_flow()
        elif mode == "3":
            return await self._reorder_flow()
        elif mode == "4":
            return await self._favorites_flow()
        else:
            stores = []

        if not stores:
            self.con.print("[yellow]Nothing found. Try a different search.[/yellow]")
            return await self.step_find_store()

        await self.step_pick_store(stores)

    async def _reorder_flow(self) -> None:
        """Show past orders and let user pick one to reorder."""
        orders = await self._memory.orders.list_recent(limit=10)
        if not orders:
            self.con.print("[yellow]No order history.[/yellow]")
            return await self.step_find_store()

        self.con.print("\n[bold]Recent Orders[/bold]")
        for i, o in enumerate(orders, 1):
            items_str = ""
            if o.items:
                names = [it["name"] for it in o.items[:3]]
                items_str = f" — {', '.join(names)}"
            date = o.placed_at[:10] if o.placed_at else "?"
            self.con.print(
                f"  [bold cyan]{i}.[/bold cyan] {o.store_name}{items_str}  "
                f"[dim]{format_cop(o.total)} | {date}[/dim]"
            )

        self.con.print()
        choice = IntPrompt.ask(
            f"Pick an order to reorder [1-{len(orders)}]",
            choices=[str(i) for i in range(1, len(orders) + 1)],
        )
        picked = orders[choice - 1]

        # Load the store and re-add items
        self.con.print(f"[dim]Loading {picked.store_name}...[/dim]")
        store_detail = await get_store_detail(self.client, picked.store_id)
        self.state.current_store = store_detail

        added = []
        failed = []
        for item in (picked.items or []):
            from rappi.mcp.server import _find_product
            product = _find_product(store_detail, int(item["product_id"]))
            if product and product.in_stock:
                try:
                    carts = await add_to_cart(
                        self.client, store_detail.store_id, product, [],
                        item.get("quantity", 1),
                        store_type=store_detail.effective_store_type,
                    )
                    self.state.carts = carts
                    added.append(f"{item.get('quantity', 1)}x {item['name']}")
                except Exception:
                    failed.append(item["name"])
            else:
                failed.append(f"{item['name']} (unavailable)")

        if added:
            self.con.print(f"\n[green]Added:[/green] {', '.join(added)}")
        if failed:
            self.con.print(f"[yellow]Couldn't add:[/yellow] {', '.join(failed)}")
        render_cart_summary_bar(self.con, self.state.cart_item_count, self.state.cart_total)

    async def _favorites_flow(self) -> None:
        """Let user pick a favorite store."""
        fav_ids = await self._memory.preferences.get_favorite_store_ids()
        if not fav_ids:
            self.con.print("[yellow]No favorites saved.[/yellow]")
            return await self.step_find_store()

        self.con.print("\n[bold]Favorite Stores[/bold]")
        stores_info = []
        for i, sid in enumerate(fav_ids, 1):
            cached = await self._memory.stores.get(sid, ttl_hours=99999)
            name = cached["name"] if cached else str(sid)
            stores_info.append((sid, name))
            self.con.print(f"  [bold cyan]{i}.[/bold cyan] {name}")

        self.con.print()
        choice = IntPrompt.ask(
            f"Pick a store [1-{len(stores_info)}]",
            choices=[str(i) for i in range(1, len(stores_info) + 1)],
        )
        picked_id, _ = stores_info[choice - 1]

        self.con.print(f"[dim]Loading store...[/dim]")
        store_detail = await get_store_detail(self.client, picked_id)
        self.state.current_store = store_detail

        status = store_detail.status.status if store_detail.status else "unknown"
        status_color = "green" if status == "open" else "red"
        self.con.print(Panel(
            f"[bold]{store_detail.name}[/bold]\nStatus: [{status_color}]{status}[/{status_color}]",
            expand=False,
        ))

    async def _search_flow(self) -> list:
        """Prompt for query, search, return stores."""
        # Show recent search suggestions
        try:
            popular = await self._memory.search.get_popular_queries(limit=5)
            if popular:
                suggestions = [q["query"] for q in popular]
                self.con.print(f"[dim]Recent: {', '.join(suggestions)}[/dim]")
        except Exception:
            pass

        query = Prompt.ask("\n[bold]Search[/bold]")
        self.con.print(f"[dim]Searching for '{query}'...[/dim]")
        stores = await search(self.client, query)
        self.state.last_search_stores = stores

        if not stores:
            return []

        self.con.print()
        render_numbered_stores(self.con, stores)
        return stores

    async def _browse_flow(self) -> list:
        """Browse nearby restaurants."""
        self.con.print("[dim]Loading nearby restaurants...[/dim]")
        stores = await get_restaurant_catalog(self.client, limit=15)
        self.state.last_catalog_stores = stores

        if not stores:
            return []

        self.con.print()
        render_numbered_stores(self.con, stores)
        return stores

    async def step_pick_store(self, stores: list) -> None:
        """User picks a store by number, fetch full detail."""
        n = len(stores)
        choice = IntPrompt.ask(
            f"Pick a store [1-{n}]",
            choices=[str(i) for i in range(1, n + 1)],
        )
        picked = stores[choice - 1]
        store_id = picked.store_id

        self.con.print(f"[dim]Loading store...[/dim]")
        store_detail = await get_store_detail(self.client, store_id)
        self.state.current_store = store_detail

        # Show store header
        status = store_detail.status.status if store_detail.status else "unknown"
        status_color = "green" if status == "open" else "red"
        store_type_label = store_detail.effective_store_type
        if store_type_label == "restaurant":
            time_info = f"Cooking: {store_detail.min_cooking_time or '?'}–{store_detail.max_cooking_time or '?'} min"
        else:
            time_info = f"Type: {store_type_label}"

        self.con.print(Panel(
            f"[bold]{store_detail.name}[/bold]\n"
            f"Status: [{status_color}]{status}[/{status_color}] | {time_info}",
            expand=False,
        ))

        # For non-restaurant stores with no menu, explain the search-based flow
        if not store_detail.corridors and not store_detail.is_restaurant:
            self.con.print(
                f"[dim]This is a {store_type_label} store — search for products to browse.[/dim]"
            )

    async def step_browse_menu(self) -> None:
        """Browse products — either via menu corridors or in-store search."""
        store = self.state.current_store
        if not store:
            return

        if store.corridors:
            # Restaurant-style: pick category -> pick product
            await self._browse_corridors(store.corridors)
        else:
            # Store-style (Turbo, markets): search for products
            await self._search_in_store()

    async def _browse_corridors(self, corridors) -> None:
        """Browse menu categories and pick a product."""
        store = self.state.current_store

        self.con.print()
        render_corridor_list(self.con, corridors)
        self.con.print()
        n = len(corridors)
        cat_choice = IntPrompt.ask(
            f"Pick a category [1-{n}]",
            choices=[str(i) for i in range(1, n + 1)],
        )
        corridor = corridors[cat_choice - 1]

        # Pick product
        self.con.print(f"\n[bold]{corridor.name}[/bold]")
        render_numbered_products(self.con, corridor.products)
        self.con.print()
        np = len(corridor.products)
        prod_choice = IntPrompt.ask(
            f"Pick a product [1-{np}]",
            choices=[str(i) for i in range(1, np + 1)],
        )
        product = corridor.products[prod_choice - 1]

        if not product.in_stock:
            self.con.print("[red]This product is out of stock.[/red] Pick another.")
            return await self._browse_corridors(corridor.products)

        await self._confirm_and_add(product)

    async def _search_in_store(self) -> None:
        """Search for products within the current store (for non-restaurant stores)."""
        store = self.state.current_store
        if not store:
            return

        query = Prompt.ask(f"\n[bold]Search in {store.name}[/bold]")
        self.con.print(f"[dim]Searching...[/dim]")

        corridors = await search_store_products(self.client, store.store_id, query)

        if not corridors:
            self.con.print("[yellow]No products found. Try a different search.[/yellow]")
            return await self._search_in_store()

        # Flatten all products for selection (they're already grouped by category)
        all_products: list[Product] = []
        for corridor in corridors:
            if corridor.products:
                self.con.print(f"\n[bold]{corridor.name}[/bold]")
                for p in corridor.products:
                    all_products.append(p)

        # Show numbered list across all categories
        self.con.print()
        render_numbered_products(self.con, all_products)
        self.con.print()

        np = len(all_products)
        prod_choice = IntPrompt.ask(
            f"Pick a product [1-{np}]",
            choices=[str(i) for i in range(1, np + 1)],
        )
        product = all_products[prod_choice - 1]

        if not product.in_stock:
            self.con.print("[red]This product is out of stock.[/red]")
            return await self._search_in_store()

        await self._confirm_and_add(product)

    async def _confirm_and_add(self, product: Product) -> None:
        """Show product details, handle toppings, ask quantity, add to cart."""
        store = self.state.current_store
        if not store:
            return

        self.con.print(f"\n[bold]{product.name}[/bold] — [green]{format_cop(product.price)}[/green]")
        if product.description:
            self.con.print(f"[dim]{product.description}[/dim]")

        # Handle toppings
        selected_toppings = await self._select_toppings(store.store_id, product)

        # Quantity
        qty = IntPrompt.ask("Quantity", default=1)

        # Add to cart
        store_type = store.effective_store_type
        carts = await add_to_cart(
            self.client, store.store_id, product, selected_toppings, qty,
            store_type=store_type,
        )
        self.state.carts = carts
        self.con.print(f"\n[green]Added![/green]")
        render_cart_summary_bar(self.con, self.state.cart_item_count, self.state.cart_total)

    async def _select_toppings(self, store_id: int, product: Product) -> list[Topping]:
        """Interactive topping selection. Returns list of selected Topping objects."""
        if not product.has_toppings:
            return []

        try:
            toppings_resp = await get_product_toppings(self.client, store_id, product.id)
        except RappiAPIError:
            return []

        if not toppings_resp.categories:
            return []

        selected: list[Topping] = []

        for cat in toppings_resp.categories:
            available = [t for t in cat.toppings if t.is_available]
            if not available:
                continue

            required = cat.min_toppings_for_categories > 0
            label = "[red](required)[/red]" if required else "[dim](optional)[/dim]"
            self.con.print(f"\n[bold]{cat.description or f'Category {cat.id}'}[/bold] {label}")

            for i, t in enumerate(available, 1):
                price = f" [yellow]+{format_cop(t.price)}[/yellow]" if t.price > 0 else ""
                self.con.print(f"  [bold cyan]{i}.[/bold cyan] {t.description or '—'}{price}")

            if cat.max_toppings_for_categories == 1:
                if required:
                    choice = IntPrompt.ask(
                        "Select",
                        choices=[str(i) for i in range(1, len(available) + 1)],
                    )
                    selected.append(available[choice - 1])
                else:
                    choice_str = Prompt.ask("Select (Enter to skip)", default="")
                    if choice_str.strip():
                        idx = int(choice_str) - 1
                        if 0 <= idx < len(available):
                            selected.append(available[idx])
            else:
                max_sel = cat.max_toppings_for_categories
                hint = f"up to {max_sel}" if max_sel > 0 else "any"
                choice_str = Prompt.ask(
                    f"Select ({hint}, comma-separated, Enter to skip)",
                    default="",
                )
                if choice_str.strip():
                    for part in choice_str.split(","):
                        part = part.strip()
                        if part.isdigit():
                            idx = int(part) - 1
                            if 0 <= idx < len(available):
                                selected.append(available[idx])

        return selected

    async def step_post_add(self) -> str:
        """What to do after adding an item. Returns action string."""
        store = self.state.current_store
        store_label = self.state.store_name

        self.con.print()
        self.con.print("[bold]What next?[/bold]")
        self.con.print(f"  [bold cyan]1.[/bold cyan] Add more from {store_label}")
        self.con.print("  [bold cyan]2.[/bold cyan] Search another store")
        self.con.print("  [bold cyan]3.[/bold cyan] View cart")
        self.con.print("  [bold cyan]4.[/bold cyan] Checkout")
        self.con.print(f"  [bold cyan]5.[/bold cyan] Save {store_label} to favorites")
        self.con.print()

        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            return "continue"
        elif choice == "2":
            return "new_store"
        elif choice == "3":
            await self._show_cart()
            return await self.step_post_add()
        elif choice == "5":
            if store:
                try:
                    await self._memory.preferences.add_favorite_store(store.store_id)
                    self.con.print(f"[green]Saved {store_label} to favorites![/green]")
                except Exception:
                    self.con.print("[yellow]Couldn't save favorite.[/yellow]")
            return await self.step_post_add()
        else:
            return "checkout"

    async def _show_cart(self) -> None:
        """Display current cart contents."""
        carts = await get_carts(self.client)
        self.state.carts = carts

        if not carts or all(not c.stores for c in carts):
            self.con.print("[yellow]Your cart is empty.[/yellow]")
            return

        for cart in carts:
            for store in cart.stores:
                self.con.print(f"\n[bold]{store.name or 'Store'}[/bold]")
                for p in store.products:
                    topping_str = ""
                    if p.toppings:
                        names = [t.description for t in p.toppings if t.description]
                        if names:
                            topping_str = f" [dim]({', '.join(names)})[/dim]"
                    self.con.print(f"  {p.units}x {p.name}{topping_str}  [green]{format_cop(p.total)}[/green]")
                for charge in store.charges:
                    self.con.print(f"  [dim]{charge.charge_type or 'Fee'}: {format_cop(charge.total)}[/dim]")
                self.con.print(f"  [bold]Total: {format_cop(store.total)}[/bold]")

    async def step_checkout(self) -> None:
        """Recalculate, set tip, show summary, confirm, place order."""
        store = self.state.current_store
        store_type = store.effective_store_type if store else "restaurant"

        self.con.print("\n[dim]Preparing checkout...[/dim]")
        await recalculate_cart(self.client, store_type=store_type)

        # Tip (pre-fill from saved preference)
        default_tip = "0"
        try:
            saved_tip = await self._memory.preferences.get_default_tip()
            if saved_tip:
                default_tip = str(saved_tip)
        except Exception:
            pass
        tip_str = Prompt.ask("\nTip for your driver (COP)", default=default_tip)
        tip_amount = int(tip_str) if tip_str.strip().isdigit() else 0
        if tip_amount > 0:
            await set_tip(self.client, tip_amount, store_type=store_type)

        # Get checkout detail
        detail = await get_checkout_detail(self.client, store_type=store_type)

        # Show summary (strip HTML tags from API response)
        self.con.print()
        for summary in detail.summary:
            if summary.header:
                self.con.print(f"[bold]{strip_html(summary.header.title) or 'Order'}[/bold]")
            for item in summary.details:
                key = strip_html(item.key)
                value = strip_html(item.value)
                if not key or not value:
                    continue
                if item.type == "total":
                    self.con.print(f"  [bold]{key}: {value}[/bold]")
                else:
                    self.con.print(f"  {key}: {value}")

        if tip_amount > 0:
            self.con.print(f"  [bold]Tip: {format_cop(tip_amount)}[/bold]")

        if not detail.return_key:
            self.con.print("[red]Cannot place order — no return key received.[/red]")
            return

        self.con.print()
        if not Confirm.ask("[bold]Place this order?[/bold]", default=False):
            self.con.print("[yellow]Order cancelled.[/yellow]")
            return

        self.con.print("[dim]Placing order...[/dim]")
        try:
            result = await place_order(self.client, detail.return_key, store_type=store_type)
            self.con.print(Panel("[green][bold]Order placed![/bold][/green]", style="green", expand=False))

            # Record order to memory
            try:
                carts = await get_carts(self.client)
                order_id = result.get("order_id", 0) if isinstance(result, dict) else 0
                for cart in carts:
                    await self._memory.record_order_from_cart(
                        order_id=order_id,
                        cart_stores=cart.stores,
                        tip=tip_amount,
                    )
            except Exception:
                pass

        except RappiAPIError as e:
            import json as _json
            try:
                err = _json.loads(e.detail)
                msg = err.get("error", {}).get("message", str(e))
            except (ValueError, AttributeError):
                msg = str(e)
            self.con.print(f"\n[red]Order failed:[/red] {msg}")
            self.con.print("[dim]The store may be closed or unavailable right now.[/dim]")

    async def step_track(self) -> None:
        """Offer to track the order."""
        if not Confirm.ask("Track your order?", default=True):
            return

        self.con.print("[dim]Tracking... (Ctrl+C to stop)[/dim]\n")
        try:
            while True:
                result = await get_orders(self.client)
                if not result.active_orders:
                    self.con.print("[green]No active orders — your order may have been delivered![/green]")
                    break

                for order in result.active_orders:
                    state_icons = {"created": "[ ]", "in_store": "[*]", "on_the_way": "[>>]", "delivered": "[ok]"}
                    icon = state_icons.get(order.state or "", "[?]")
                    store_name = order.store.name if order.store else "—"
                    eta = f"ETA: {order.eta} min" if order.eta else ""
                    state_colors = {"created": "yellow", "in_store": "cyan", "on_the_way": "blue", "delivered": "green"}
                    color = state_colors.get(order.state or "", "white")
                    self.con.print(
                        f"  {icon} #{order.id} {store_name} — "
                        f"[{color}]{order.state}[/{color}] {eta}  "
                        f"Total: {format_cop(order.total)}"
                    )
                    if order.state == "delivered":
                        self.con.print("\n[green]Your order has been delivered![/green]")
                        return

                await asyncio.sleep(10)
                self.con.print("[dim]Refreshing...[/dim]")

        except KeyboardInterrupt:
            self.con.print("\n[dim]Stopped tracking.[/dim]")


def launch_interactive() -> None:
    """Entry point for the interactive session."""
    async def _run():
        async with InteractiveSession() as session:
            await session.run()
    asyncio.run(_run())

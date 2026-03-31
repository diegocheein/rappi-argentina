"""CLI commands for managing favorites."""

import asyncio

import typer
from rich.console import Console

from rappi.memory import MemoryManager

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def list_cmd() -> None:
    """List favorite stores."""

    async def _run():
        async with MemoryManager() as memory:
            store_ids = await memory.preferences.get_favorite_store_ids()
            stores = []
            for sid in store_ids:
                cached = await memory.stores.get(sid, ttl_hours=99999)
                stores.append({"id": sid, "name": cached["name"] if cached else str(sid)})
            return stores

    stores = asyncio.run(_run())

    if not stores:
        console.print("[yellow]No favorites yet.[/yellow] Add one with [bold]rappi favorites add <store_id>[/bold].")
        return

    console.print("[bold]Favorite Stores:[/bold]")
    for s in stores:
        console.print(f"  {s['id']} — {s['name']}")


@app.command("add")
def add_cmd(store_id: int = typer.Argument(..., help="Store ID to favorite")) -> None:
    """Add a store to favorites."""

    async def _run():
        async with MemoryManager() as memory:
            await memory.preferences.add_favorite_store(store_id)

    asyncio.run(_run())
    console.print(f"[green]Store {store_id} added to favorites.[/green]")


@app.command("remove")
def remove_cmd(store_id: int = typer.Argument(..., help="Store ID to remove")) -> None:
    """Remove a store from favorites."""

    async def _run():
        async with MemoryManager() as memory:
            await memory.preferences.remove_favorite_store(store_id)

    asyncio.run(_run())
    console.print(f"[green]Store {store_id} removed from favorites.[/green]")

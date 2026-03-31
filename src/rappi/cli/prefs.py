"""CLI commands for user preferences."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from rappi.memory import MemoryManager
from rappi.utils.pricing import format_cop

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def show_cmd() -> None:
    """Show all preferences."""

    async def _run():
        async with MemoryManager() as memory:
            return await memory.preferences.get_all()

    prefs = asyncio.run(_run())

    if not prefs:
        console.print("[yellow]No preferences set.[/yellow]")
        console.print("Set them with: [bold]rappi prefs set tip 5000[/bold]")
        return

    table = Table(title="Preferences", show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    display_map = {
        "default_tip": lambda v: format_cop(v),
        "dietary_restrictions": lambda v: ", ".join(v) if v else "—",
        "allergies": lambda v: ", ".join(v) if v else "—",
        "favorite_store_ids": lambda v: ", ".join(str(i) for i in v) if v else "—",
    }

    for key, value in prefs.items():
        formatter = display_map.get(key, str)
        table.add_row(key, formatter(value))

    console.print(table)


@app.command("set")
def set_cmd(
    key: str = typer.Argument(..., help="Preference key (tip, diet, allergy)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a preference. Keys: tip, diet, allergy."""

    async def _run():
        async with MemoryManager() as memory:
            if key == "tip":
                await memory.preferences.set_default_tip(int(value))
            elif key == "diet":
                items = [v.strip() for v in value.split(",")]
                await memory.preferences.set_dietary_restrictions(items)
            elif key == "allergy":
                items = [v.strip() for v in value.split(",")]
                await memory.preferences.set_allergies(items)
            else:
                await memory.preferences.set(key, value)

    asyncio.run(_run())
    console.print(f"[green]Preference '{key}' set to: {value}[/green]")


@app.command("clear")
def clear_cmd(key: str = typer.Argument(..., help="Preference key to clear")) -> None:
    """Clear a preference."""

    async def _run():
        async with MemoryManager() as memory:
            await memory.preferences.delete(key)

    asyncio.run(_run())
    console.print(f"[green]Preference '{key}' cleared.[/green]")

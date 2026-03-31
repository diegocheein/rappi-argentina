"""CLI commands for address management."""

import asyncio

import typer
from rich.console import Console

from rappi.cli.formatters import render_addresses
from rappi.client import RappiClient
from rappi.services.address import list_addresses, reverse_geocode, set_active_address

app = typer.Typer()
console = Console()


@app.command("list")
def list_cmd() -> None:
    """List all saved delivery addresses."""

    async def _run():
        async with RappiClient() as client:
            return await list_addresses(client)

    addresses = asyncio.run(_run())
    if not addresses:
        console.print("[yellow]No addresses found.[/yellow]")
        return
    console.print(render_addresses(addresses))


@app.command("set")
def set_cmd(address_id: int = typer.Argument(..., help="Address ID to set as active")) -> None:
    """Set a delivery address as active."""

    async def _run():
        async with RappiClient() as client:
            await set_active_address(client, address_id)

    asyncio.run(_run())
    console.print(f"[green]Address {address_id} set as active.[/green]")


@app.command()
def geocode(
    lat: float = typer.Argument(..., help="Latitude"),
    lng: float = typer.Argument(..., help="Longitude"),
) -> None:
    """Get a human-readable address from coordinates."""

    async def _run():
        async with RappiClient() as client:
            return await reverse_geocode(client, lat, lng)

    geo = asyncio.run(_run())
    console.print(f"[bold]{geo.full_text_to_show or geo.full_text or geo.original_text}[/bold]")

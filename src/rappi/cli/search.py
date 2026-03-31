"""CLI commands for searching products and stores."""

import asyncio

import typer
from rich.console import Console

from rappi.cli.formatters import render_search_results
from rappi.client import RappiClient
from rappi.services.search import search

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def search_cmd(
    query: str = typer.Argument(..., help="Search term (e.g. 'hamburguesa')"),
) -> None:
    """Search for products and stores."""

    async def _run():
        async with RappiClient() as client:
            return await search(client, query)

    stores = asyncio.run(_run())
    render_search_results(stores)

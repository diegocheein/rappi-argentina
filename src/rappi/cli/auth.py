"""CLI commands for authentication."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table

from rappi.client import RappiClient, TokenExpiredError
from rappi.config import ConfigManager
from rappi.services.auth import get_profile, is_prime, set_token

app = typer.Typer()
console = Console()


@app.command()
def login(
    token: str | None = typer.Option(None, "--token", "-t", help="Manual Bearer token (skips browser login)"),
    device_id: str | None = typer.Option(None, "--device-id", "-d", help="Device ID (UUID). Auto-generated if omitted."),
    country: str = typer.Option("co", "--country", "-c", help="Country code: co (Colombia), mx (Mexico)"),
    headless: bool = typer.Option(False, "--headless", help="Run browser in headless mode"),
) -> None:
    """Log in to Rappi. Opens a browser for you to sign in (or pass --token for manual auth)."""
    import os
    os.environ["RAPPI_COUNTRY"] = country
    # Re-import to pick up the new country
    import importlib
    import rappi.constants
    importlib.reload(rappi.constants)

    config_manager = ConfigManager()
    config_manager.update(country=country)

    if token:
        # Manual token flow
        if not token.startswith("ft."):
            console.print("[yellow]Warning:[/yellow] Token doesn't start with 'ft.' — this may not work.")
        set_token(config_manager, token, device_id)
    else:
        # Browser login flow
        from rappi.services.browser_auth import login_with_browser

        def on_status(msg: str) -> None:
            console.print(f"  [dim]{msg}[/dim]")

        from rappi.constants import RAPPI_DOMAIN
        console.print(Panel(
            "[bold]Browser Login[/bold]\n\n"
            f"A browser window will open to [cyan]{RAPPI_DOMAIN}/login[/cyan]\n"
            "Log in with your phone number and OTP.\n"
            "The token will be captured automatically.\n\n"
            "[dim]Timeout: 5 minutes[/dim]",
            title="Rappi Auth",
        ))

        try:
            creds = asyncio.run(login_with_browser(headless=headless, on_status=on_status))
        except TimeoutError:
            console.print("[red]Login timed out. Please try again.[/red]")
            raise typer.Exit(1)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            console.print("\nTo install browser support: [bold]uv run playwright install chromium[/bold]")
            console.print("Or use manual token: [bold]rappi auth login --token <your-token>[/bold]")
            raise typer.Exit(1)

        set_token(config_manager, creds.token, creds.device_id)

    # Verify the token works
    async def _verify():
        async with RappiClient(config_manager=config_manager) as client:
            return await get_profile(client)

    try:
        profile = asyncio.run(_verify())
        console.print(Panel(
            f"[green]Logged in as [bold]{profile.name}[/bold][/green]\n"
            f"Email: {profile.email}\n"
            f"Phone: {profile.country_code} {profile.phone}",
            title="Authentication Successful",
        ))
    except TokenExpiredError:
        console.print("[red]Token appears to be invalid or expired.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[yellow]Token saved but verification failed:[/yellow] {e}")
        console.print("The token may still work — try [bold]rappi auth status[/bold].")


@app.command()
def status() -> None:
    """Check your authentication status and show profile info."""
    config_manager = ConfigManager()
    config = config_manager.load()

    if not config.token:
        console.print("[red]Not authenticated.[/red] Run: [bold]rappi auth login[/bold]")
        raise typer.Exit(1)

    async def _fetch():
        async with RappiClient(config=config) as client:
            profile = await get_profile(client)
            prime = await is_prime(client)
            return profile, prime

    try:
        profile, prime = asyncio.run(_fetch())
    except TokenExpiredError:
        console.print("[red]Token expired.[/red] Run: [bold]rappi auth login[/bold]")
        raise typer.Exit(1)

    table = Table(title="Rappi Profile", show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Name", profile.name or "—")
    table.add_row("Email", profile.email or "—")
    table.add_row("Phone", f"{profile.country_code or ''} {profile.phone or '—'}")
    table.add_row("ID", str(profile.id))
    table.add_row("VIP", "Yes" if profile.vip else "No")
    if profile.loyalty:
        table.add_row("Loyalty", f"{profile.loyalty.name} ({profile.loyalty.type})")
    table.add_row("Prime", "[green]Yes[/green]" if prime.is_prime else "No")

    console.print(table)


@app.command()
def logout() -> None:
    """Clear saved authentication token."""
    config_manager = ConfigManager()
    config_manager.update(token=None)
    console.print("[green]Token cleared.[/green]")

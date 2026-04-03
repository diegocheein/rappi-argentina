"""Build the Cowork plugin zip with a custom MCP server URL."""

import json
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _find_project_root() -> Path:
    """Find the project root by looking for .claude-plugin/plugin.json."""
    # Try relative to this file first
    if (PROJECT_ROOT / ".claude-plugin" / "plugin.json").exists():
        return PROJECT_ROOT
    # Fall back to cwd
    cwd = Path.cwd()
    if (cwd / ".claude-plugin" / "plugin.json").exists():
        return cwd
    raise typer.BadParameter("Could not find project root (no .claude-plugin/plugin.json found)")


@app.command()
def build(
    url: str = typer.Option(..., "--url", help="Your MCP server SSE URL (e.g., https://your-app.up.railway.app/sse)"),
    output: str = typer.Option(
        str(Path.home() / "Desktop" / "rappi-cowork-plugin.zip"),
        "--output", "-o",
        help="Output path for the zip file",
    ),
) -> None:
    """Build a Cowork plugin zip with your MCP server URL."""
    root = _find_project_root()
    output_path = Path(output)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy plugin manifest
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        shutil.copy2(root / ".claude-plugin" / "plugin.json", plugin_dir / "plugin.json")

        # Copy skills
        skills_src = root / "skills"
        if skills_src.exists():
            shutil.copytree(skills_src, tmp_path / "skills")

        # Copy agents
        agents_src = root / "agents"
        if agents_src.exists():
            shutil.copytree(agents_src, tmp_path / "agents")

        # Generate .mcp.json with the user's URL
        mcp_config = {
            "mcpServers": {
                "rappi": {
                    "type": "http",
                    "url": url,
                }
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config, indent=2) + "\n")

        # Create zip
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w") as zf:
            for file in sorted(tmp_path.rglob("*")):
                if file.is_file():
                    arcname = file.relative_to(tmp_path)
                    zf.write(file, arcname)

    console.print(f"\n[green]Plugin zip created:[/green] {output_path}")
    console.print(f"[dim]MCP URL:[/dim] {url}")
    console.print(f"\n[bold]Next steps:[/bold]")
    console.print("1. Upload the zip to Cowork > Customize > Plugins")
    console.print(f"2. Add remote MCP connector with URL: {url}")
    console.print("3. Start a conversation and try: \"Search for pizza on Rappi\"")

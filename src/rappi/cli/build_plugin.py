"""Build plugin bundles for Claude Cowork and OpenClaw."""

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

TARGETS = ("claude", "openclaw")


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


def _build_bundle(root: Path, tmp_path: Path, *, target: str, url: str | None) -> None:
    """Assemble a plugin bundle in tmp_path."""
    # Copy plugin manifest
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    shutil.copy2(root / ".claude-plugin" / "plugin.json", plugin_dir / "plugin.json")

    # Copy skills
    skills_src = root / "skills"
    if skills_src.exists():
        shutil.copytree(skills_src, tmp_path / "skills")

    # Copy agents (Claude uses them; OpenClaw ignores but no harm including)
    agents_src = root / "agents"
    if agents_src.exists():
        shutil.copytree(agents_src, tmp_path / "agents")

    if url:
        # Remote MCP — HTTP/SSE transport
        mcp_config = {
            "mcpServers": {
                "rappi": {
                    "type": "http",
                    "url": url,
                }
            }
        }
    else:
        # Local MCP — stdio transport (same as repo .mcp.json)
        mcp_config = {
            "mcpServers": {
                "rappi": {
                    "command": "uv",
                    "args": ["run", "--project", ".", "rappi-mcp"],
                }
            }
        }

    (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config, indent=2) + "\n")


@app.command()
def build(
    url: str = typer.Option(
        None, "--url",
        help="MCP server SSE URL (e.g., https://your-app.up.railway.app/sse). Omit for local stdio.",
    ),
    target: str = typer.Option(
        "claude", "--target", "-t",
        help=f"Target platform: {', '.join(TARGETS)}",
    ),
    output: str = typer.Option(
        None, "--output", "-o",
        help="Output path for the zip file (default: ~/Desktop/rappi-{target}-plugin.zip)",
    ),
) -> None:
    """Build a plugin bundle for Claude Cowork or OpenClaw."""
    if target not in TARGETS:
        raise typer.BadParameter(f"Unknown target '{target}'. Choose from: {', '.join(TARGETS)}")

    root = _find_project_root()

    # Default output path based on target
    if output is None:
        output = str(Path.home() / "Desktop" / f"rappi-{target}-plugin.zip")
    output_path = Path(output)

    # Claude Cowork requires a remote URL
    if target == "claude" and url is None:
        raise typer.BadParameter(
            "Claude Cowork requires --url (your Railway SSE endpoint). "
            "Example: --url https://your-app.up.railway.app/sse"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _build_bundle(root, tmp_path, target=target, url=url)

        # Create zip
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w") as zf:
            for file in sorted(tmp_path.rglob("*")):
                if file.is_file():
                    arcname = file.relative_to(tmp_path)
                    zf.write(file, arcname)

    console.print(f"\n[green]Plugin zip created:[/green] {output_path}")
    if url:
        console.print(f"[dim]MCP transport:[/dim] HTTP (SSE) → {url}")
    else:
        console.print(f"[dim]MCP transport:[/dim] stdio (local)")

    console.print(f"\n[bold]Next steps ({target}):[/bold]")
    if target == "claude":
        console.print("1. Upload the zip to Cowork > Customize > Plugins")
        console.print(f"2. Add remote MCP connector with URL: {url}")
        console.print("3. Start a conversation and try: \"Search for pizza on Rappi\"")
    else:
        if url:
            console.print(f"1. openclaw plugins install {output_path}")
        else:
            console.print(f"1. openclaw plugins install {root}")
            console.print(f"   (or from zip: openclaw plugins install {output_path})")
        console.print("2. openclaw gateway restart")
        console.print("3. Start a conversation and try: \"Search for pizza on Rappi\"")

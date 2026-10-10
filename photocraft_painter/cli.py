"""Interactive CLI and REPL for PhotoCraft Painter."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from photocraft_painter import __version__
from photocraft_painter.artist import execute_live_drawing
from photocraft_painter.composer import plan_artwork
from photocraft_painter.config import PainterConfig
from photocraft_painter.desktop import is_desktop_running, launch_desktop
from photocraft_painter.mcp_client import PhotocraftMcpClient, connect_mcp_bridge

console = Console()


def print_banner(config: PainterConfig) -> None:
    """Print welcoming banner and configuration summary."""
    if config.provider == "ollama":
        engine_name = f"Ollama ({config.ollama_model})"
        engine_target = config.ollama_host
    else:
        engine_name = f"OpenAI ({config.openai_model})"
        engine_target = config.openai_base_url or "api.openai.com"

    text = (
        f"[bold cyan]PhotoCraft Painter[/] [dim]v{__version__}[/]\n"
        f"[dim]Bridge Target:[/]  [green]127.0.0.1:{config.control_port}[/]\n"
        f"[dim]AI Composer:[/]    [yellow]{engine_name}[/] [dim]at[/] [cyan]{engine_target}[/]\n"
        f"[dim]Detail Level:[/]   [bold yellow]{config.detail_level}/25[/] [dim](~{config.detail_level * 10} brushstrokes across all layers)[/]\n"
        f"[dim]Drawing Speed:[/]  [magenta]{config.step_delay}s per step[/]"
    )
    console.print(Panel(text, title="🎨 PhotoCraft Live MCP Painter", border_style="cyan"))


async def draw_prompt(
    client: PhotocraftMcpClient,
    prompt_text: str,
    config: PainterConfig,
) -> None:
    """Compose and animate drawing of a prompt."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Composing illustration plan for:[/] {task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description=f"'{prompt_text}'", total=None)
        plan, source = plan_artwork(prompt_text, config, config.default_width, config.default_height)

    title = plan.get("title", prompt_text)
    steps = plan.get("steps", [])
    console.print(f"[bold green]✓[/] Composed [bold]{title}[/] ({len(steps)} steps via [cyan]{source}[/])")
    console.print(f"[dim]Watching canvas update live in PhotoCraft...[/]")

    def on_progress(idx: int, total: int, name: str, step: dict[str, Any]) -> None:
        params = step.get("params", {})
        kind = params.get("kind", "")
        fill = params.get("fill") or "outline"
        desc = f"{kind} {fill}".strip()
        console.print(
            f"  [cyan]({idx:02d}/{total:02d})[/] [bold]{name}[/] "
            f"[dim]({desc})[/]"
        )

    def on_error(idx: int, total: int, name: str, err_msg: str) -> None:
        console.print(
            f"  [yellow]({idx:02d}/{total:02d}) ⚠ Skipped minor step '{name}':[/] [dim]{err_msg}[/]"
        )

    summary = await execute_live_drawing(
        client,
        plan,
        config,
        on_step_progress=on_progress,
        on_step_error=on_error,
    )
    console.print(
        f"[bold green]✨ Artwork complete on your PhotoCraft screen![/] "
        f"[dim]({summary['steps_drawn']}/{summary['total_steps']} steps rendered)[/]\n"
    )


async def run_repl(client: PhotocraftMcpClient, config: PainterConfig) -> None:
    """Run interactive REPL loop."""
    print_banner(config)
    console.print(
        "[bold]Type any prompt to draw live on screen.[/] Commands: [cyan]/detail <1-25>[/], [cyan]/export <file>[/], [cyan]/speed <sec>[/], [cyan]/quit[/]\n"
    )

    while True:
        try:
            user_input = Prompt.ask("[bold magenta]🎨 Prompt[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting PhotoCraft Painter.[/]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "exit", "quit"):
            console.print("[dim]Goodbye![/]")
            break

        if user_input.startswith("/detail"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    lvl = int(parts[1])
                    if 1 <= lvl <= 25:
                        config.detail_level = lvl
                        console.print(f"[bold green]✓[/] Detail level set to {config.detail_level}/25 (~{config.detail_level * 10} brushstrokes)\n")
                    else:
                        console.print("[red]Detail level must be between 1 and 25[/]\n")
                except ValueError:
                    console.print("[red]Invalid detail level (expected integer 1-25)[/]\n")
            else:
                console.print(f"[cyan]Current detail level:[/] {config.detail_level}/25 (~{config.detail_level * 10} brushstrokes)\n")
            continue

        if user_input.startswith("/export"):
            parts = user_input.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else "output.png"
            try:
                await client.doc_export(target)
                console.print(f"[bold green]✓[/] Exported active document to [cyan]{target}[/]\n")
            except Exception as e:
                console.print(f"[bold red]✗ Export failed:[/] {e}\n")
            continue

        if user_input.startswith("/speed"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    config.step_delay = max(0.0, float(parts[1]))
                    console.print(f"[bold green]✓[/] Live animation delay set to {config.step_delay}s\n")
                except ValueError:
                    console.print("[red]Invalid speed number (expected float in seconds)[/]\n")
            continue

        if user_input == "/help":
            console.print(
                "[bold cyan]Available Commands:[/]\n"
                "  <any text>        Compose and draw illustration live in PhotoCraft\n"
                "  /detail <1-25>    Adjust drawing detail level 1 to 25 (~10 to ~250 brushstrokes)\n"
                "  /export <path>    Export active document as PNG/PSD/etc.\n"
                "  /speed <sec>      Set live step delay (e.g. 0.05 for fast, 0.2 for slower)\n"
                "  /quit             Exit the program\n"
            )
            continue

        try:
            await draw_prompt(client, user_input, config)
        except Exception as e:
            console.print(f"[bold red]✗ Error during drawing:[/] {e}\n")


async def async_main(args: argparse.Namespace) -> None:
    """Entry point connecting to desktop and executing prompt or REPL."""
    config = PainterConfig(
        control_port=args.port,
        step_delay=args.delay,
        detail_level=args.detail,
        provider=args.provider or os.getenv("PAINTER_PROVIDER") or "ollama",
        ollama_host=args.ollama_host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434",
        ollama_model=args.model or os.getenv("OLLAMA_MODEL") or "ornith-1.5:35b",
        openai_api_key=args.api_key or os.getenv("OPENAI_API_KEY"),
        openai_base_url=args.base_url or os.getenv("OPENAI_BASE_URL"),
        openai_model=args.openai_model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
    )

    # Check if PhotoCraft desktop is running
    if not is_desktop_running(config.control_host, config.control_port):
        console.print(
            f"[yellow]PhotoCraft desktop is not currently running on {config.control_host}:{config.control_port}.[/]"
        )
        should_launch = args.launch
        if not should_launch and sys.stdin.isatty():
            should_launch = Confirm.ask("Would you like to launch PhotoCraft desktop now?", default=True)

        if should_launch:
            console.print("[dim]Launching PhotoCraft desktop...[/]")
            try:
                launch_desktop(config)
                console.print("[bold green]✓[/] PhotoCraft desktop started and connected!")
            except Exception as e:
                console.print(f"[bold red]Failed to launch PhotoCraft:[/] {e}")
                console.print(
                    "\nYou can start it manually in another terminal with:\n"
                    f"  [cyan]photocraft --control {config.control_port} "
                    f"--control-token-file {config.control_token_file}[/]\n"
                )
                return
        else:
            console.print(
                "\nPlease start PhotoCraft in another terminal with:\n"
                f"  [cyan]photocraft --control {config.control_port} "
                f"--control-token-file {config.control_token_file}[/]\n"
            )
            return

    # Connect to MCP bridge
    try:
        async with connect_mcp_bridge(config) as client:
            if args.prompt:
                print_banner(config)
                await draw_prompt(client, args.prompt, config)
            else:
                await run_repl(client, config)
    except Exception as e:
        console.print(f"[bold red]MCP bridge error:[/] {e}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="PhotoCraft Live MCP Painter - Prompt-driven drawing via bridge mode"
    )
    parser.add_argument("prompt", nargs="?", help="Direct prompt to draw immediately")
    parser.add_argument("--port", type=int, default=7878, help="PhotoCraft control port (default: 7878)")
    parser.add_argument("--delay", type=float, default=0.12, help="Animation delay between steps in seconds (default: 0.12)")
    parser.add_argument(
        "--detail",
        "-d",
        type=int,
        default=5,
        choices=range(1, 26),
        metavar="1-25",
        help="Drawing detail level 1 (minimal) to 25 (ultra ~250 brushstrokes, default: 5)",
    )
    parser.add_argument("--launch", action="store_true", help="Automatically launch PhotoCraft if not already running")
    parser.add_argument("--provider", type=str, choices=["ollama", "openai"], default="ollama", help="AI provider (default: ollama)")
    parser.add_argument("--model", type=str, default="ornith-1.5:35b", help="Ollama model name (default: ornith-1.5:35b)")
    parser.add_argument("--ollama-host", type=str, default="http://127.0.0.1:11434", help="Ollama host URL (default: http://127.0.0.1:11434)")
    parser.add_argument("--api-key", type=str, help="OpenAI API key (if using --provider openai)")
    parser.add_argument("--base-url", type=str, help="OpenAI base URL (if using --provider openai)")
    parser.add_argument("--openai-model", type=str, default="gpt-4o-mini", help="OpenAI model name")

    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")


if __name__ == "__main__":
    main()

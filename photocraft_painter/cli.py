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
from photocraft_painter.composer import (
    parse_prompt_and_images,
    plan_artwork,
    plan_refinement_artwork,
    validate_image_files,
)
from photocraft_painter.config import PainterConfig
from photocraft_painter.desktop import is_desktop_running, launch_desktop
from photocraft_painter.mcp_client import PhotocraftMcpClient, connect_mcp_bridge
from photocraft_painter.models import (
    build_models_table,
    get_all_model_choices,
    resolve_model_selection,
)
from photocraft_painter.styles import STYLE_PRESETS, get_style

console = Console()


def print_banner(config: PainterConfig) -> None:
    """Print welcoming banner and configuration summary."""
    if config.provider == "ollama":
        engine_name = f"Ollama ({config.ollama_model})"
        engine_target = config.ollama_host
    else:
        engine_name = f"OpenAI ({config.openai_model})"
        engine_target = config.openai_base_url or "api.openai.com"

    style_preset = get_style(config.style)
    loop_val = getattr(config, "loop", 1)
    loop_desc = "single pass (no resubmission)" if loop_val == 1 else f"{loop_val - 1} critique & refinement {'pass' if loop_val - 1 == 1 else 'passes'}"

    text = (
        f"[bold cyan]PhotoCraft Painter[/] [dim]v{__version__}[/]\n"
        f"[dim]Artistic Style:[/] [bold cyan]{style_preset.name.upper()}[/] [dim]({style_preset.description})[/]\n"
        f"[dim]Detail Level:[/]   [bold yellow]{config.detail_level}/25[/] [dim](~{config.detail_level * 10} brushstrokes across all layers)[/]\n"
        f"[dim]Refinement Loop:[/] [bold yellow]{loop_val}/5[/] [dim]({loop_desc})[/]\n"
        f"[dim]AI Composer:[/]    [yellow]{engine_name}[/] [dim]at[/] [cyan]{engine_target}[/]\n"
        f"[dim]Bridge Target:[/]  [green]127.0.0.1:{config.control_port}[/]\n"
        f"[dim]Drawing Speed:[/]  [magenta]{config.step_delay}s per step[/]"
    )
    console.print(Panel(text, title="🎨 PhotoCraft Live MCP Painter", border_style="cyan"))


async def draw_prompt(
    client: PhotocraftMcpClient,
    prompt_text: str,
    config: PainterConfig,
) -> None:
    """Compose and animate drawing of a prompt (with optional vision reference images)."""
    clean_text, images = parse_prompt_and_images(prompt_text)
    try:
        validate_image_files(images)
    except Exception as e:
        console.print(f"[bold red]✗ Image error:[/] {e}\n")
        return

    effective_prompt = clean_text or (
        f"Recreate an expressive artist illustration inspired by the reference image{'s' if len(images) > 1 else ''}"
        if images
        else prompt_text
    )

    task_desc = f"'{effective_prompt}'"
    if images:
        img_names = ", ".join(f"'{p.name}'" for p in images)
        task_desc += f" [dim](reference: {img_names})[/]"

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Composing illustration plan for:[/] {task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description=task_desc, total=None)
        plan, source = plan_artwork(effective_prompt, config, config.default_width, config.default_height, images=images)

    title = plan.get("title", effective_prompt)
    steps = plan.get("steps", [])
    console.print(f"[bold green]✓[/] Composed [bold]{title}[/] ({len(steps)} steps via [cyan]{source}[/])")
    if images:
        console.print(f"  [dim]Visual reference from:[/] {', '.join(f'[cyan]{p}[/]' for p in images)}")
    console.print(f"[dim]Watching canvas update live in PhotoCraft...[/]")

    def on_progress(idx: int, total: int, name: str, step: dict[str, Any]) -> None:
        cmd = step.get("cmd") or step.get("id") or ""
        params = step.get("params", {})
        if cmd == "paint.bucket":
            col = params.get("color", "")
            x = params.get("x", 0)
            y = params.get("y", 0)
            desc = f"paint bucket {col} @ ({x}, {y})"
        elif cmd == "paint.stroke":
            kind = params.get("kind", "")
            fill = params.get("fill") or "brush stroke"
            desc = f"{kind} {fill}".strip()
        else:
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
        create_canvas=True,
    )
    console.print(
        f"[bold green]✓ Initial pass complete![/] "
        f"[dim]({summary['steps_drawn']}/{summary['total_steps']} steps rendered)[/]\n"
    )

    loop_total = getattr(config, "loop", 1)
    refinement_passes = max(0, loop_total - 1)

    phase_names = {
        1: "Phase 1: Complete Occlusion Repair & Solid Base Flats",
        2: "Phase 2: Volumetric Form Modeling & Waterline Grounding",
        3: "Phase 3: Facial Features, Anatomy & Dynamic Splashes",
        4: "Phase 4: Master Vector Inking & Specular Highlights",
    }

    for loop_i in range(1, refinement_passes + 1):
        phase_title = phase_names.get(min(loop_i, 4), "Progressive Art Refinement")
        console.print(
            f"[bold cyan]─── Refinement Loop Pass {loop_i}/{refinement_passes}: {phase_title} (loop setting: {loop_total}) ───[/]"
        )
        canvas_png: Path | None = None
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Exporting canvas snapshot for critique...[/]"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="capture", total=None)
                canvas_png = await client.capture_png()

            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold cyan]AI analyzing in-progress image & planning {phase_title} (pass {loop_i}/{refinement_passes})...[/]"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="refine", total=None)
                refine_plan, refine_source = plan_refinement_artwork(
                    effective_prompt,
                    config,
                    current_image=canvas_png,
                    loop_iteration=loop_i,
                    total_iterations=refinement_passes,
                    width=config.default_width,
                    height=config.default_height,
                    images=images,
                )

            critique = refine_plan.get("critique")
            if critique:
                console.print(
                    Panel(
                        f"[yellow]{critique}[/]",
                        title=f"🔍 AI Critique & Problem Analysis (Pass {loop_i})",
                        border_style="yellow",
                    )
                )

            refine_steps = refine_plan.get("steps", [])
            console.print(
                f"[bold green]✓[/] Refinement plan ready ({len(refine_steps)} corrective strokes via [cyan]{refine_source}[/])"
            )
            console.print(f"[dim]Applying refinement brushstrokes directly to active canvas...[/]")

            refine_summary = await execute_live_drawing(
                client,
                refine_plan,
                config,
                on_step_progress=on_progress,
                on_step_error=on_error,
                create_canvas=False,
            )
            console.print(
                f"[bold green]✓ Refinement pass {loop_i} complete![/] "
                f"[dim]({refine_summary['steps_drawn']}/{refine_summary['total_steps']} corrective steps rendered)[/]\n"
            )
        except Exception as e:
            console.print(f"[bold yellow]⚠ Refinement pass {loop_i} encountered an error:[/] {e}\n")
        finally:
            if canvas_png and canvas_png.exists():
                try:
                    canvas_png.unlink()
                except Exception:
                    pass

    console.print(
        f"[bold green]✨ Artwork complete on your PhotoCraft screen![/]\n"
    )


async def run_repl(client: PhotocraftMcpClient, config: PainterConfig) -> None:
    """Run interactive REPL loop."""
    print_banner(config)
    console.print(
        "[bold]Type any prompt to draw live on screen.[/] Commands: [cyan]/style <name>[/], [cyan]/model <name|#>[/], [cyan]/detail <1-25>[/], [cyan]/loop <1-5>[/], [cyan]/export <file>[/], [cyan]/speed <sec>[/], [cyan]/quit[/]\n"
        "[dim]Tip: Use file:<path> to reference images (e.g. file:/path/to/apple.png make a green apple)[/]\n"
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

        if user_input.startswith("/style"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                requested_style = parts[1].strip().lower()
                if requested_style in STYLE_PRESETS:
                    config.style = requested_style
                    preset = STYLE_PRESETS[requested_style]
                    console.print(
                        f"[bold green]✓[/] Artistic style set to [bold cyan]{preset.name.upper()}[/]\n"
                        f"  [dim]{preset.description}[/]\n"
                    )
                else:
                    available = ", ".join(f"[bold cyan]{k}[/]" for k in STYLE_PRESETS.keys())
                    console.print(
                        f"[red]Unknown style '{parts[1]}'.[/] Available styles: {available}\n"
                    )
            else:
                current_preset = get_style(config.style)
                console.print(
                    f"[bold]Active Artistic Style:[/] [bold cyan]{current_preset.name.upper()}[/] [dim]({current_preset.description})[/]\n"
                    f"[bold]Available Styles:[/]"
                )
                for k, p in STYLE_PRESETS.items():
                    active_marker = "[bold green]▶ (active)[/]" if k == current_preset.id else "  "
                    console.print(f"  {active_marker} [bold cyan]{p.id:10s}[/] : {p.description}")
                console.print("\n[dim]To switch styles, use: /style <name> (e.g. /style dreamlike)[/]\n")
            continue

        if user_input.startswith(("/model", "/models")):
            parts = user_input.split(maxsplit=1)
            choices = get_all_model_choices(config.ollama_host)
            current_active = config.ollama_model if config.provider == "ollama" else config.openai_model

            if len(parts) > 1:
                arg = parts[1].strip()
                try:
                    new_model, new_provider = resolve_model_selection(arg, choices)
                    config.provider = new_provider
                    if new_provider == "ollama":
                        config.ollama_model = new_model
                    else:
                        config.openai_model = new_model

                    console.print(
                        f"[bold green]✓[/] Active model switched to: [bold cyan]{new_model}[/] "
                        f"[dim](Provider: {new_provider.upper()})[/]\n"
                    )
                    if new_provider == "openai" and not config.openai_api_key:
                        console.print(
                            "[yellow]⚠ Note: OPENAI_API_KEY environment variable is not set. "
                            "Cloud API requests may fail unless configured.[/]\n"
                        )
                except ValueError as err:
                    console.print(f"[red]{err}[/]\n")
            else:
                table = build_models_table(choices, current_active, config.provider)
                console.print(table)
                console.print(
                    f"\n[bold]Current Active Model:[/] [bold cyan]{current_active}[/] "
                    f"[dim](Provider: {config.provider.upper()})[/]"
                )
                try:
                    selection = Prompt.ask(
                        "\n[bold magenta]Select model[/] [dim](enter # or name, or press Enter to keep current)[/]",
                        default="",
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n")
                    continue

                if selection:
                    try:
                        new_model, new_provider = resolve_model_selection(selection, choices)
                        config.provider = new_provider
                        if new_provider == "ollama":
                            config.ollama_model = new_model
                        else:
                            config.openai_model = new_model

                        console.print(
                            f"[bold green]✓[/] Active model switched to: [bold cyan]{new_model}[/] "
                            f"[dim](Provider: {new_provider.upper()})[/]\n"
                        )
                        if new_provider == "openai" and not config.openai_api_key:
                            console.print(
                                "[yellow]⚠ Note: OPENAI_API_KEY environment variable is not set. "
                                "Cloud API requests may fail unless configured.[/]\n"
                            )
                    except ValueError as err:
                        console.print(f"[red]{err}[/]\n")
                else:
                    console.print(f"[dim]Keeping current model: {current_active}[/]\n")
            continue

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

        if user_input.startswith("/loop"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    lvl = int(parts[1])
                    if 1 <= lvl <= 5:
                        config.loop = lvl
                        passes = lvl - 1
                        pass_desc = "single pass (no resubmission)" if passes == 0 else f"{passes} critique & refinement {'pass' if passes == 1 else 'passes'}"
                        console.print(f"[bold green]✓[/] Refinement loop set to [bold cyan]{config.loop}[/] [dim]({pass_desc})[/]\n")
                    else:
                        console.print("[red]Loop setting must be an integer between 1 and 5[/]\n")
                except ValueError:
                    console.print("[red]Invalid loop setting (expected integer 1-5)[/]\n")
            else:
                passes = config.loop - 1
                pass_desc = "single pass (no resubmission)" if passes == 0 else f"{passes} critique & refinement {'pass' if passes == 1 else 'passes'}"
                console.print(f"[cyan]Current loop setting:[/] [bold]{config.loop}[/]/5 [dim]({pass_desc})[/]\n"
                              f"[dim]Use /loop <1-5> to set (1 = standard single pass; 2-5 = submits rendered PNG back to AI for iterative refinement)[/]\n")
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
                "[bold cyan]Available Commands & Syntax:[/]\n"
                "  <prompt>          Compose and draw illustration live in PhotoCraft\n"
                "  file:<path> <msg> Use reference image(s) to inspire composition (e.g. file:/path/to/apple.png make a green apple)\n"
                "  /style            List all available artistic styles and show active style\n"
                "  /style <name>     Switch artistic style (realistic, dreamlike, abstract, sketchy, cartoon, painterly, cubism)\n"
                "  /model            List local & recommended models (https://ollama.com/search) with interactive selection\n"
                "  /model <name|#>   Switch active AI model on the fly by name or list number\n"
                "  /detail <1-25>    Adjust drawing detail level 1 to 25 (~10 to ~250 brushstrokes)\n"
                "  /loop <1-5>       Refinement loop count (1=single pass; 2-5=re-submits PNG snapshot to AI with critique instructions)\n"
                "  /export <path>    Export active document as PNG/PSD/etc.\n"
                "  /speed <sec>      Set live step delay (e.g. 0.05 for fast, 0.2 for slower)\n"
                "  /help             Display this help guide\n"
                "  /quit             Exit the program\n"
            )
            continue

        try:
            await draw_prompt(client, user_input, config)
        except Exception as e:
            console.print(f"[bold red]✗ Error during drawing:[/] {e}\n")


async def async_main(args: argparse.Namespace) -> None:
    """Entry point connecting to desktop and executing prompt or REPL."""
    provider = args.provider
    if not provider:
        if args.model and any(args.model.lower().startswith(p) for p in ("gpt-", "o1-", "o3-")):
            provider = "openai"
        else:
            provider = os.getenv("PAINTER_PROVIDER") or "ollama"

    config = PainterConfig(
        control_port=args.port,
        step_delay=args.delay,
        style=args.style,
        detail_level=args.detail,
        loop=args.loop,
        provider=provider,
        ollama_host=args.ollama_host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434",
        ollama_model=args.model or os.getenv("OLLAMA_MODEL") or "ornith-1.5:35b",
        openai_api_key=args.api_key or os.getenv("OPENAI_API_KEY"),
        openai_base_url=args.base_url or os.getenv("OPENAI_BASE_URL"),
        openai_model=args.openai_model or (args.model if provider == "openai" else "gpt-4o-mini"),
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
        "--style",
        "-s",
        type=str,
        default=os.getenv("PAINTER_STYLE") or "realistic",
        choices=list(STYLE_PRESETS.keys()),
        help=f"Overarching artistic style (choices: {', '.join(STYLE_PRESETS.keys())}; default: realistic)",
    )
    parser.add_argument(
        "--detail",
        "-d",
        type=int,
        default=5,
        choices=range(1, 26),
        metavar="1-25",
        help="Drawing detail level 1 (minimal) to 25 (ultra ~250 brushstrokes, default: 5)",
    )
    parser.add_argument(
        "--loop",
        "-l",
        type=int,
        default=int(os.getenv("PAINTER_LOOP") or "1"),
        choices=range(1, 6),
        metavar="1-5",
        help="Refinement loop count 1 to 5 (default: 1; values 2-5 re-submit rendered canvas PNG back to AI for iterative refinement)",
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

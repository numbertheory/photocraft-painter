"""Live drawing orchestrator that executes steps over MCP in real time."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable

from photocraft_painter.fallback_composer import format_document_title

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig
    from photocraft_painter.mcp_client import PhotocraftMcpClient

logger = logging.getLogger(__name__)


async def execute_live_drawing(
    client: PhotocraftMcpClient,
    plan: dict[str, Any],
    config: PainterConfig,
    on_step_progress: Callable[[int, int, str, dict[str, Any]], None] | None = None,
    on_step_error: Callable[[int, int, str, str], None] | None = None,
    create_canvas: bool = True,
) -> dict[str, Any]:
    """Execute drawing plan steps sequentially over MCP with animated delays."""
    width = plan.get("width", config.default_width)
    height = plan.get("height", config.default_height)
    bg = plan.get("background", "white")
    raw_title = plan.get("title", "Artwork")
    style = plan.get("style", config.style)
    detail = plan.get("detail_level", config.detail_level)
    model = plan.get("model", config.active_model)
    doc_name = format_document_title(raw_title, style=style, detail_level=detail, model=model)
    plan["title"] = doc_name
    steps: list[dict[str, Any]] = plan.get("steps", [])

    # 1. Create fresh canvas (only on initial pass)
    if create_canvas:
        await client.doc_new(
            width=width,
            height=height,
            background=bg,
            name=doc_name,
        )
        if config.step_delay > 0:
            await asyncio.sleep(config.step_delay)
    else:
        try:
            await client.new_layer(name=f"Refinement: {raw_title}")
        except Exception as e:
            logger.debug("Automatic refinement layer notice: %s", e)

    # 2. Sequentially execute drawing steps
    total = len(steps)
    succeeded = 0
    active_layer_is_raster = True  # initial background is a raster layer

    for idx, step in enumerate(steps, start=1):
        cmd = step.get("cmd") or step.get("id") or "shape.create"
        params = step.get("params", {})
        name = params.get("name") or f"Step {idx}"

        # If we need to paint but the active layer is a vector shape layer,
        # automatically create a new raster layer so paint.stroke has a valid target surface.
        if cmd == "layer.new.layer":
            active_layer_is_raster = True
        elif cmd == "shape.create":
            active_layer_is_raster = False
        elif cmd in ("paint.stroke", "paint.bucket"):
            if not active_layer_is_raster:
                try:
                    await client.new_layer("Paint Layer")
                    active_layer_is_raster = True
                except Exception as e:
                    logger.debug("Automatic layer creation notice: %s", e)

        if on_step_progress:
            on_step_progress(idx, total, name, step)

        try:
            await client.command_run(cmd, params)
            succeeded += 1
        except Exception as e:
            logger.warning("Step %d (%s) failed: %s", idx, name, e)
            if on_step_error:
                on_step_error(idx, total, name, str(e))

        if config.step_delay > 0:
            await asyncio.sleep(config.step_delay)

    return {
        "title": doc_name,
        "width": width,
        "height": height,
        "steps_drawn": succeeded,
        "total_steps": total,
    }

"""Live drawing orchestrator that executes steps over MCP in real time with layer isolation."""

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
    """Execute drawing plan steps sequentially over MCP with layer isolation and animated delays.

    To prevent background elements and shapes from interfering with or fragmenting paint bucket
    fills, each layer is isolated as it is drawn (prior background layers are temporarily hidden).
    Once drawing finishes, all layers are switched back on simultaneously so the complete composite
    renders properly for export and refinement loops.
    """
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

    known_layer_ids: list[int] = []

    async def get_doc_layer_ids() -> list[int]:
        """Fetch list of layer IDs currently present in the document."""
        try:
            if hasattr(client, "doc_inspect") and callable(client.doc_inspect):
                info = await client.doc_inspect()
            else:
                info = await client.command_run("document.inspect", {})
            if isinstance(info, dict):
                return [int(l["id"]) for l in info.get("layers", []) if isinstance(l, dict) and "id" in l]
        except Exception:
            pass
        return []

    async def isolate_layer(active_id: int | None) -> None:
        """Isolate the active layer by hiding all prior background layers."""
        if active_id is None:
            return
        # Hide all previously recorded background layers
        for prev_id in known_layer_ids:
            if prev_id != active_id:
                try:
                    await client.command_run("layer.setProps", {"layer": prev_id, "visible": False})
                except Exception as e:
                    logger.debug("Failed to hide background layer %s: %s", prev_id, e)
        # Ensure active layer is visible
        try:
            await client.command_run("layer.setProps", {"layer": active_id, "visible": True})
        except Exception as e:
            logger.debug("Failed to set active layer %s visible: %s", active_id, e)
        if active_id not in known_layer_ids:
            known_layer_ids.append(active_id)

    async def restore_all_layers() -> None:
        """Switch all layers back on after drawing completes."""
        for lid in known_layer_ids:
            try:
                await client.command_run("layer.setProps", {"layer": lid, "visible": True})
            except Exception as e:
                logger.debug("Layer visibility restore notice for layer %s: %s", lid, e)
        try:
            all_ids = await get_doc_layer_ids()
            for lid in all_ids:
                if lid not in known_layer_ids:
                    try:
                        await client.command_run("layer.setProps", {"layer": lid, "visible": True})
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Sweep layer visibility restore notice: %s", e)

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
        init_ids = await get_doc_layer_ids()
        for lid in init_ids:
            if lid not in known_layer_ids:
                known_layer_ids.append(lid)
    else:
        try:
            res_ref = await client.new_layer(name=f"Refinement: {raw_title}")
            if isinstance(res_ref, dict) and "layer" in res_ref:
                ref_id = int(res_ref["layer"])
                await isolate_layer(ref_id)
        except Exception as e:
            logger.debug("Automatic refinement layer notice: %s", e)

    # 2. Sequentially execute drawing steps with layer isolation
    total = len(steps)
    succeeded = 0
    active_layer_is_raster = True  # initial background is a raster layer

    try:
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
                        res_auto = await client.new_layer("Paint Layer")
                        active_layer_is_raster = True
                        if isinstance(res_auto, dict) and "layer" in res_auto:
                            auto_id = int(res_auto["layer"])
                            await isolate_layer(auto_id)
                    except Exception as e:
                        logger.debug("Automatic layer creation notice: %s", e)

            if on_step_progress:
                on_step_progress(idx, total, name, step)

            try:
                step_res = await client.command_run(cmd, params)
                succeeded += 1

                # If this step created a new layer, isolate it by making previous layers invisible!
                if cmd in ("layer.new.layer", "shape.create"):
                    new_id = None
                    if isinstance(step_res, dict) and "layer" in step_res:
                        new_id = int(step_res["layer"])
                    else:
                        doc_ids = await get_doc_layer_ids()
                        for lid in doc_ids:
                            if lid not in known_layer_ids:
                                new_id = lid
                                break
                    if new_id is not None:
                        await isolate_layer(new_id)

            except Exception as e:
                logger.warning("Step %d (%s) failed: %s", idx, name, e)
                if on_step_error:
                    on_step_error(idx, total, name, str(e))

            if config.step_delay > 0:
                await asyncio.sleep(config.step_delay)
    finally:
        # 3. Always restore all layers to visible once the drawing process finishes
        await restore_all_layers()
        if str(style).lower() == "pencil":
            await merge_drawing_layers_to_single_layer(client, target_name="Pencil Drawing")

    return {
        "title": doc_name,
        "width": width,
        "height": height,
        "steps_drawn": succeeded,
        "total_steps": total,
    }


async def merge_drawing_layers_to_single_layer(
    client: PhotocraftMcpClient,
    target_name: str = "Pencil Drawing",
) -> bool:
    """Merge all drawing layers above the background into a single drawing layer.

    Guarantees that the document has exactly two layers: 1 background and 1 containing the drawing.
    """
    try:
        if hasattr(client, "doc_inspect") and callable(client.doc_inspect):
            info = await client.doc_inspect()
        else:
            info = await client.command_run("document.inspect", {})
        if not isinstance(info, dict):
            return False

        layers = info.get("layers", [])
        if len(layers) <= 1:
            return True

        if len(layers) == 2:
            top_id = layers[0].get("id")
            if top_id is not None:
                try:
                    await client.command_run("layer.renameLayer", {"layer": top_id, "name": target_name})
                except Exception as e:
                    logger.debug("Could not rename top layer: %s", e)
            return True

        # When len(layers) > 2, merge down from the top until only 2 layers remain
        max_merges = len(layers) - 2
        for _ in range(max_merges + 5):
            if hasattr(client, "doc_inspect") and callable(client.doc_inspect):
                cur_info = await client.doc_inspect()
            else:
                cur_info = await client.command_run("document.inspect", {})
            if not isinstance(cur_info, dict):
                break
            cur_layers = cur_info.get("layers", [])
            if len(cur_layers) <= 2:
                break

            top_id = cur_layers[0].get("id")
            if top_id is None:
                break

            try:
                await client.command_run("layer.mergeDown", {"layer": top_id})
            except Exception as e:
                logger.debug("layer.mergeDown failed for layer %s: %s, attempting mergeVisible fallback", top_id, e)
                bg_id = cur_layers[-1].get("id")
                if bg_id is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": bg_id, "visible": False})
                    except Exception:
                        pass
                try:
                    await client.command_run("layer.mergeVisible", {})
                except Exception as e_mv:
                    logger.warning("layer.mergeVisible fallback notice: %s", e_mv)
                if bg_id is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": bg_id, "visible": True})
                    except Exception:
                        pass
                break

        # After merging down, rename the final top layer to target_name and ensure visibility
        final_info = await client.doc_inspect() if hasattr(client, "doc_inspect") else await client.command_run("document.inspect", {})
        if isinstance(final_info, dict):
            final_layers = final_info.get("layers", [])
            if final_layers:
                final_top_id = final_layers[0].get("id")
                if final_top_id is not None:
                    try:
                        await client.command_run("layer.renameLayer", {"layer": final_top_id, "name": target_name})
                    except Exception as e:
                        logger.debug("Could not rename final top layer: %s", e)
                for l in final_layers:
                    lid = l.get("id")
                    if lid is not None:
                        try:
                            await client.command_run("layer.setProps", {"layer": lid, "visible": True})
                        except Exception:
                            pass
        return True
    except Exception as e:
        logger.warning("Error consolidating drawing layers: %s", e)
        return False

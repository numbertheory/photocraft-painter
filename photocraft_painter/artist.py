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
    if plan.get("is_animation") or (plan.get("frames") and len(plan["frames"]) > 1):
        return await execute_live_animation(
            client=client,
            plan=plan,
            config=config,
            on_step_progress=on_step_progress,
            on_step_error=on_step_error,
            create_canvas=create_canvas,
        )

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
        if str(style).lower() == "pencil" and config.steps == 1:
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


async def execute_live_animation(
    client: PhotocraftMcpClient,
    plan: dict[str, Any],
    config: PainterConfig,
    on_step_progress: Callable[[int, int, str, dict[str, Any]], None] | None = None,
    on_step_error: Callable[[int, int, str, str], None] | None = None,
    create_canvas: bool = True,
) -> dict[str, Any]:
    """Execute multi-frame animation steps sequentially over MCP with layer-per-frame structure.

    Each animation frame corresponds to a distinct layer in PhotoCraft.
    Frames 2..N copy previous layers and selectively erase/redraw deltas.
    Post drawing: all frames are kept visible (even if they overlap), as requested.
    """
    width = plan.get("width", config.default_width)
    height = plan.get("height", config.default_height)
    bg = plan.get("background", "white")
    raw_title = plan.get("title", "Animation")
    style = plan.get("style", config.style)
    detail = plan.get("detail_level", config.detail_level)
    model = plan.get("model", config.active_model)
    doc_name = format_document_title(raw_title, style=style, detail_level=detail, model=model)
    plan["title"] = doc_name

    frames: list[dict[str, Any]] = plan.get("frames", [])
    if not frames:
        return await execute_live_drawing(client, plan, config, on_step_progress, on_step_error, create_canvas)

    total_steps = sum(len(f.get("steps", [])) for f in frames)
    current_step_global = 0
    total_succeeded = 0

    async def get_doc_layer_ids() -> list[int]:
        try:
            info = await client.doc_inspect() if hasattr(client, "doc_inspect") else await client.command_run("document.inspect", {})
            if isinstance(info, dict):
                return [int(l["id"]) for l in info.get("layers", []) if isinstance(l, dict) and "id" in l]
        except Exception:
            pass
        return []

    # 1. Create fresh canvas
    if create_canvas:
        await client.doc_new(
            width=width,
            height=height,
            background=bg,
            name=doc_name,
        )
        if config.step_delay > 0:
            await asyncio.sleep(config.step_delay)

    prev_frame_id: int | None = None

    try:
        for f_idx, frame in enumerate(frames, start=1):
            frame_name = frame.get("name") or f"Frame {f_idx}"
            is_base = frame.get("is_base", f_idx == 1)
            steps = frame.get("steps", [])

            if is_base:
                # Frame 1: Execute base artwork steps
                for s_idx, step in enumerate(steps, start=1):
                    cmd = step.get("cmd") or step.get("id") or "paint.stroke"
                    params = step.get("params", {})
                    name = params.get("name") or f"{frame_name} Step {s_idx}"
                    current_step_global += 1

                    if on_step_progress:
                        on_step_progress(current_step_global, total_steps, f"[{frame_name}] {name}", step)

                    try:
                        await client.command_run(cmd, params)
                        total_succeeded += 1
                    except Exception as e:
                        logger.warning("Frame 1 step %d failed: %s", s_idx, e)
                        if on_step_error:
                            on_step_error(current_step_global, total_steps, f"[{frame_name}] {name}", str(e))

                    if config.step_delay > 0:
                        await asyncio.sleep(config.step_delay)

                # Consolidate Frame 1 drawing layers into a single layer named "Frame 1" above background
                await merge_drawing_layers_to_single_layer(client, target_name="Frame 1")
                doc_layers = await get_doc_layer_ids()
                if doc_layers:
                    prev_frame_id = doc_layers[0]
                    try:
                        await client.command_run("layer.select", {"layer": prev_frame_id})
                    except Exception:
                        pass

            else:
                # Frames 2..N: Duplicate previous frame layer, hide previous, and apply delta strokes
                dup_params: dict[str, Any] = {"inPlace": True}
                if prev_frame_id is not None:
                    dup_params["layer"] = prev_frame_id
                    try:
                        await client.command_run("layer.select", {"layer": prev_frame_id})
                    except Exception:
                        pass

                dup_res = await client.command_run("layer.duplicate", dup_params)
                new_frame_id: int | None = None
                if isinstance(dup_res, dict) and "layer" in dup_res:
                    new_frame_id = int(dup_res["layer"])
                else:
                    doc_layers = await get_doc_layer_ids()
                    if doc_layers:
                        new_frame_id = doc_layers[0]

                if new_frame_id is not None:
                    try:
                        await client.command_run("layer.select", {"layer": new_frame_id})
                        await client.command_run("layer.renameLayer", {"layer": new_frame_id, "name": frame_name})
                        await client.command_run("layer.setProps", {"layer": new_frame_id, "visible": True})
                    except Exception as e:
                        logger.debug("Could not rename layer %s: %s", new_frame_id, e)

                if prev_frame_id is not None and prev_frame_id != new_frame_id:
                    try:
                        await client.command_run("layer.setProps", {"layer": prev_frame_id, "visible": False})
                    except Exception:
                        pass

                # Execute delta strokes for this frame
                for s_idx, step in enumerate(steps, start=1):
                    cmd = step.get("cmd") or step.get("id") or "paint.stroke"
                    if cmd in ("layer.duplicate", "layer.new.layerViaCopy"):
                        continue
                    params = step.get("params", {})
                    name = params.get("name") or f"{frame_name} Step {s_idx}"
                    current_step_global += 1

                    if on_step_progress:
                        on_step_progress(current_step_global, total_steps, f"[{frame_name}] {name}", step)

                    try:
                        await client.command_run(cmd, params)
                        total_succeeded += 1
                    except Exception as e:
                        logger.warning("Frame %d step %d failed: %s", f_idx, s_idx, e)
                        if on_step_error:
                            on_step_error(current_step_global, total_steps, f"[{frame_name}] {name}", str(e))

                    if config.step_delay > 0:
                        await asyncio.sleep(config.step_delay)

                if new_frame_id is not None:
                    prev_frame_id = new_frame_id

    finally:
        # POST DRAWING: Keep ALL frames visible, even if they overlap!
        try:
            info = await client.doc_inspect() if hasattr(client, "doc_inspect") else await client.command_run("document.inspect", {})
            if isinstance(info, dict):
                for layer in info.get("layers", []):
                    lid = layer.get("id")
                    if lid is not None:
                        try:
                            await client.command_run("layer.setProps", {"layer": lid, "visible": True})
                        except Exception:
                            pass
        except Exception as e:
            logger.warning("Notice restoring all frames visible post drawing: %s", e)

    return {
        "title": doc_name,
        "width": width,
        "height": height,
        "frames_drawn": len(frames),
        "total_frames": len(frames),
        "steps_drawn": total_succeeded,
        "total_steps": total_steps,
    }


async def list_open_documents(client: PhotocraftMcpClient) -> list[dict[str, Any]]:
    """Query PhotoCraft for all open document tabs."""
    docs: list[dict[str, Any]] = []
    for idx in range(32):
        try:
            info = await client.command_run("document.inspect", {"document": idx})
            if isinstance(info, dict) and ("layers" in info or "width" in info):
                docs.append({
                    "index": idx,
                    "title": info.get("name") or info.get("title") or f"Document {idx}",
                    "width": info.get("width"),
                    "height": info.get("height"),
                    "layers_count": len(info.get("layers", [])),
                })
        except Exception:
            break
    return docs


async def play_live_animation(
    client: PhotocraftMcpClient,
    target_doc: str | int | None = None,
    fps: float = 12.0,
    stop_event: asyncio.Event | None = None,
    on_frame_change: Callable[[int, int, str], None] | None = None,
    max_loops: int | None = None,
) -> dict[str, Any]:
    """Play back multi-frame animation live in PhotoCraft by cycling layer visibilities.

    If target_doc is None: plays the currently active document tab.
    If target_doc is an int: activates and plays that document index.
    If target_doc is a str: checks file path or document title.
    When playback finishes or is cancelled, restores ALL frame layers to visible.
    """
    import re
    from pathlib import Path

    # 1. Activate designated document if provided
    if target_doc is not None:
        if isinstance(target_doc, int):
            await client.command_run("document.activate", {"document": target_doc})
        elif isinstance(target_doc, str):
            p = Path(target_doc).expanduser()
            if p.exists() and p.is_file():
                await client.command_run("file.openAs", {"path": str(p.resolve())})
            else:
                matched = False
                if target_doc.isdigit():
                    try:
                        await client.command_run("document.activate", {"document": int(target_doc)})
                        matched = True
                    except Exception:
                        pass
                if not matched:
                    open_docs = await list_open_documents(client)
                    for d in open_docs:
                        if target_doc.lower() in str(d.get("title", "")).lower():
                            await client.command_run("document.activate", {"document": d["index"]})
                            matched = True
                            break

    # 2. Inspect active document
    info = await client.doc_inspect() if hasattr(client, "doc_inspect") else await client.command_run("document.inspect", {})
    if not isinstance(info, dict) or "layers" not in info:
        return {"status": "error", "message": "No active document or layers found in PhotoCraft"}

    all_layers = info.get("layers", [])
    if len(all_layers) < 2:
        return {"status": "error", "message": f"Document has only {len(all_layers)} layer(s). At least 2 layers are needed to animate."}

    # Background layer is typically the bottom-most layer (all_layers[-1])
    bg_id = all_layers[-1].get("id")

    frame_numbered: list[tuple[int, dict[str, Any]]] = []
    other_layers: list[dict[str, Any]] = []

    for l in all_layers:
        if l.get("id") == bg_id:
            continue
        lname = str(l.get("name", "")).strip()
        m = re.match(r"^Frame\s*(\d+)$", lname, re.IGNORECASE)
        if m:
            frame_numbered.append((int(m.group(1)), l))
        else:
            other_layers.append(l)

    frame_layers: list[dict[str, Any]] = []
    if frame_numbered:
        frame_numbered.sort(key=lambda x: x[0])
        frame_layers = [item[1] for item in frame_numbered]
    else:
        frame_layers = list(reversed(other_layers))

    if len(frame_layers) < 2:
        return {"status": "error", "message": f"Found only {len(frame_layers)} frame layer(s). Need at least 2 frames to play animation."}

    delay = 1.0 / max(1.0, min(60.0, float(fps)))
    total_frames = len(frame_layers)
    loops_done = 0

    try:
        if bg_id is not None:
            try:
                await client.command_run("layer.setProps", {"layer": bg_id, "visible": True})
            except Exception:
                pass

        # Initialize visibility: show first frame, hide others
        first_frame_id = frame_layers[0].get("id")
        for flayer in frame_layers[1:]:
            fid = flayer.get("id")
            if fid is not None:
                try:
                    await client.command_run("layer.setProps", {"layer": fid, "visible": False})
                except Exception:
                    pass
        if first_frame_id is not None:
            try:
                await client.command_run("layer.setProps", {"layer": first_frame_id, "visible": True})
            except Exception:
                pass

        prev_id = first_frame_id
        while True:
            if stop_event and stop_event.is_set():
                break

            for idx, flayer in enumerate(frame_layers, start=1):
                cur_id = flayer.get("id")
                cur_name = flayer.get("name") or f"Frame {idx}"

                if prev_id is not None and prev_id != cur_id:
                    try:
                        await client.command_run("layer.setProps", {"layer": prev_id, "visible": False})
                    except Exception:
                        pass
                if cur_id is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": cur_id, "visible": True})
                    except Exception:
                        pass
                prev_id = cur_id

                if on_frame_change:
                    on_frame_change(idx, total_frames, cur_name)

                await asyncio.sleep(delay)
                if stop_event and stop_event.is_set():
                    break

            loops_done += 1
            if max_loops is not None and loops_done >= max_loops:
                break
            if stop_event and stop_event.is_set():
                break

    finally:
        # Post playback: restore ALL frames to visible (keeping user's preference)
        for flayer in frame_layers:
            fid = flayer.get("id")
            if fid is not None:
                try:
                    await client.command_run("layer.setProps", {"layer": fid, "visible": True})
                except (Exception, KeyboardInterrupt):
                    pass
        if bg_id is not None:
            try:
                await client.command_run("layer.setProps", {"layer": bg_id, "visible": True})
            except (Exception, KeyboardInterrupt):
                pass

    return {
        "status": "ok",
        "frames_played": total_frames,
        "loops_completed": loops_done,
        "fps": fps,
    }

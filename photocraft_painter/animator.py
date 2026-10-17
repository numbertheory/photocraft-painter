"""Animation composition and frame delta generator for PhotoCraft Painter.

Supports multi-frame cel animation where each frame corresponds to a distinct layer in PhotoCraft.
Strictly enforces:
1. Each frame has the exact same level of detail (identical number of brush strokes per frame).
2. Frames 2..N build on previous frames by copying layers and applying selective erasures
   (`paint.stroke` with `erase: true`) and replacement strokes, so drawing doesn't restart from scratch.
3. Smooth, subtle incremental changes between consecutive frames.
"""

from __future__ import annotations

import copy
import logging
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from photocraft_painter.composer import normalize_step, plan_artwork
from photocraft_painter.fallback_composer import (
    format_document_title,
    is_portrait_or_face_prompt,
    parse_geometric_shape_prompt,
    plan_fallback,
)
from photocraft_painter.strokes import (
    smooth_path,
    stroke_enclosed_loop,
    stroke_enclosed_oval,
    stroke_line,
    stroke_polygon,
)
from photocraft_painter.styles import get_style

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig

logger = logging.getLogger(__name__)


def count_brush_strokes(steps: list[dict[str, Any]]) -> int:
    """Count how many paint.stroke commands are in the steps list."""
    count = 0
    for s in steps:
        cmd = s.get("cmd") or s.get("id") or ""
        if cmd == "paint.stroke":
            count += 1
    return count


def enforce_stroke_parity(
    steps: list[dict[str, Any]],
    target_count: int,
    canvas_w: int = 800,
    canvas_h: int = 800,
    default_color: str = "#333333",
) -> list[dict[str, Any]]:
    """Enforce that the steps contain EXACTLY target_count paint.stroke commands.

    If deficient, subtle inbetween / accent brushstrokes are added.
    If excessive, surplus non-essential strokes are trimmed.
    """
    current_count = count_brush_strokes(steps)
    if current_count == target_count:
        return steps

    result = list(steps)

    if current_count > target_count:
        # Trim excess strokes from the end, prioritizing keeping erase and key draw strokes
        new_steps: list[dict[str, Any]] = []
        strokes_kept = 0
        for s in result:
            cmd = s.get("cmd") or s.get("id") or ""
            if cmd == "paint.stroke":
                if strokes_kept < target_count:
                    new_steps.append(s)
                    strokes_kept += 1
            else:
                new_steps.append(s)
        return new_steps

    # If current_count < target_count, add micro-refinement inbetween strokes
    needed = target_count - current_count
    # Find a stroke to base subtle accents on
    existing_strokes = [s for s in result if (s.get("cmd") or s.get("id")) == "paint.stroke"]
    ref_pts = [[400.0, 400.0, 0.5], [405.0, 405.0, 0.5]]
    ref_col = default_color
    if existing_strokes:
        last_params = existing_strokes[-1].get("params", {})
        pts = last_params.get("points")
        if pts and isinstance(pts, list) and len(pts) >= 2:
            ref_pts = pts
        ref_col = last_params.get("color") or default_color

    for i in range(needed):
        # Subtle stipple or micro-shading stroke
        cx = float(ref_pts[0][0]) + (i * 3.5) % 30.0 - 15.0
        cy = float(ref_pts[0][1]) + (i * 2.5) % 20.0 - 10.0
        cx = max(10.0, min(float(canvas_w - 10), cx))
        cy = max(10.0, min(float(canvas_h - 10), cy))
        micro_stroke = {
            "cmd": "paint.stroke",
            "params": {
                "name": f"Detail Inbetweening Accent {i + 1}",
                "points": [[round(cx, 1), round(cy, 1), 0.4], [round(cx + 2.0, 1), round(cy + 2.0, 1), 0.3]],
                "size": 3.0,
                "color": ref_col,
                "hardness": 0.8,
                "opacity": 0.5,
                "erase": False,
            },
        }
        result.append(micro_stroke)

    return result


def extract_mobile_feature_strokes(
    strokes: list[dict[str, Any]],
    motion_type: str = "bounce",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition strokes into mobile (animated) and stationary (static) strokes.

    Returns: (mobile_strokes, stationary_strokes)
    """
    mobile: list[dict[str, Any]] = []
    stationary: list[dict[str, Any]] = []

    for s in strokes:
        name = str(s.get("params", {}).get("name", "")).lower()
        # Elements that typically move in animations
        is_mobile = any(
            kw in name
            for kw in (
                "eye", "pupil", "lid", "blink", "mouth", "lip", "smile", "beak", "bill",
                "wing", "arm", "hand", "wave", "splash", "ripple", "tail", "bob", "head",
                "water splash", "bubble", "gleam", "highlight", "crest", "oscillation",
            )
        )
        if is_mobile:
            mobile.append(s)
        else:
            stationary.append(s)

    # If nothing was explicitly tagged as mobile, pick the upper 30% of strokes as foreground mobile features
    if not mobile and strokes:
        split_idx = max(1, int(len(strokes) * 0.7))
        stationary = strokes[:split_idx]
        mobile = strokes[split_idx:]

    return mobile, stationary


def apply_motion_transform(
    stroke: dict[str, Any],
    dx: float,
    dy: float,
    scale_y: float = 1.0,
    origin_y: float = 400.0,
) -> dict[str, Any]:
    """Return a new stroke with transformed coordinates."""
    transformed = copy.deepcopy(stroke)
    params = transformed.get("params", {})
    pts = params.get("points", [])
    new_pts: list[list[float]] = []

    for p in pts:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            x = float(p[0]) + dx
            y = (float(p[1]) - origin_y) * scale_y + origin_y + dy
            pr = float(p[2]) if len(p) >= 3 else 0.8
            new_pts.append([round(x, 1), round(y, 1), round(pr, 2)])

    params["points"] = new_pts
    transformed["params"] = params
    return transformed


def create_erase_stroke_from(stroke: dict[str, Any], expand_size: float = 1.3) -> dict[str, Any]:
    """Create an erase stroke corresponding to a previous stroke."""
    erased = copy.deepcopy(stroke)
    params = erased.get("params", {})
    old_size = float(params.get("size") or 6.0)
    params["name"] = f"Erase: {params.get('name', 'Stroke')}"
    params["erase"] = True
    params["size"] = min(300.0, max(2.0, old_size * expand_size))
    params["hardness"] = 1.0
    params["opacity"] = 1.0
    erased["params"] = params
    return erased


def plan_animation_fallback(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
) -> dict[str, Any]:
    """Procedural fallback for generating multi-frame animation with strict stroke parity."""
    num_frames = max(1, min(24, int(config.steps)))
    detail = config.detail_level
    style = config.style

    # 1. Generate base artwork (Frame 1)
    base_plan = plan_fallback(prompt, width, height, detail_level=detail, style=style, model=config.active_model)
    base_steps = [normalize_step(s, width, height) for s in base_plan.get("steps", [])]

    # Collect base brush strokes and determine the invariant stroke budget S
    base_strokes = [s for s in base_steps if (s.get("cmd") or s.get("id")) == "paint.stroke"]
    stroke_budget = len(base_strokes)
    if stroke_budget == 0:
        stroke_budget = max(10, detail * 10)

    # Wrap Frame 1 steps:
    # Ensure Frame 1 has exactly stroke_budget strokes
    frame_1_steps = enforce_stroke_parity(base_steps, stroke_budget, width, height)

    frames: list[dict[str, Any]] = [
        {
            "frame_index": 1,
            "name": "Frame 1",
            "is_base": True,
            "steps": frame_1_steps,
            "stroke_count": count_brush_strokes(frame_1_steps),
        }
    ]

    if num_frames == 1:
        return {
            "title": base_plan.get("title", prompt),
            "width": width,
            "height": height,
            "background": base_plan.get("background", "white"),
            "frames_count": 1,
            "strokes_per_frame": stroke_budget,
            "frames": frames,
            "steps": frame_1_steps,
        }

    # Identify mobile strokes for delta animation
    mobile_strokes, stationary_strokes = extract_mobile_feature_strokes(base_strokes)
    if not mobile_strokes:
        mobile_strokes = base_strokes[-max(5, stroke_budget // 3):]

    # Detect animation motion characteristics from prompt
    prompt_lower = prompt.lower()
    is_wave = any(k in prompt_lower for k in ("wave", "waving", "wing", "hand", "arm", "tail"))
    is_blink = any(k in prompt_lower for k in ("blink", "blinking", "eye", "wink"))
    is_walk = any(k in prompt_lower for k in ("walk", "walking", "run", "running", "step"))

    prev_mobile = copy.deepcopy(mobile_strokes)

    # 2. Generate Frames 2..N
    for k in range(2, num_frames + 1):
        # Progress phase 0..2pi for looping cycles
        phase = 2.0 * math.pi * float(k - 1) / float(num_frames)

        # Calculate subtle coordinate displacements (bounded to subtle delta, e.g. <= 25-35 px)
        if is_wave:
            dx = round(15.0 * math.sin(phase), 1)
            dy = round(-8.0 * math.cos(phase), 1)
            squash = 1.0 + 0.05 * math.sin(phase)
        elif is_blink:
            # Blink smoothly closes around midpoint
            blink_amt = max(0.0, math.sin(phase))
            dx = round(4.0 * math.cos(phase), 1)
            dy = round(1.0 + 3.0 * blink_amt, 1)
            squash = max(0.2, 1.0 - 0.7 * blink_amt)
        elif is_walk:
            dx = round(20.0 * math.sin(phase), 1)
            dy = round(-10.0 * abs(math.cos(phase)), 1)
            squash = 1.0 + 0.06 * math.sin(phase * 2)
        else:
            # Default: gentle bounce and floating bob (e.g. rubber duck or bouncing shape)
            dx = round(6.0 * math.sin(phase), 1)
            dy = round(-16.0 * math.sin(phase), 1)
            squash = 1.0 + 0.06 * math.cos(phase)

        frame_k_steps: list[dict[str, Any]] = []

        # Step A: Duplicate active layer from previous frame
        frame_k_steps.append({
            "cmd": "layer.duplicate",
            "params": {"name": f"Frame {k}"},
        })

        # Step B: Erase previous frame's mobile positions
        # Take a subset of mobile strokes to erase (up to half of the budget)
        erase_count = min(len(prev_mobile), max(3, stroke_budget // 3))
        erase_subset = prev_mobile[:erase_count]
        erase_strokes: list[dict[str, Any]] = []
        for es in erase_subset:
            erase_strokes.append(create_erase_stroke_from(es))

        # Step C: Redraw elements at new displaced coordinates
        current_mobile: list[dict[str, Any]] = []
        draw_strokes: list[dict[str, Any]] = []
        for ms in mobile_strokes:
            trans = apply_motion_transform(ms, dx=dx, dy=dy, scale_y=squash)
            # Ensure erase is False
            trans.setdefault("params", {})["erase"] = False
            current_mobile.append(trans)
            draw_strokes.append(trans)

        # Assemble frame steps
        frame_k_steps.extend(erase_strokes)
        frame_k_steps.extend(draw_strokes)

        # Step D: Strictly balance strokes so stroke_count == stroke_budget!
        frame_k_steps = enforce_stroke_parity(
            frame_k_steps,
            target_count=stroke_budget,
            canvas_w=width,
            canvas_h=height,
        )

        frames.append({
            "frame_index": k,
            "name": f"Frame {k}",
            "is_base": False,
            "steps": frame_k_steps,
            "stroke_count": count_brush_strokes(frame_k_steps),
        })

        prev_mobile = current_mobile

    title = base_plan.get("title", prompt)
    clean_title = re.sub(r"\[\d+\s*Frames?\]", "", title, flags=re.IGNORECASE).strip()
    formatted_title = f"{clean_title} [{num_frames} Frames]"

    return {
        "title": formatted_title,
        "width": width,
        "height": height,
        "background": base_plan.get("background", "white"),
        "is_animation": True,
        "frames_count": num_frames,
        "strokes_per_frame": stroke_budget,
        "frames": frames,
    }


def plan_animation(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> tuple[dict[str, Any], str]:
    """Compose a multi-frame animation plan with strict stroke parity and layer-per-frame structure."""
    num_frames = max(1, min(24, int(config.steps)))
    if num_frames == 1:
        # Standard static drawing pass
        plan, source = plan_artwork(prompt, config, width, height, images=images)
        return plan, source

    # Multi-frame animation mode
    # For now, generate base via plan_artwork/fallback, then build delta frames
    try:
        base_plan, source = plan_artwork(prompt, config, width, height, images=images)
        base_steps = [normalize_step(s, width, height) for s in base_plan.get("steps", [])]
        base_strokes = [s for s in base_steps if (s.get("cmd") or s.get("id")) == "paint.stroke"]
        stroke_budget = len(base_strokes)
        if stroke_budget == 0:
            stroke_budget = max(10, config.detail_level * 10)

        frame_1_steps = enforce_stroke_parity(base_steps, stroke_budget, width, height)
        frames: list[dict[str, Any]] = [
            {
                "frame_index": 1,
                "name": "Frame 1",
                "is_base": True,
                "steps": frame_1_steps,
                "stroke_count": count_brush_strokes(frame_1_steps),
            }
        ]

        # Generate subsequent frames with deltas
        mobile_strokes, _ = extract_mobile_feature_strokes(base_strokes)
        if not mobile_strokes:
            mobile_strokes = base_strokes[-max(5, stroke_budget // 3):]

        prev_mobile = copy.deepcopy(mobile_strokes)

        for k in range(2, num_frames + 1):
            phase = 2.0 * math.pi * float(k - 1) / float(num_frames)
            dx = round(8.0 * math.sin(phase), 1)
            dy = round(-14.0 * math.sin(phase), 1)
            squash = 1.0 + 0.05 * math.cos(phase)

            frame_k_steps: list[dict[str, Any]] = []
            frame_k_steps.append({
                "cmd": "layer.duplicate",
                "params": {"name": f"Frame {k}"},
            })

            erase_count = min(len(prev_mobile), max(3, stroke_budget // 3))
            for es in prev_mobile[:erase_count]:
                frame_k_steps.append(create_erase_stroke_from(es))

            current_mobile: list[dict[str, Any]] = []
            for ms in mobile_strokes:
                trans = apply_motion_transform(ms, dx=dx, dy=dy, scale_y=squash)
                trans.setdefault("params", {})["erase"] = False
                current_mobile.append(trans)
                frame_k_steps.append(trans)

            frame_k_steps = enforce_stroke_parity(
                frame_k_steps,
                target_count=stroke_budget,
                canvas_w=width,
                canvas_h=height,
            )

            frames.append({
                "frame_index": k,
                "name": f"Frame {k}",
                "is_base": False,
                "steps": frame_k_steps,
                "stroke_count": count_brush_strokes(frame_k_steps),
            })
            prev_mobile = current_mobile

        title = base_plan.get("title", prompt)
        clean_title = re.sub(r"\[\d+\s*Frames?\]", "", title, flags=re.IGNORECASE).strip()
        formatted_title = f"{clean_title} [{num_frames} Frames]"

        plan = {
            "title": formatted_title,
            "width": width,
            "height": height,
            "background": base_plan.get("background", "white"),
            "is_animation": True,
            "frames_count": num_frames,
            "strokes_per_frame": stroke_budget,
            "frames": frames,
        }
        return plan, f"{source}+animator"

    except Exception as e:
        logger.warning("Error composing LLM animation plan: %s. Using procedural animation fallback.", e)
        fallback = plan_animation_fallback(prompt, config, width, height)
        return fallback, "procedural-animator"

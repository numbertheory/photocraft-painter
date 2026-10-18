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


def is_essential_feature_stroke(stroke: dict[str, Any]) -> bool:
    """Return True if stroke is a core drawing feature (body fill, face, eye, outline)."""
    params = stroke.get("params", {})
    name = str(params.get("name", "")).lower()
    if any(k in name for k in ("accent", "inbetween", "micro", "stipple", "detail inbetweening", "speed accent")):
        return False
    essential_keywords = (
        "fill", "paint", "color", "body", "fur", "skin", "belly", "inner",
        "ear", "eye", "pupil", "iris", "nose", "mouth", "lip", "beak",
        "face", "head", "whisker", "contour", "outline", "silhouette",
    )
    if any(k in name for k in essential_keywords):
        return True
    return False


def enforce_stroke_parity(
    steps: list[dict[str, Any]],
    target_count: int,
    canvas_w: int = 800,
    canvas_h: int = 800,
    default_color: str = "#333333",
) -> list[dict[str, Any]]:
    """Enforce that the steps contain EXACTLY target_count paint.stroke commands.

    If deficient, subtle inbetween / accent brushstrokes are added.
    If excessive, surplus non-essential strokes are trimmed while preserving core features.
    """
    current_count = count_brush_strokes(steps)
    if current_count == target_count:
        return steps

    result = list(steps)

    if current_count > target_count:
        excess = current_count - target_count
        to_drop: set[int] = set()

        # Phase 1: drop non-essential accent/inbetween strokes from the end
        for idx in range(len(result) - 1, -1, -1):
            s = result[idx]
            if (s.get("cmd") or s.get("id")) == "paint.stroke":
                if not is_essential_feature_stroke(s) and not s.get("params", {}).get("erase"):
                    to_drop.add(idx)
                    if len(to_drop) == excess:
                        break

        # Phase 2: if still excess, drop surplus erase strokes beyond the first 2
        if len(to_drop) < excess:
            erase_indices = [
                idx for idx, s in enumerate(result)
                if (s.get("cmd") or s.get("id")) == "paint.stroke" and s.get("params", {}).get("erase")
            ]
            if len(erase_indices) > 2:
                for idx in reversed(erase_indices[2:]):
                    if idx not in to_drop:
                        to_drop.add(idx)
                        if len(to_drop) == excess:
                            break

        # Phase 3: if still excess (rare), drop from any remaining strokes from the end
        if len(to_drop) < excess:
            for idx in range(len(result) - 1, -1, -1):
                if idx in to_drop:
                    continue
                s = result[idx]
                if (s.get("cmd") or s.get("id")) == "paint.stroke":
                    to_drop.add(idx)
                    if len(to_drop) == excess:
                        break

        return [s for idx, s in enumerate(result) if idx not in to_drop]

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


BACKGROUND_KEYWORDS = (
    "background", "ground", "floor", "horizon", "sky", "cloud",
    "backdrop", "surface", "table", "road", "street", "platform",
    "court", "field", "wall", "room", "baseline", "shadow on ground",
)

PART_KEYWORDS = (
    "eye", "pupil", "lid", "blink", "mouth", "lip", "smile", "beak", "bill",
    "wing", "arm", "hand", "wave", "splash", "ripple", "tail", "bob", "head",
    "water splash", "bubble", "gleam", "highlight", "crest", "oscillation",
)


def get_strokes_bounds(strokes: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    """Calculate (min_x, min_y, max_x, max_y) bounding box for a set of strokes."""
    all_pts: list[tuple[float, float]] = []
    for s in strokes:
        pts = s.get("params", {}).get("points", [])
        if isinstance(pts, list):
            for p in pts:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    all_pts.append((float(p[0]), float(p[1])))
    if not all_pts:
        return 200.0, 200.0, 400.0, 400.0
    return (
        min(p[0] for p in all_pts),
        min(p[1] for p in all_pts),
        max(p[0] for p in all_pts),
        max(p[1] for p in all_pts),
    )


def extract_mobile_feature_strokes(
    strokes: list[dict[str, Any]],
    motion_type: str = "bounce",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition strokes into mobile (animated) and stationary (static) strokes.

    Returns: (mobile_strokes, stationary_strokes)
    """
    if not strokes:
        return [], []

    prompt_lower = str(motion_type or "").lower()
    is_locomotion = any(
        kw in prompt_lower
        for kw in (
            "across", "bounce", "bouncing", "ball", "walk", "walking", "run", "running",
            "fly", "flying", "jump", "jumping", "swim", "swimming", "roll", "rolling",
            "travel", "move", "moving", "slide", "sliding", "glide", "gliding",
            "hop", "hopping", "drive", "driving", "chase", "chasing",
        )
    )

    stationary: list[dict[str, Any]] = []
    subject_strokes: list[dict[str, Any]] = []

    for s in strokes:
        name = str(s.get("params", {}).get("name", "")).lower()
        if any(bg in name for bg in BACKGROUND_KEYWORDS):
            stationary.append(s)
        else:
            subject_strokes.append(s)

    if is_locomotion or not subject_strokes:
        # Whole subject moves across/bounces; only background stays stationary
        mobile = subject_strokes if subject_strokes else list(strokes)
        stationary = [s for s in strokes if s not in mobile]
        return mobile, stationary

    # For localized in-place motions (e.g. blinking, smiling, waving)
    mobile = []
    body_stationary = []
    for s in subject_strokes:
        name = str(s.get("params", {}).get("name", "")).lower()
        if any(kw in name for kw in PART_KEYWORDS):
            mobile.append(s)
        else:
            body_stationary.append(s)

    if not mobile:
        mobile = subject_strokes
        stationary = [s for s in strokes if s not in mobile]
    else:
        stationary.extend(body_stationary)

    return mobile, stationary


def apply_motion_transform(
    stroke: dict[str, Any],
    dx: float,
    dy: float,
    scale_y: float = 1.0,
    origin_y: float = 400.0,
    scale_x: float = 1.0,
    origin_x: float = 400.0,
) -> dict[str, Any]:
    """Return a new stroke with transformed coordinates."""
    transformed = copy.deepcopy(stroke)
    params = transformed.get("params", {})
    pts = params.get("points", [])
    new_pts: list[list[float]] = []

    for p in pts:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            x = (float(p[0]) - origin_x) * scale_x + origin_x + dx
            y = (float(p[1]) - origin_y) * scale_y + origin_y + dy
            pr = float(p[2]) if len(p) >= 3 else 0.8
            new_pts.append([round(x, 1), round(y, 1), round(pr, 2)])

    params["points"] = new_pts
    transformed["params"] = params
    return transformed


def create_erase_stroke_from(stroke: dict[str, Any], expand_size: float = 1.5) -> dict[str, Any]:
    """Create an erase stroke corresponding to a previous stroke."""
    erased = copy.deepcopy(stroke)
    params = erased.get("params", {})
    old_size = float(params.get("size") or 6.0)
    params["name"] = f"Erase: {params.get('name', 'Stroke')}"
    params["erase"] = True
    params["size"] = min(300.0, max(4.0, old_size * expand_size))
    params["hardness"] = 1.0
    params["opacity"] = 1.0
    erased["params"] = params
    return erased


def create_erase_strokes_covering(
    prev_mobile_strokes: list[dict[str, Any]],
    max_erase_count: int = 4,
) -> list[dict[str, Any]]:
    """Create erase strokes that cleanly clear the previous mobile subject along its actual paths.

    Never uses giant 250px crater sweeps that wipe out background scenery or overlap with the
    new subject position.
    """
    if not prev_mobile_strokes:
        return []

    # Sort previous mobile strokes by brush size descending so we erase the largest masses first
    sorted_strokes = sorted(
        prev_mobile_strokes,
        key=lambda s: float(s.get("params", {}).get("size") or 5.0),
        reverse=True,
    )

    limit = max(2, min(max_erase_count, len(sorted_strokes)))
    selected = sorted_strokes[:limit]
    erases = []
    for s in selected:
        e = create_erase_stroke_from(s, expand_size=1.25)
        cur_sz = float(e.get("params", {}).get("size", 10.0))
        e["params"]["size"] = round(max(40.0, min(100.0, cur_sz)), 1)
        erases.append(e)

    # If only 1 stroke in mobile_strokes, add a second targeted stroke to satisfy parity/coverage
    if len(erases) < 2 and sorted_strokes:
        e2 = create_erase_stroke_from(sorted_strokes[0], expand_size=1.4)
        cur_sz2 = float(e2.get("params", {}).get("size", 10.0))
        e2["params"]["size"] = round(max(40.0, min(100.0, cur_sz2)), 1)
        erases.append(e2)

    return erases


def build_animation_frames(
    base_steps: list[dict[str, Any]],
    prompt: str,
    num_frames: int,
    stroke_budget: int,
    width: int = 800,
    height: int = 800,
) -> list[dict[str, Any]]:
    """Generate multi-frame animation layers with clean previous-frame erasure and physics-based motion."""
    base_strokes = [s for s in base_steps if (s.get("cmd") or s.get("id")) == "paint.stroke"]
    mobile_strokes, stationary_strokes = extract_mobile_feature_strokes(base_strokes, prompt)
    if not mobile_strokes:
        mobile_strokes = list(base_strokes)

    num_mobile = len(mobile_strokes)
    num_erase = min(4, max(2, num_mobile // 8)) if num_frames > 1 else 0
    target_budget = max(stroke_budget, len(base_strokes), num_mobile + num_erase)

    frame_1_steps = enforce_stroke_parity(base_steps, target_budget, width, height)
    frames: list[dict[str, Any]] = [
        {
            "frame_index": 1,
            "name": "Frame 1",
            "is_base": True,
            "steps": frame_1_steps,
            "stroke_count": count_brush_strokes(frame_1_steps),
        }
    ]

    if num_frames <= 1:
        return frames

    min_x, min_y, max_x, max_y = get_strokes_bounds(mobile_strokes)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    bottom_y = max_y

    prompt_lower = prompt.lower()
    is_across = any(kw in prompt_lower for kw in ("across", "screen", "cross", "traverse", "left to right", "through"))
    is_bounce = any(kw in prompt_lower for kw in ("bounce", "bouncing", "ball", "hop", "hopping", "rebound"))
    is_walk = any(kw in prompt_lower for kw in ("walk", "walking", "run", "running", "step", "stride"))
    is_blink = any(kw in prompt_lower for kw in ("blink", "blinking", "eye", "wink"))
    is_wave = any(kw in prompt_lower for kw in ("wave", "waving", "wing", "hand", "arm", "tail"))

    # Determine across-screen horizontal travel distance
    if cx < 400.0:
        total_dx = min(500.0, max(150.0, (float(width) - 100.0) - cx))
    else:
        total_dx = -min(500.0, max(150.0, cx - 100.0))

    prev_mobile = copy.deepcopy(mobile_strokes)

    for k in range(2, num_frames + 1):
        t = float(k - 1) / float(num_frames - 1)
        theta = 2.0 * math.pi * float(k - 1) / float(num_frames)

        if is_bounce and is_across:
            # Trajectory across screen with smooth bounce arcs
            dx = round(t * total_dx, 1)
            num_bounces = 2 if num_frames <= 12 else 3
            # Inverted sine arc bounces
            bounce_height = min(120.0, max(60.0, bottom_y - 120.0))
            bounce_arc = abs(math.sin(math.pi * float(num_bounces) * t))
            dy = -round(bounce_height * bounce_arc, 1)

            # Squash & stretch: near ground impact squash, mid-air stretch
            cycle = t * float(num_bounces)
            tau = cycle - math.floor(cycle)
            if tau < 0.12 or tau > 0.88:
                squash_y = 0.72
                squash_x = 1.25
                orig_y = bottom_y
            elif 0.18 <= tau <= 0.35 or 0.65 <= tau <= 0.82:
                squash_y = 1.15
                squash_x = 0.90
                orig_y = cy
            else:
                squash_y = 1.0
                squash_x = 1.0
                orig_y = cy
            orig_x = cx

        elif is_walk and is_across:
            dx = round(t * total_dx, 1)
            dy = -round(12.0 * abs(math.sin(math.pi * 6.0 * t)), 1)
            squash_y = 1.0 + 0.04 * math.sin(math.pi * 6.0 * t)
            squash_x = 1.0
            orig_x = cx
            orig_y = bottom_y

        elif is_across:
            dx = round(t * total_dx, 1)
            dy = -round(15.0 * math.sin(2.0 * math.pi * 2.0 * t), 1)
            squash_y = 1.0
            squash_x = 1.0
            orig_x = cx
            orig_y = cy

        elif is_bounce and not is_across:
            # Bouncing in place
            dx = 0.0
            tau = (1.0 - math.cos(theta)) / 2.0
            dy = -round(80.0 * tau, 1)
            if tau < 0.12:
                squash_y = 0.72
                squash_x = 1.25
                orig_y = bottom_y
            else:
                squash_y = 1.10
                squash_x = 0.95
                orig_y = cy
            orig_x = cx

        elif is_walk and not is_across:
            dx = round(16.0 * math.sin(theta), 1)
            dy = -round(10.0 * abs(math.cos(theta)), 1)
            squash_y = 1.0 + 0.05 * math.sin(2.0 * theta)
            squash_x = 1.0
            orig_x = cx
            orig_y = bottom_y

        elif is_wave:
            dx = round(15.0 * math.sin(theta), 1)
            dy = -round(8.0 * math.cos(theta), 1)
            squash_y = 1.0 + 0.05 * math.sin(theta)
            squash_x = 1.0
            orig_x = cx
            orig_y = cy

        elif is_blink:
            blink_amt = max(0.0, math.sin(theta))
            dx = 0.0
            dy = round(2.0 * blink_amt, 1)
            squash_y = max(0.15, 1.0 - 0.85 * blink_amt)
            squash_x = 1.0
            orig_x = cx
            orig_y = cy

        else:
            dx = round(10.0 * math.sin(theta), 1)
            dy = -round(14.0 * math.sin(theta), 1)
            squash_y = 1.0 + 0.05 * math.cos(theta)
            squash_x = 1.0
            orig_x = cx
            orig_y = cy

        frame_k_steps: list[dict[str, Any]] = []

        # Step A: Duplicate active layer from previous frame
        frame_k_steps.append({
            "cmd": "layer.duplicate",
            "params": {"name": f"Frame {k}"},
        })

        # Step B: Erase previous frame's mobile positions cleanly
        erase_strokes = create_erase_strokes_covering(prev_mobile, max_erase_count=num_erase)

        # Step C: Redraw elements at new displaced coordinates
        current_mobile: list[dict[str, Any]] = []
        draw_strokes: list[dict[str, Any]] = []
        for ms in mobile_strokes:
            trans = apply_motion_transform(
                ms,
                dx=dx,
                dy=dy,
                scale_y=squash_y,
                origin_y=orig_y,
                scale_x=squash_x,
                origin_x=orig_x,
            )
            trans.setdefault("params", {})["erase"] = False
            current_mobile.append(trans)
            draw_strokes.append(trans)

        frame_k_steps.extend(erase_strokes)
        frame_k_steps.extend(draw_strokes)

        # Step D: Strictly balance strokes so stroke_count == target_budget!
        frame_k_steps = enforce_stroke_parity(
            frame_k_steps,
            target_count=target_budget,
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

    return frames


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

    frames = build_animation_frames(
        base_steps=base_steps,
        prompt=prompt,
        num_frames=num_frames,
        stroke_budget=stroke_budget,
        width=width,
        height=height,
    )

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
        "strokes_per_frame": frames[0]["stroke_count"] if frames else stroke_budget,
        "frames": frames,
        "steps": frames[0]["steps"],
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
    try:
        base_plan, source = plan_artwork(prompt, config, width, height, images=images)
        base_steps = [normalize_step(s, width, height) for s in base_plan.get("steps", [])]
        base_strokes = [s for s in base_steps if (s.get("cmd") or s.get("id")) == "paint.stroke"]
        stroke_budget = len(base_strokes)
        if stroke_budget == 0:
            stroke_budget = max(10, config.detail_level * 10)

        frames = build_animation_frames(
            base_steps=base_steps,
            prompt=prompt,
            num_frames=num_frames,
            stroke_budget=stroke_budget,
            width=width,
            height=height,
        )

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
            "strokes_per_frame": frames[0]["stroke_count"] if frames else stroke_budget,
            "frames": frames,
        }
        return plan, f"{source}+animator"

    except Exception as e:
        logger.warning("Error composing LLM animation plan: %s. Using procedural animation fallback.", e)
        fallback = plan_animation_fallback(prompt, config, width, height)
        return fallback, "procedural-animator"


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

    # If current_count < target_count, add interior fill reinforcement strokes underneath outlines
    needed = target_count - current_count
    existing_strokes = [
        (idx, s) for idx, s in enumerate(result)
        if (s.get("cmd") or s.get("id")) == "paint.stroke" and not s.get("params", {}).get("erase")
    ]
    ref_pts = [[400.0, 400.0, 1.0], [402.0, 402.0, 1.0]]
    ref_col = default_color
    insert_pos = len(result)

    if existing_strokes:
        # Prefer a solid interior base fill stroke (size >= 12 or 'fill'/'solid'/'core' in name)
        fill_candidates = [
            (idx, s) for idx, s in existing_strokes
            if (
                float(s.get("params", {}).get("size") or 0.0) >= 12.0
                or any(k in str(s.get("params", {}).get("name") or "").lower() for k in ("fill", "solid", "core", "base", "wash"))
            )
            and not any(k in str(s.get("params", {}).get("name") or "").lower() for k in ("shadow", "cast", "ink", "outline"))
        ]
        chosen_idx, chosen_stroke = fill_candidates[0] if fill_candidates else existing_strokes[0]
        insert_pos = chosen_idx + 1
        c_params = chosen_stroke.get("params", {})
        pts = c_params.get("points")
        if pts and isinstance(pts, list) and len(pts) >= 2:
            ref_pts = pts
        ref_col = c_params.get("color") or default_color

    cx_fill = sum(float(pt[0]) for pt in ref_pts) / len(ref_pts)
    cy_fill = sum(float(pt[1]) for pt in ref_pts) / len(ref_pts)
    cx_fill = max(10.0, min(float(canvas_w - 10), cx_fill))
    cy_fill = max(10.0, min(float(canvas_h - 10), cy_fill))

    padding_strokes: list[dict[str, Any]] = []
    for i in range(needed):
        micro_stroke = {
            "cmd": "paint.stroke",
            "params": {
                "name": f"Interior Solid Fill Reinforcement {i + 1}",
                "points": [[round(cx_fill, 1), round(cy_fill, 1), 1.0], [round(cx_fill + 1.0, 1), round(cy_fill + 0.5, 1), 1.0]],
                "size": 8.0,
                "color": ref_col,
                "hardness": 0.95,
                "opacity": 1.0,
                "erase": False,
            },
        }
        padding_strokes.append(micro_stroke)

    result[insert_pos:insert_pos] = padding_strokes
    return result


BACKGROUND_KEYWORDS = (
    "background", "bg", "ground", "floor", "horizon", "sky", "cloud", "cumulus",
    "sun", "sunbeam", "sunlight", "solar", "moon", "star", "backdrop", "surface",
    "table", "road", "street", "path", "trail", "platform", "court", "field",
    "meadow", "pasture", "prairie", "lawn", "turf", "grass", "blade", "tuft",
    "clover", "weed", "reed", "flower", "daisy", "dandelion", "blossom", "petal",
    "wildflower", "flora", "plant", "stem", "leaf", "leaves", "foliage", "bush",
    "shrub", "hedge", "tree", "trunk", "branch", "canopy", "forest", "woods",
    "hill", "hillside", "knoll", "mound", "slope", "ridge", "mountain", "peak",
    "valley", "landscape", "scenery", "environment", "setting", "atmosphere",
    "distant", "far", "water", "pond", "lake", "river", "stream", "ocean", "sea",
    "wave", "ripple", "foam", "shimmer", "bubble", "wall", "room", "fence",
    "baseline", "shadow on ground",
)

CHARACTER_KEYWORDS = (
    "rabbit", "bunny", "hare", "character", "subject", "hero", "animal",
    "creature", "person", "human", "figure", "body", "torso", "belly", "chest",
    "back", "rump", "haunch", "head", "face", "skull", "cheek", "jaw", "chin",
    "snout", "muzzle", "nose", "nostril", "ear", "inner ear", "eye", "pupil",
    "iris", "lid", "lash", "brow", "mouth", "lip", "smile", "tooth", "teeth",
    "whisker", "leg", "thigh", "hind", "foreleg", "foot", "feet", "paw", "toe",
    "hoof", "arm", "hand", "wing", "tail", "cotton", "pelage", "fur", "ball",
    "sphere", "orb", "duck", "bill", "beak", "feather", "plumage", "cat", "dog",
    "bear", "teddy", "kangaroo", "frog", "deer", "moose", "antler", "car",
    "wheel", "tire", "windshield", "chassis", "butterfly", "cast shadow",
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


def _stroke_bbox(stroke: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) for a single stroke."""
    return get_strokes_bounds([stroke])


def _is_background_stroke_name(name: str, layer_name: str = "") -> bool:
    """Return True if a stroke's name or layer name indicates stationary background scenery."""
    n = name.lower()
    ln = layer_name.lower()

    # Cast shadow directly under the character feet moves with the character
    if any(k in n for k in ("cast shadow", "under feet", "contact shadow", "rabbit", "bunny", "hare", "character", "ball", "duck", "bear", "kangaroo", "cat", "dog")):
        if not any(bg in n for bg in ("background", "sky", "hill", "meadow", "field", "cloud", "sun", "flower", "grass", "tree", "horizon")):
            return False

    if any(bg in n for bg in BACKGROUND_KEYWORDS):
        return True

    if any(bg in ln for bg in ("background", "scenery", "environment", "sky", "field", "meadow", "landscape", "setting", "horizon", "hill", "ground")):
        if not any(ck in ln for ck in ("character", "subject", "rabbit", "bunny", "ball", "duck", "bear", "figure", "person", "animal")):
            if not any(ck in n for ck in CHARACTER_KEYWORDS):
                return True

    return False


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
            "hop", "hopping", "drive", "driving", "chase", "chasing", "field", "meadow",
        )
    )

    stationary: list[dict[str, Any]] = []
    subject_strokes: list[dict[str, Any]] = []

    for s in strokes:
        name = str(s.get("params", {}).get("name", "")).lower()
        bx0, by0, bx1, by1 = _stroke_bbox(s)
        bw = bx1 - bx0
        # Full-width horizontal strokes (> 520px wide on 800px canvas) are ground/sky/hill lines
        is_wide_env = bw > 520.0 and not any(ck in name for ck in ("rabbit", "bunny", "ball", "character", "body", "head", "ear"))
        if _is_background_stroke_name(name) or is_wide_env:
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


def _contract_points_toward_centroid(
    pts: list[list[float]],
    scale: float,
    close_loop: bool = True,
) -> list[list[float]]:
    """Contract a sequence of points toward their centroid by `scale` (0..1)."""
    if not pts:
        return []
    cx = sum(float(p[0]) for p in pts) / len(pts)
    cy = sum(float(p[1]) for p in pts) / len(pts)
    contracted: list[list[float]] = []
    for p in pts:
        nx = round(cx + (float(p[0]) - cx) * scale, 1)
        ny = round(cy + (float(p[1]) - cy) * scale, 1)
        contracted.append([nx, ny, 1.0])
    if close_loop and len(contracted) >= 3:
        if math.hypot(contracted[0][0] - contracted[-1][0], contracted[0][1] - contracted[-1][1]) > 2.0:
            contracted.append([contracted[0][0], contracted[0][1], 1.0])
    return contracted


def _synthesize_interior_fill_strokes_from_contour(
    contour_pts: list[list[float]],
    fill_color: str,
    base_name: str,
) -> list[dict[str, Any]]:
    """Create 100% opaque inward-contracted fill strokes that completely fill inside `contour_pts`."""
    if len(contour_pts) < 3:
        return []
    xs = [float(p[0]) for p in contour_pts]
    ys = [float(p[1]) for p in contour_pts]
    bx0, bx1 = min(xs), max(xs)
    by0, by1 = min(ys), max(ys)
    bw = max(6.0, bx1 - bx0)
    bh = max(6.0, by1 - by0)
    short_dim = min(bw, bh)

    outer_pts = _contract_points_toward_centroid(contour_pts, scale=0.50, close_loop=True)
    inner_pts = _contract_points_toward_centroid(contour_pts, scale=0.18, close_loop=True)

    outer_size = round(max(10.0, min(80.0, short_dim * 0.46)), 1)
    inner_size = round(max(12.0, min(85.0, short_dim * 0.56)), 1)

    fills: list[dict[str, Any]] = [
        {
            "cmd": "paint.stroke",
            "params": {
                "name": f"{base_name} (Solid Outer Fill)",
                "points": outer_pts,
                "size": outer_size,
                "color": fill_color,
                "hardness": 0.98,
                "opacity": 1.0,
                "erase": False,
            },
        },
        {
            "cmd": "paint.stroke",
            "params": {
                "name": f"{base_name} (Solid Core Fill)",
                "points": inner_pts,
                "size": inner_size,
                "color": fill_color,
                "hardness": 1.0,
                "opacity": 1.0,
                "erase": False,
            },
        },
    ]
    return fills


def _convert_step_to_strokes(
    step: dict[str, Any],
    prev_stroke: dict[str, Any] | None,
    canvas_w: int = 800,
    canvas_h: int = 800,
) -> list[dict[str, Any]]:
    """Convert `shape.create` or `paint.bucket` into opaque `paint.stroke` commands so they animate across all frames."""
    cmd = str(step.get("cmd") or step.get("id") or "").strip()
    params = step.get("params") or {}

    if cmd == "paint.stroke":
        return [step]

    if cmd == "shape.create":
        rect = params.get("rect") or [200.0, 200.0, 120.0, 100.0]
        rx, ry = float(rect[0]), float(rect[1])
        rw, rh = max(8.0, float(rect[2])), max(8.0, float(rect[3]))
        cx, cy = rx + rw * 0.5, ry + rh * 0.5
        name = str(params.get("name") or "Shape")
        fill_col = params.get("fill") or params.get("color")
        stroke_info = params.get("stroke")
        out: list[dict[str, Any]] = []

        oval_pts = stroke_enclosed_oval(cx, cy, rw * 0.5, rh * 0.5)
        if fill_col and str(fill_col).lower() not in ("none", "null", "transparent"):
            out.extend(_synthesize_interior_fill_strokes_from_contour(oval_pts, str(fill_col), f"{name} Solid Fill"))

        if stroke_info:
            s_col = stroke_info.get("color", "#111116") if isinstance(stroke_info, dict) else str(stroke_info)
            s_w = float(stroke_info.get("width", 4.0)) if isinstance(stroke_info, dict) else 4.0
            out.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"{name} Outline",
                    "points": oval_pts,
                    "size": max(2.5, s_w),
                    "color": s_col,
                    "hardness": 1.0,
                    "opacity": 1.0,
                    "erase": False,
                },
            })
        return out

    if cmd == "paint.bucket":
        fill_col = str(params.get("color") or "#ffffff")
        name = str(params.get("name") or "Solid Fill")
        bx = float(params.get("x", canvas_w * 0.5))
        by = float(params.get("y", canvas_h * 0.5))

        if prev_stroke is not None:
            pts = prev_stroke.get("params", {}).get("points") or []
            sx0, sy0, sx1, sy1 = _stroke_bbox(prev_stroke)
            sw = sx1 - sx0
            sh = sy1 - sy0
            if len(pts) >= 3 and sw < canvas_w * 0.75 and sh < canvas_h * 0.75:
                return _synthesize_interior_fill_strokes_from_contour(pts, fill_col, name)

        # If it's a background region bucket fill (sky or ground/field), create broad horizontal wash strokes
        if _is_background_stroke_name(name):
            y_start = max(40.0, by - 90.0)
            y_end = min(float(canvas_h - 40), by + 90.0)
            return [
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": f"Background {name} Sweep 1",
                        "points": stroke_line(0.0, y_start, float(canvas_w), y_start, steps=16),
                        "size": 140.0,
                        "color": fill_col,
                        "hardness": 0.95,
                        "opacity": 1.0,
                        "erase": False,
                    },
                },
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": f"Background {name} Sweep 2",
                        "points": stroke_line(0.0, y_end, float(canvas_w), y_end, steps=16),
                        "size": 140.0,
                        "color": fill_col,
                        "hardness": 0.95,
                        "opacity": 1.0,
                        "erase": False,
                    },
                },
            ]

    return []


def _infer_character_base_color(prompt: str, strokes: list[dict[str, Any]]) -> str:
    """Infer the primary solid fill color for the animated character."""
    p = prompt.lower()
    if "white" in p or any(k in p for k in ("rabbit", "bunny", "hare", "polar bear", "swan", "sheep", "lamb", "snowman", "ghost")):
        if "brown" in p:
            return "#d2996c"
        if "gray" in p or "grey" in p:
            return "#cbd5e1"
        if "pink" in p:
            return "#ffc2d1"
        return "#ffffff"
    if any(k in p for k in ("yellow", "duck", "rubber duck", "pikachu", "chick", "canary", "lemon", "bee")):
        return "#ffd700"
    if any(k in p for k in ("brown", "teddy", "bear", "kangaroo", "moose", "deer", "squirrel", "monkey", "dog", "puppy", "horse")):
        return "#c68642"
    if any(k in p for k in ("red", "apple", "ladybug", "crab", "lobster", "fire")):
        return "#e74c3c"
    if any(k in p for k in ("green", "frog", "toad", "turtle", "lizard", "alligator", "dinosaur", "alien")):
        return "#2ecc71"
    if any(k in p for k in ("orange", "fox", "tiger", "goldfish", "cat", "kitten", "basketball", "carrot")):
        return "#f39c12"
    if any(k in p for k in ("pink", "pig", "piglet", "flamingo", "kirby")):
        return "#ffb6c1"
    if any(k in p for k in ("blue", "whale", "dolphin", "bluebird", "smurf", "sonic")):
        return "#3498db"
    if any(k in p for k in ("gray", "grey", "elephant", "rhino", "hippo", "mouse", "rat", "koala", "wolf")):
        return "#cbd5e1"

    # Otherwise check existing thick fill strokes on the character
    for s in strokes:
        sp = s.get("params", {})
        col = str(sp.get("color") or "").lower()
        sz = float(sp.get("size") or 5.0)
        if sz >= 16.0 and col not in ("#000000", "#111111", "#111116", "#1a1a1a", "#2c3e50", ""):
            return col
    return "#ffffff"


def _stroke_cel_z_tier(stroke: dict[str, Any]) -> int:
    """Return strict Cel Z-Order tier (0=ground shadow, 1=base fill, 2=secondary fill/shade, 3=ink outline, 4=facial features)."""
    p = stroke.get("params", {})
    name = str(p.get("name") or "").lower()
    col = str(p.get("color") or "").lower()
    size = float(p.get("size") or 6.0)

    if any(k in name for k in ("cast shadow", "under feet", "ground shadow", "contact shadow")):
        return 0

    if any(k in name for k in (
        "eye", "pupil", "iris", "catchlight", "sparkle", "glint", "nose", "nostril",
        "mouth", "smile", "lip", "whisker", "cheek blush", "rosy cheek", "brow", "eyebrow", "tooth",
    )):
        return 4

    is_dark_ink = col in ("#000000", "#111111", "#111116", "#181512", "#1a1a1a", "#1c2833", "#212121", "#2c3e50", "#374151")
    if any(k in name for k in ("ink", "outline", "contour", "perimeter", "boundary")) or (is_dark_ink and size <= 9.0):
        return 3

    if any(k in name for k in ("inner ear", "pink", "cel shadow", "shade", "shading", "underside", "shadow")):
        return 2

    if any(k in name for k in ("fill", "solid", "flat", "wash", "base", "core")):
        return 1

    if size >= 16.0:
        return 1

    return 2


def ensure_character_solid_fills(
    mobile_strokes: list[dict[str, Any]],
    prompt: str,
    style: str = "cartoon",
) -> list[dict[str, Any]]:
    """Ensure the animated character is 100% colored in on every cel with strict back-to-front Z-ordering.

    Synthesizes opaque interior fill strokes for any hollow character contours (body, head, ears, legs, tail)
    and orders strokes: Cast Shadow (0) -> Solid Base Fills (1) -> Secondary Fills/Shading (2)
    -> Crisp Ink Outlines (3) -> Facial Features (4).
    """
    if not mobile_strokes or str(style).lower() in ("pencil", "sketchy"):
        return mobile_strokes

    base_color = _infer_character_base_color(prompt, mobile_strokes)
    inner_ear_color = "#ffb6c1"

    # Identify existing opaque interior fills (explicit fill strokes or thick Tier 1 base strokes)
    existing_fills = [
        s for s in mobile_strokes
        if (
            float(s.get("params", {}).get("size") or 0.0) >= 12.0
            or any(k in str(s.get("params", {}).get("name") or "").lower() for k in ("fill", "solid", "core", "flat", "wash"))
        )
        and float(s.get("params", {}).get("opacity") or 1.0) >= 0.85
        and _stroke_cel_z_tier(s) in (1, 2)
    ]

    synthesized_fills: list[dict[str, Any]] = []
    body_pts: list[list[float]] = []
    head_pts: list[list[float]] = []

    for s in mobile_strokes:
        p = s.get("params", {})
        name = str(p.get("name") or "")
        n_low = name.lower()
        pts = p.get("points") or []
        if len(pts) < 3:
            continue

        # Skip facial features, whiskers, and cast shadows
        if _stroke_cel_z_tier(s) in (0, 4):
            continue

        bx0, by0, bx1, by1 = _stroke_bbox(s)
        bw, bh = bx1 - bx0, by1 - by0

        if any(k in n_low for k in ("body", "torso", "belly", "back", "rump", "chest", "haunch")):
            body_pts.extend(pts)
        elif any(k in n_low for k in ("head", "cheek", "skull", "face", "jaw")):
            head_pts.extend(pts)

        # If this stroke is a character contour/outline or hollow part loop with substantial area
        is_part_contour = (
            _stroke_cel_z_tier(s) == 3
            or (
                _stroke_cel_z_tier(s) not in (1, 2)
                and any(k in n_low for k in ("ear", "tail", "leg", "thigh", "foot", "paw", "head", "body", "torso", "outline", "contour"))
            )
        )
        if is_part_contour and bw >= 14.0 and bh >= 14.0:
            cx, cy = (bx0 + bx1) * 0.5, (by0 + by1) * 0.5
            # Check if an existing fill already covers (cx, cy)
            covered = False
            for ef in existing_fills:
                ex0, ey0, ex1, ey1 = _stroke_bbox(ef)
                esz = float(ef.get("params", {}).get("size") or 16.0) * 0.65
                if (ex0 - esz) <= cx <= (ex1 + esz) and (ey0 - esz) <= cy <= (ey1 + esz):
                    covered = True
                    break
            if not covered:
                f_col = inner_ear_color if "inner ear" in n_low else base_color
                synthesized_fills.extend(
                    _synthesize_interior_fill_strokes_from_contour(pts, f_col, f"{name} Auto-Fill")
                )

    # Also ensure the combined body region and head region have solid core fills if drawn with open arcs
    for group_name, g_pts in (("Character Body", body_pts), ("Character Head", head_pts)):
        if len(g_pts) >= 4:
            gx0 = min(float(pt[0]) for pt in g_pts)
            gx1 = max(float(pt[0]) for pt in g_pts)
            gy0 = min(float(pt[1]) for pt in g_pts)
            gy1 = max(float(pt[1]) for pt in g_pts)
            gw, gh = gx1 - gx0, gy1 - gy0
            gcx, gcy = (gx0 + gx1) * 0.5, (gy0 + gy1) * 0.5
            if gw >= 24.0 and gh >= 24.0:
                covered = False
                for ef in existing_fills + synthesized_fills:
                    ex0, ey0, ex1, ey1 = _stroke_bbox(ef)
                    if ex0 <= gcx <= ex1 and ey0 <= gcy <= ey1 and float(ef.get("params", {}).get("size") or 0) >= 22.0:
                        covered = True
                        break
                if not covered:
                    oval = stroke_enclosed_oval(gcx, gcy, gw * 0.42, gh * 0.42)
                    synthesized_fills.extend(
                        _synthesize_interior_fill_strokes_from_contour(oval, base_color, group_name)
                    )

    combined = synthesized_fills + list(mobile_strokes)

    # Ensure all Tier 1 & Tier 2 fills in cartoon style have full opacity so background never bleeds through
    if str(style).lower() == "cartoon":
        for s in combined:
            tier = _stroke_cel_z_tier(s)
            if tier in (1, 2, 3, 4):
                s.setdefault("params", {})["opacity"] = 1.0
                if tier in (1, 3):
                    s["params"]["hardness"] = max(0.95, float(s["params"].get("hardness") or 0.98))

    # Stable sort by Cel Z-Order tier (0 -> 1 -> 2 -> 3 -> 4)
    combined_with_idx = [( _stroke_cel_z_tier(s), idx, s ) for idx, s in enumerate(combined)]
    combined_with_idx.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in combined_with_idx]


def split_background_and_character_steps(
    base_steps: list[dict[str, Any]],
    prompt: str,
    width: int = 800,
    height: int = 800,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split Frame 1 steps into stationary `background_steps` (drawn once on Background)
    and mobile `character_strokes` (drawn on each cel Frame 1..N).
    """
    current_layer = ""
    tagged_strokes: list[tuple[str, dict[str, Any]]] = []
    prev_stroke: dict[str, Any] | None = None

    for step in base_steps:
        cmd = str(step.get("cmd") or step.get("id") or "").strip()
        if cmd == "layer.new.layer":
            current_layer = str(step.get("params", {}).get("name") or "")
            continue
        converted = _convert_step_to_strokes(step, prev_stroke, canvas_w=width, canvas_h=height)
        for cs in converted:
            if (cs.get("cmd") or cs.get("id")) == "paint.stroke":
                if prev_stroke is not None and cmd == "paint.bucket" and tagged_strokes:
                    # Insert bucket fill strokes right before the outline stroke they fill
                    last_layer, last_st = tagged_strokes.pop()
                    tagged_strokes.append((current_layer, cs))
                    tagged_strokes.append((last_layer, last_st))
                else:
                    tagged_strokes.append((current_layer, cs))
                prev_stroke = cs

    if not tagged_strokes:
        return [], []

    prompt_lower = str(prompt or "").lower()
    is_locomotion = any(
        kw in prompt_lower
        for kw in (
            "across", "bounce", "bouncing", "ball", "walk", "walking", "run", "running",
            "fly", "flying", "jump", "jumping", "swim", "swimming", "roll", "rolling",
            "travel", "move", "moving", "slide", "sliding", "glide", "gliding",
            "hop", "hopping", "drive", "driving", "chase", "chasing", "field", "meadow",
        )
    )

    bg_strokes: list[dict[str, Any]] = []
    char_candidates: list[dict[str, Any]] = []

    for layer_name, s in tagged_strokes:
        name = str(s.get("params", {}).get("name") or "")
        bx0, by0, bx1, by1 = _stroke_bbox(s)
        bw = bx1 - bx0

        # 1. Explicit background name/layer or full-width horizontal sweep (> 55% of canvas width)
        is_wide_scene = bw > float(width) * 0.55 and not any(
            ck in name.lower() for ck in ("rabbit", "bunny", "ball", "character", "body", "head", "ear")
        )
        if _is_background_stroke_name(name, layer_name) or is_wide_scene:
            bg_strokes.append(s)
        else:
            char_candidates.append(s)

    if not char_candidates:
        # If everything was classified as background, fallback to extract_mobile_feature_strokes
        all_only = [s for _, s in tagged_strokes]
        mobile, stationary = extract_mobile_feature_strokes(all_only, prompt)
        return stationary, mobile

    # 2. Spatial clustering check: find the bounding box of explicit character strokes
    explicit_char = [
        s for s in char_candidates
        if any(ck in str(s.get("params", {}).get("name") or "").lower() for ck in CHARACTER_KEYWORDS)
    ]
    if explicit_char:
        cx0, cy0, cx1, cy1 = get_strokes_bounds(explicit_char)
        pad = 65.0
        final_char: list[dict[str, Any]] = []
        for s in char_candidates:
            sx0, sy0, sx1, sy1 = _stroke_bbox(s)
            scx, scy = (sx0 + sx1) * 0.5, (sy0 + sy1) * 0.5
            sname = str(s.get("params", {}).get("name") or "").lower()
            # If a stroke is far outside the character's bounding box, check if it's scenery or a stray shape
            if not ((cx0 - pad) <= scx <= (cx1 + pad) and (cy0 - pad) <= scy <= (cy1 + pad)):
                if any(ck in sname for ck in ("rabbit", "bunny", "body", "head", "ear", "ellipse", "oval", "rect")):
                    # Stray misplaced character shape (e.g. LLM put a white ellipse at x=400 while rabbit is at x=220):
                    # Drop the misaligned shape so ensure_character_solid_fills synthesizes aligned fills!
                    continue
                bg_strokes.append(s)
            else:
                final_char.append(s)
        if final_char:
            char_candidates = final_char

    if not is_locomotion:
        mobile, stationary = extract_mobile_feature_strokes(char_candidates, prompt)
        return bg_strokes + stationary, mobile

    return bg_strokes, char_candidates


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
    """Create erase strokes that 100% clear the previous frame's character on the transparent cel layer.

    Because the stationary background is drawn on the separate `Background` layer underneath,
    full-bounding-box `erase: True` sweeps on `Frame k` cleanly reset `Frame k` to transparent
    with zero ghosting while leaving `Background` completely untouched.
    """
    if not prev_mobile_strokes:
        return []

    min_x, min_y, max_x, max_y = get_strokes_bounds(prev_mobile_strokes)
    pad = 45.0
    x0 = max(0.0, round(min_x - pad, 1))
    x1 = min(800.0, round(max_x + pad, 1))
    y0 = max(0.0, round(min_y - pad, 1))
    y1 = min(800.0, round(max_y + pad, 1))
    bh = max(60.0, y1 - y0)

    count = max(2, min(max_erase_count, 4))
    band_h = bh / float(count)
    brush_size = round(min(300.0, max(160.0, band_h * 1.85)), 1)

    erases: list[dict[str, Any]] = []
    for i in range(count):
        yc = round(y0 + (i + 0.5) * band_h, 1)
        pts = stroke_line(x0, yc, x1, yc, steps=12)
        erases.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Erase Previous Cel Band {i + 1}",
                "points": pts,
                "size": brush_size,
                "color": "#ffffff",
                "hardness": 1.0,
                "opacity": 1.0,
                "erase": True,
            },
        })

    return erases


def build_animation_frames(
    base_steps: list[dict[str, Any]],
    prompt: str,
    num_frames: int,
    stroke_budget: int,
    width: int = 800,
    height: int = 800,
    style: str = "cartoon",
) -> list[dict[str, Any]]:
    """Generate multi-frame cel animation layers with stationary background separation and solid character fills."""
    background_steps, mobile_strokes = split_background_and_character_steps(
        base_steps, prompt, width=width, height=height
    )
    if not mobile_strokes:
        base_strokes = [s for s in base_steps if (s.get("cmd") or s.get("id")) == "paint.stroke"]
        mobile_strokes, background_steps = extract_mobile_feature_strokes(base_strokes, prompt)
        if not mobile_strokes:
            mobile_strokes = list(base_strokes)

    # Ensure the character is 100% colored in with solid opaque fills and proper Cel Z-Order on every frame
    mobile_strokes = ensure_character_solid_fills(mobile_strokes, prompt, style=style)

    prompt_lower = prompt.lower()
    is_across = any(
        kw in prompt_lower
        for kw in ("across", "screen", "cross", "traverse", "left to right", "through", "field", "meadow")
    )
    is_bounce = any(kw in prompt_lower for kw in ("bounce", "bouncing", "ball", "hop", "hopping", "rebound", "rabbit", "bunny", "hare", "kangaroo", "frog"))
    is_walk = any(kw in prompt_lower for kw in ("walk", "walking", "run", "running", "step", "stride"))
    is_blink = any(kw in prompt_lower for kw in ("blink", "blinking", "eye", "wink"))
    is_wave = any(kw in prompt_lower for kw in ("wave", "waving", "wing", "hand", "arm", "tail"))
    is_animal_character = any(kw in prompt_lower for kw in ("rabbit", "bunny", "hare", "kangaroo", "frog", "cat", "dog", "bear", "teddy", "duck"))

    # If moving across the screen/field and the LLM placed the character near the center,
    # position Frame 1 at the left starting side (cx ~ 170) so it hops cleanly across the entire field!
    if num_frames > 1 and is_across and mobile_strokes:
        m_x0, m_y0, m_x1, m_y1 = get_strokes_bounds(mobile_strokes)
        init_cx = (m_x0 + m_x1) * 0.5
        if 250.0 < init_cx < 550.0:
            shift_left = round(170.0 - init_cx, 1)
            mobile_strokes = [
                apply_motion_transform(ms, dx=shift_left, dy=0.0)
                for ms in mobile_strokes
            ]

    num_mobile = len(mobile_strokes)
    num_erase = min(4, max(2, num_mobile // 8)) if num_frames > 1 else 0
    target_budget = max(stroke_budget, num_mobile + num_erase)

    # Frame 1 contains ONLY the character cel steps (background_steps are stored separately and drawn onto Background)
    frame_1_steps = enforce_stroke_parity(list(mobile_strokes), target_budget, width, height)
    frames: list[dict[str, Any]] = [
        {
            "frame_index": 1,
            "name": "Frame 1",
            "is_base": True,
            "steps": frame_1_steps,
            "background_steps": background_steps,
            "stroke_count": count_brush_strokes(frame_1_steps),
        }
    ]

    if num_frames <= 1:
        return frames

    min_x, min_y, max_x, max_y = get_strokes_bounds(mobile_strokes)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    bottom_y = max_y

    # Determine across-screen horizontal travel distance
    max_travel = min(500.0, 44.0 * float(num_frames - 1))
    if cx < 400.0:
        total_dx = min(max_travel, max(150.0, (float(width) - 120.0) - cx))
    else:
        total_dx = -min(max_travel, max(150.0, cx - 120.0))

    prev_mobile = copy.deepcopy(mobile_strokes)

    for k in range(2, num_frames + 1):
        t = float(k - 1) / float(num_frames - 1)
        theta = 2.0 * math.pi * float(k - 1) / float(num_frames)

        if is_bounce and is_across:
            # Trajectory across screen with smooth bounce/hop arcs
            dx = round(t * total_dx, 1)
            num_bounces = 2 if num_frames <= 12 else 3
            bounce_height = min(95.0 if is_animal_character else 120.0, max(55.0, bottom_y - 120.0))
            bounce_arc = abs(math.sin(math.pi * float(num_bounces) * t))
            dy = -round(bounce_height * bounce_arc, 1)

            # Squash & stretch: subtle for animal characters, pronounced for rubber balls
            cycle = t * float(num_bounces)
            tau = cycle - math.floor(cycle)
            if tau < 0.12 or tau > 0.88:
                squash_y = 0.88 if is_animal_character else 0.72
                squash_x = 1.10 if is_animal_character else 1.25
                orig_y = bottom_y
            elif 0.18 <= tau <= 0.35 or 0.65 <= tau <= 0.82:
                squash_y = 1.08 if is_animal_character else 1.15
                squash_x = 0.94 if is_animal_character else 0.90
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
                squash_y = 0.86 if is_animal_character else 0.72
                squash_x = 1.12 if is_animal_character else 1.25
                orig_y = bottom_y
            else:
                squash_y = 1.06 if is_animal_character else 1.10
                squash_x = 0.96 if is_animal_character else 0.95
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

        # Step B: Erase previous frame's mobile positions cleanly on the cel layer
        erase_strokes = create_erase_strokes_covering(prev_mobile, max_erase_count=num_erase)

        # Step C: Redraw character elements at new displaced coordinates in strict Cel Z-Order
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
        style=style,
    )

    title = base_plan.get("title", prompt)
    clean_title = re.sub(r"\[\d+\s*Frames?\]", "", title, flags=re.IGNORECASE).strip()
    formatted_title = f"{clean_title} [{num_frames} Frames]"
    bg_steps = frames[0].get("background_steps", []) if frames else []

    return {
        "title": formatted_title,
        "width": width,
        "height": height,
        "background": base_plan.get("background", "white"),
        "is_animation": True,
        "frames_count": num_frames,
        "strokes_per_frame": frames[0]["stroke_count"] if frames else stroke_budget,
        "background_steps": bg_steps,
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
            style=config.style,
        )

        title = base_plan.get("title", prompt)
        clean_title = re.sub(r"\[\d+\s*Frames?\]", "", title, flags=re.IGNORECASE).strip()
        formatted_title = f"{clean_title} [{num_frames} Frames]"
        bg_steps = frames[0].get("background_steps", []) if frames else []

        plan = {
            "title": formatted_title,
            "width": width,
            "height": height,
            "background": base_plan.get("background", "white"),
            "is_animation": True,
            "frames_count": num_frames,
            "strokes_per_frame": frames[0]["stroke_count"] if frames else stroke_budget,
            "background_steps": bg_steps,
            "frames": frames,
        }
        return plan, f"{source}+animator"

    except Exception as e:
        logger.warning("Error composing LLM animation plan: %s. Using procedural animation fallback.", e)
        fallback = plan_animation_fallback(prompt, config, width, height)
        return fallback, "procedural-animator"


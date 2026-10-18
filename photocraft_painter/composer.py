"""Composition engine that translates user prompts into PhotoCraft drawing commands."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from photocraft_painter.fallback_composer import (
    format_document_title,
    is_portrait_or_face_prompt,
    parse_geometric_shape_prompt,
    plan_fallback,
    plan_painterly_geometric_shape,
    plan_painterly_portrait,
    plan_refinement_fallback,
)
from photocraft_painter.strokes import (
    smooth_path,
    stroke_enclosed_loop,
    stroke_enclosed_oval,
    stroke_enclosed_rect,
    stroke_line,
    stroke_polygon,
    stroke_regular_polygon_vertices,
    stroke_triangle,
)
from photocraft_painter.styles import STYLE_PRESETS, get_style

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a master artist, painter, and illustrator for PhotoCraft, a native graphic design and painting application.
Your goal is to plan and generate drawing commands that recreate an authentic human artist drawing the user's prompt on a digital canvas.
Keep your internal reasoning very short and concise (under 150 words). Immediately output the JSON illustration plan.

CRITICAL DEPTH & LAYER ORDERING (STRICT BACK-TO-FRONT / Z-ORDER):
Digital drawing renders strokes in sequential order. Elements behind must ALWAYS be drawn BEFORE elements in front!
An artist works in strict depth layers:
1. "1. Background & Atmosphere": Sky, environment, room, setting wash drawn FIRST.
2. "2. Rear Elements & Back Hair": Anything physically BEHIND the subject.
   - For portraits/figures: draw the rear hair volume, back flowing tresses, and backdrop silhouettes.
3. "3. Body, Torso & Clothes": Shoulders, neck, collar, clothing, drapery.
4. "4. Head & Face Base (Skin Flat)":
   - Head oval and jawline drawn as a completely enclosed contour, then IMMEDIATELY filled with `paint.bucket` in the skin tone ("sampleAllLayers": true).
   - CRITICAL: This opaque skin base cleanly covers any background lines and rear hair passing behind the head!
5. "5. Facial Features & Anatomical Modeling":
   - Drawn ON TOP of the clean face skin flat.
   - Eyes: upper & lower eyelid contours, colored iris, dark pupil, white catchlight dot.
   - Eyebrows: arched hair strokes matching the gaze and expression.
   - Nose: subtle shaded nose bridge line and small nostril curves.
   - Mouth: upper lip with cupid's bow, lower lip curve, center mouth parting line, natural rosy tone.
   - Soft cheek blush, jawline shading, and facial depth modeling.
6. "6. Foreground Framing Hair & Accents":
   - ONLY draw hair locks or elements that sit physically IN FRONT of the shoulders or gently frame the outer cheeks.
   - STRICT FORBIDDEN RULE: NEVER draw horizontal hair strokes, texture sweeps, or hatching across the eyes, nose, or mouth! The face must remain clean, legible, and completely unobstructed!
7. "7. Specular Highlights & Glints":
   - White eye pupil catchlights, lip gloss gleams, nose tip glint, and lustrous hair sheen accents.

Output strictly valid JSON matching this schema:
{
  "title": "Illustration Title",
  "background": "#f8f9fa",
  "steps": [
    {
      "cmd": "layer.new.layer",
      "params": {
        "name": "1. Pencil Sketch"
      }
    },
    {
      "cmd": "paint.stroke",
      "params": {
        "name": "Sketch: Head Gesture",
        "points": [[200, 300], [250, 260], [350, 260], [400, 300]],
        "size": 3.0,
        "color": "#7f8c8d",
        "hardness": 0.8
      }
    },
    {
      "cmd": "layer.new.layer",
      "params": {
        "name": "2. Base Color Flats"
      }
    },
    {
      "cmd": "paint.stroke",
      "params": {
        "name": "Head Bounding Outline (Enclosed)",
        "points": [[200, 200], [400, 200], [400, 400], [200, 400], [200, 200]],
        "size": 5.0,
        "color": "#111111",
        "hardness": 0.95
      }
    },
    {
      "cmd": "paint.bucket",
      "params": {
        "name": "Head Yellow Base Fill",
        "x": 300,
        "y": 300,
        "color": "#ffd700",
        "sampleAllLayers": true
      }
    }
  ]
}

COMMAND OPTIONS:
1. "paint.stroke": Hand-drawn brush strokes with a sequence of coordinate points.
   - "points": [[x0, y0], [x1, y1], [x2, y2], ...] (continuous stroke trajectory)
   - "size": brush diameter in pixels (2-5 for pencil/sketch/ink lines, 15-30 for shading, 40-80 for broad painterly sweeps)
   - "color": hex string (e.g. "#1c2833", "#ffd700", "#ffffff")
   - "hardness": 0.0 to 1.0 (0.5 for soft paint/watercolor, 0.9 for sharp pencil/ink lines)
   - "name": descriptive name for the stroke
2. "paint.bucket": Paint bucket / flood fill tool for filling enclosed areas cleanly.
   - "x": integer x coordinate seed point strictly inside the enclosed area
   - "y": integer y coordinate seed point strictly inside the enclosed area
   - "color": hex color string (e.g. "#ffd700", "#e74c3c")
   - "tolerance": integer 0-255 (default 32)
   - "sampleAllLayers": true (checks boundary lines from all layers)
   - "name": descriptive name for the fill
3. "layer.new.layer": Creates a new raster layer to organize the artwork.
   - "name": descriptive layer name (e.g. "Pencil Sketch", "Color Flats", "Shading", "Ink Outlines")
4. "shape.create": For backdrop blocks or clean shapes.
   - "kind": "ellipse", "rect", "roundedRect", "polygon", "star"
   - "rect": [x, y, width, height] (3rd and 4th values MUST be WIDTH and HEIGHT, NOT x2/y2!)
   - "fill": hex string or null

IMPORTANT BOUNDING BOX & PAINT BUCKET RULE:
When coloring in regions (such as a character's body, face, head, ears, clothing, or background objects), NEVER messily scribble back and forth with dozens of thick brush strokes!
Instead:
- First, draw a completely enclosed bounding outline with `paint.stroke` (e.g. a closed polygon or contour where the start and end points connect: points[0] == points[-1], size >= 4.0, hardness >= 0.9).
  WARNING: The bounding contour MUST be completely enclosed without any gaps, pinholes, or openings, otherwise the paint bucket will leak across the entire canvas!
- Immediately follow with `paint.bucket` on the SAME layer using a seed point (x, y) situated well inside the center of that enclosed area, with "sampleAllLayers": true.
- Organize distinct subjects and elements onto separate layers with `layer.new.layer` (e.g. background shapes first, character base next, details on top). Each layer is isolated during drawing (prior background layers are kept hidden) so background shapes will NEVER divide, cut through, or segment your paint bucket fills. Once drawing finishes, all layers are restored to visible simultaneously for the final artwork.
- After filling the clean solid flats, proceed to shading, highlights, and painterly details.

Canvas size is 800x800 pixels. Generate expressive steps according to the requested detail level.
Output ONLY the JSON object.
"""

PORTRAIT_PROMPT_INSTRUCTION = """
*** CRITICAL PORTRAIT & FACE DEPTH RULES (STRICT Z-ORDER) ***:
The artwork features a person, portrait, or human face. You MUST obey these depth and anatomical rules:
1. STRICT Z-ORDER (BACK-TO-FRONT):
   - Layer 1: Background & Atmosphere (sky, setting, canvas wash) MUST be drawn first.
   - Layer 2: Rear Hair & Backdrop Elements (hair volume and flowing tresses behind the head/shoulders) MUST be drawn in an early layer BEFORE the face.
   - Layer 3: Torso, Neck & Garments.
   - Layer 4: Head & Face Skin Base (draw a completely enclosed contour of the head/jaw and fill it with `paint.bucket` in skin tone, sampleAllLayers: true). This creates an opaque base that cleanly covers any background lines and rear hair underneath!
   - Layer 5: Facial Features (eyes, eyebrows, nose, mouth) MUST be drawn on top of the clean skin base.
   - Layer 6: Foreground Framing Tendrils (ONLY hair curls framing the outer cheeks or resting on shoulders).
   - Layer 7: Specular Highlights & Eye Catchlights.
2. ABSOLUTELY FORBIDDEN:
   - NEVER draw hair strokes, shading, or texture lines horizontally across the eyes, nose, or mouth! The face must remain pristine and unobstructed!
   - NEVER draw hair texture after the facial features unless it is purely framing the side contours!
3. HIGH FIDELITY FACIAL ANATOMY:
   - Replicate the subject's facial features with high fidelity:
     * Eyes: almond upper/lower eyelids, colored iris, dark pupil, white specular catchlight dots.
     * Eyebrows: graceful arches matching the expression.
     * Nose: sculpted bridge line and delicate nostril curves/shading.
     * Lips: defined upper lip with cupid's bow, mouth center line, fuller lower lip with natural tone.
   - Do NOT use crude scratches for the face. Allocate dedicated, distinct anatomical strokes for each feature.
"""

GEOMETRIC_PROMPT_INSTRUCTION = """
*** CRITICAL GEOMETRIC SHAPES & TRIANGLES RULES (STRICTLY NO GUM DROPS) ***:
The user prompt requests geometric shapes (e.g. triangle, square, polygon, hexagon). You MUST obey these shape rules:
1. A TRIANGLE IS AN EXACT 3-SIDED POLYGON:
   - It MUST have 3 sharp corners (vertices) and straight linear edges connecting them!
   - ABSOLUTELY FORBIDDEN: NEVER round the corners or bow the sides of a triangle! It must NEVER look like a rounded gum drop, bell, oval, or curved blob!
2. HOW TO DRAW A TRIANGLE WITH `paint.stroke`:
   - Define 3 sharp vertices [V0, V1, V2] forming straight edges. Example:
     Apex V0: [400, 150], Bottom-Right V1: [650, 600], Bottom-Left V2: [150, 600].
   - Close the loop by returning to the start point: [[400, 150], [650, 600], [150, 600], [400, 150]].
   - Set "size": 4.5-5.5, "hardness": 1.0, and "name": "Triangle Bounding Outline".
3. CLEAN INTERIOR COLOR FILL WITH `paint.bucket`:
   - Follow immediately with `paint.bucket` using the centroid point (e.g. x: 400, y: 450) inside the triangle, with "sampleAllLayers": true.
4. STYLE ADAPTATION (ESPECIALLY SKETCHY & CARTOON):
   - In "sketchy" style: include straight pencil drafting guide lines extending through each corner (corner overshoots) and directional diagonal facet cross-hatching.
   - In "cartoon" style: use bold, crisp, solid black ink outlines (size 5-6, hardness 1.0) and clean cel shading.
   - In "cubism" style: deconstruct into multi-perspective planar facets, intersecting diagonal ridge lines, and high-contrast volumetric facet lighting leaping off the canvas.
"""

ANIMATION_KEYFRAME_INSTRUCTION = """
*** CRITICAL ANIMATION RULE: SINGLE INITIAL SUBJECT ONLY (FRAME 1 AT t=0) ***
This drawing is strictly FRAME 1 (KEYFRAME AT t=0) of a multi-frame animation (steps > 1).
You MUST draw ONLY A SINGLE INSTANCE of the animated subject in its initial starting position / starting pose!
1. STRICTLY ONE SUBJECT:
   - Draw ONLY ONE ball, ONE character, ONE vehicle, or ONE creature in its starting pose at the beginning of the motion (on the left side of the canvas, e.g. x = 140..280, if moving across the screen).
   - For example, if the prompt is "a ball bouncing across the screen", draw ONLY ONE BALL (e.g. at the starting position on the left side or top-left) and an optional static ground/floor line.
   - For example, if the prompt is "a person walking across the screen", draw ONLY ONE PERSON at their starting stride on one side.
2. ABSOLUTELY FORBIDDEN:
   - NEVER draw multiple stages of the bounce, multiple positions along a trajectory, multiple exposures, or a motion sequence!
   - NEVER draw multiple balls, multiple duplicate characters, or a comic-strip progression across the canvas!
   - NEVER draw motion path arcs, dashed flight trajectory lines, or timing chart lines!
   - Drawing multiple stages in Frame 1 ruins the animation because subsequent frames duplicate and animate the entire layer. Frame 1 MUST depict only the single subject at the start of its movement.
3. STRICT CEL ANIMATION SEPARATION (STATIONARY BACKGROUND vs. SOLID CHARACTER CEL):
   - Layer 1 ("1. Background Environment"): Place ALL stationary background elements (sky, sun, clouds, hills, field, meadow, grass tufts, flowers, trees, ground line) on this first layer so the background is drawn ONCE and stays stationary!
   - Layer 2 ("2. Character Solid Color Fills"): Place the single animated character on its own layer. You MUST completely fill the interior of every character part (body, torso, head, ears, legs, paws, tail) using thick, 100% opaque `paint.stroke` sweeps (opacity: 1.0, hardness: 0.98, size: 24-55, e.g. "#ffffff" for a white rabbit, "#ffb6c1" for inner ears) BEFORE drawing ink outlines! Do NOT leave the character hollow or transparent, and do NOT use `shape.create` or `paint.bucket` for the animated character!
   - Layer 3 ("3. Character Cel Shading, Features & Ink Outlines"): Draw cel shading, eyes, dark pupils, white catchlights, nose, mouth, whiskers, and crisp black ink outlines ("#111116", size: 4-6, hardness: 1.0, opacity: 1.0) on top of the character's solid fills.
"""


def normalize_color(c: Any) -> str | None:
    """Normalize a color value into a valid #rrggbb hex string or None."""
    if c is None:
        return None
    if isinstance(c, str):
        c = c.strip()
        if c.lower() in ("none", "null", "transparent", ""):
            return None
        if re.match(r"^[0-9a-fA-F]{6}$", c):
            return f"#{c}"
        if re.match(r"^#[0-9a-fA-F]{6}$", c):
            return c
        if re.match(r"^#[0-9a-fA-F]{3}$", c):
            return f"#{c[1]*2}{c[2]*2}{c[3]*2}"
        return c
    return None


def normalize_step(step: dict[str, Any], canvas_w: int = 800, canvas_h: int = 800) -> dict[str, Any]:
    """Sanitize and normalize a drawing step into valid PhotoCraft command parameters."""
    cmd = str(step.get("cmd") or step.get("id") or "shape.create").strip()
    raw_params = dict(step.get("params") or {})

    # 1. Layer creation and duplication commands
    if cmd in ("layer.new.layer", "layer.new", "new.layer"):
        name = str(raw_params.get("name") or "Layer")
        return {"cmd": "layer.new.layer", "params": {"name": name}}
    if cmd in ("layer.duplicate", "layer.new.layerViaCopy", "layer.copy"):
        return {"cmd": "layer.duplicate", "params": raw_params}
    if cmd in ("layer.renameLayer", "layer.rename"):
        return {"cmd": "layer.renameLayer", "params": raw_params}
    if cmd in ("layer.setProps", "layer.props"):
        return {"cmd": "layer.setProps", "params": raw_params}

    # 2. Brush stroke command
    if cmd in ("paint.stroke", "brush.stroke", "stroke"):
        clean_params: dict[str, Any] = {}
        clean_params["name"] = str(raw_params.get("name") or "Brush Stroke")

        pts = raw_params.get("points")
        if isinstance(pts, list) and len(pts) >= 2:
            valid_pts: list[list[float]] = []
            for p in pts:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    px = max(-1000.0, min(2000.0, float(p[0])))
                    py = max(-1000.0, min(2000.0, float(p[1])))
                    pr = float(p[2]) if len(p) >= 3 else 0.8
                    valid_pts.append([round(px, 1), round(py, 1), round(pr, 2)])
            if len(valid_pts) < 2:
                valid_pts = [[100.0, 100.0, 0.5], [101.0, 101.0, 0.5]]
            elif len(valid_pts) <= 8:
                # Check if this stroke represents a closed polygon (e.g. triangle with 4 points, quad with 5 points, etc.)
                # or is marked with geometric / polygon / linear flags or names
                is_closed = (
                    len(valid_pts) >= 4
                    and math.hypot(valid_pts[0][0] - valid_pts[-1][0], valid_pts[0][1] - valid_pts[-1][1]) < 8.0
                )
                name_lower = str(raw_params.get("name") or "").lower()
                is_polygon_flag = (
                    bool(raw_params.get("polygon"))
                    or bool(raw_params.get("linear"))
                    or raw_params.get("shape") in ("polygon", "triangle", "poly", "rect")
                    or any(k in name_lower for k in ("triangle", "polygon", "poly", "sided", "geometric", "corner", "vertex", "prism", "pyramid", "delta", "rect", "square", "diamond", "hexagon", "pentagon", "octagon", "facet", "plane", "cubist", "cubism"))
                )

                if (is_closed or is_polygon_flag) and not raw_params.get("smooth"):
                    # Linearly interpolate polygon edges to preserve straight sides and sharp vertices!
                    # Strictly avoids Catmull-Rom spline which rounds triangles into gum drops.
                    valid_pts = stroke_polygon(valid_pts, wobble=0.0, steps_per_side=15, closed=is_closed)
                else:
                    # Interpolate coarse waypoints into smooth Catmull-Rom spline
                    valid_pts = smooth_path(valid_pts, samples_per_segment=6)
            clean_params["points"] = valid_pts
        else:
            clean_params["points"] = [[100.0, 100.0, 0.5], [101.0, 101.0, 0.5]]

        size = float(raw_params.get("size") or 6.0)
        clean_params["size"] = max(1.0, min(size, 300.0))

        color = normalize_color(raw_params.get("color") or raw_params.get("fill") or "#000000")
        clean_params["color"] = color or "#000000"

        if "hardness" in raw_params:
            clean_params["hardness"] = max(0.0, min(float(raw_params["hardness"]), 1.0))
        if "opacity" in raw_params:
            clean_params["opacity"] = max(0.0, min(float(raw_params["opacity"]), 1.0))
        if "erase" in raw_params:
            clean_params["erase"] = bool(raw_params["erase"])

        return {"cmd": "paint.stroke", "params": clean_params}

    # 3. Paint bucket / flood fill command
    if cmd in ("paint.bucket", "bucket", "fill.bucket", "flood.fill", "paint_bucket"):
        clean_params = {}
        clean_params["name"] = str(raw_params.get("name") or "Paint Bucket Fill")

        px = raw_params.get("x")
        py = raw_params.get("y")
        if px is None or py is None:
            pt = raw_params.get("point") or raw_params.get("seed")
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                px = pt[0]
                py = pt[1]
            else:
                rect = raw_params.get("rect")
                if isinstance(rect, (list, tuple)) and len(rect) >= 4:
                    px = float(rect[0]) + float(rect[2]) * 0.5
                    py = float(rect[1]) + float(rect[3]) * 0.5
                else:
                    px = canvas_w // 2
                    py = canvas_h // 2

        clean_params["x"] = int(round(max(0.0, min(float(px), float(canvas_w - 1)))))
        clean_params["y"] = int(round(max(0.0, min(float(py), float(canvas_h - 1)))))

        color = normalize_color(raw_params.get("color") or raw_params.get("fill") or "#000000")
        clean_params["color"] = color or "#000000"

        tol = int(raw_params.get("tolerance") or 32)
        clean_params["tolerance"] = max(0, min(tol, 255))
        clean_params["sampleAllLayers"] = bool(raw_params.get("sampleAllLayers", True))
        clean_params["contiguous"] = bool(raw_params.get("contiguous", True))
        clean_params["antiAlias"] = bool(raw_params.get("antiAlias", True))

        opacity = float(raw_params.get("opacity") or 100.0)
        clean_params["opacity"] = max(1.0, min(opacity, 100.0))

        return {"cmd": "paint.bucket", "params": clean_params}

    # 3. Shape creation command (default)
    kind = str(raw_params.get("kind", "rect")).lower()
    if kind in ("circle", "oval"):
        kind = "ellipse"
    elif kind in ("triangle", "tri"):
        kind = "polygon"
        raw_params.setdefault("sides", 3)
    elif kind in ("rounded_rect", "round_rect", "roundrect", "roundedrect"):
        kind = "roundedRect"
    elif kind in ("rectangle", "square", "box"):
        kind = "rect"

    clean_shape: dict[str, Any] = {"kind": kind}
    clean_shape["name"] = str(raw_params.get("name") or f"{kind.title()} Layer")

    rect = raw_params.get("rect")
    if isinstance(rect, (list, tuple)) and len(rect) >= 4:
        x, y, w, h = float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])
        if w > x and h > y and (w > canvas_w * 0.5 or x + w > canvas_w * 1.2):
            w = max(2.0, w - x)
            h = max(2.0, h - y)
        w = max(1.0, w)
        h = max(1.0, h)
        clean_shape["rect"] = [round(x, 1), round(y, 1), round(w, 1), round(h, 1)]
    elif "points" in raw_params and isinstance(raw_params["points"], list) and len(raw_params["points"]) >= 3:
        pts = raw_params["points"]
        xs = [p[0] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        ys = [p[1] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            clean_shape["rect"] = [round(min_x, 1), round(min_y, 1), max(2.0, round(max_x - min_x, 1)), max(2.0, round(max_y - min_y, 1))]
            if kind == "polygon":
                clean_shape["sides"] = 3
    else:
        clean_shape["rect"] = [100.0, 100.0, 200.0, 200.0]

    raw_fill = raw_params.get("fill")
    if raw_fill is None and "color" in raw_params and "stroke" not in raw_params:
        raw_fill = raw_params.get("color")
    clean_shape["fill"] = normalize_color(raw_fill)

    raw_stroke = raw_params.get("stroke")
    if isinstance(raw_stroke, dict):
        s_width = raw_stroke.get("width") or raw_stroke.get("strokeWidth") or raw_params.get("strokeWidth") or 2.0
        s_color = normalize_color(raw_stroke.get("color") or raw_stroke.get("strokeColor") or "#000000")
        if s_color:
            clean_shape["stroke"] = {"width": float(s_width), "color": s_color}
    elif isinstance(raw_stroke, str):
        s_color = normalize_color(raw_stroke)
        s_width = raw_params.get("strokeWidth") or raw_params.get("stroke_width") or 2.0
        if s_color:
            clean_shape["stroke"] = {"width": float(s_width), "color": s_color}

    if kind == "roundedRect":
        radii = raw_params.get("radii") or raw_params.get("radius") or 12.0
        clean_shape["radii"] = radii
    elif kind == "polygon":
        sides = int(raw_params.get("sides") or 3)
        clean_shape["sides"] = max(3, min(sides, 50))
    elif kind == "star":
        sides = int(raw_params.get("sides") or 5)
        clean_shape["sides"] = max(3, min(sides, 50))
        clean_shape["starRatio"] = float(raw_params.get("starRatio") or 0.4)
    elif kind == "line":
        if "from" in raw_params and "to" in raw_params:
            clean_shape["from"] = raw_params["from"]
            clean_shape["to"] = raw_params["to"]
            clean_shape["weight"] = float(raw_params.get("weight") or 2.0)

    return {"cmd": "shape.create", "params": clean_shape}


def expand_step(step: dict[str, Any], canvas_w: int = 800, canvas_h: int = 800) -> list[dict[str, Any]]:
    """Expand composite steps such as bounding boxes into an enclosed outline stroke and paint bucket fill."""
    cmd = str(step.get("cmd") or step.get("id") or "").strip()
    raw_params = dict(step.get("params") or {})

    if cmd in ("paint.bounding_box", "bounding_box", "box.fill", "enclosed_box"):
        rect = raw_params.get("rect") or [100.0, 100.0, 200.0, 200.0]
        rx, ry = float(rect[0]), float(rect[1])
        rw, rh = float(rect[2]), float(rect[3])
        name = str(raw_params.get("name") or "Bounding Box")
        stroke_color = normalize_color(raw_params.get("stroke_color") or raw_params.get("stroke") or "#111111") or "#111111"
        fill_color = normalize_color(raw_params.get("fill_color") or raw_params.get("fill") or raw_params.get("color") or "#ffd700") or "#ffd700"
        stroke_size = float(raw_params.get("stroke_size") or 4.5)

        outline_pts = stroke_enclosed_rect(rx, ry, rw, rh)
        outline_step = {
            "cmd": "paint.stroke",
            "params": {
                "name": f"{name} (Bounding Outline)",
                "points": outline_pts,
                "size": stroke_size,
                "color": stroke_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        }
        bucket_step = {
            "cmd": "paint.bucket",
            "params": {
                "name": f"{name} (Paint Bucket Fill)",
                "x": int(round(rx + rw * 0.5)),
                "y": int(round(ry + rh * 0.5)),
                "color": fill_color,
                "sampleAllLayers": True,
            },
        }
        return [outline_step, bucket_step]

    if cmd in (
        "paint.triangle",
        "triangle",
        "triangle.fill",
        "enclosed_triangle",
        "paint.polygon",
        "polygon",
        "polygon.fill",
        "enclosed_polygon",
    ):
        name = str(raw_params.get("name") or ("Triangle" if "tri" in cmd else "Polygon"))
        stroke_color = normalize_color(raw_params.get("stroke_color") or raw_params.get("stroke") or "#111111") or "#111111"
        fill_color = normalize_color(raw_params.get("fill_color") or raw_params.get("fill") or raw_params.get("color") or "#ffd700")
        stroke_size = float(raw_params.get("stroke_size") or raw_params.get("size") or 4.5)

        pts = raw_params.get("points")
        if isinstance(pts, list) and len(pts) >= 3:
            vertices = [[float(p[0]), float(p[1])] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        else:
            sides = int(raw_params.get("sides") or (3 if "tri" in cmd else 3))
            cx = float(raw_params.get("cx") or raw_params.get("x") or canvas_w * 0.5)
            cy = float(raw_params.get("cy") or raw_params.get("y") or canvas_h * 0.5)
            radius = float(raw_params.get("radius") or raw_params.get("size") or min(canvas_w, canvas_h) * 0.3)
            orientation = float(raw_params.get("orientation") or raw_params.get("angle") or 0.0)
            vertices = stroke_regular_polygon_vertices(cx, cy, radius, sides=sides, orientation_deg=orientation)

        cx = sum(v[0] for v in vertices) / len(vertices)
        cy = sum(v[1] for v in vertices) / len(vertices)

        outline_pts = stroke_polygon(vertices, wobble=0.0, steps_per_side=20, closed=True)
        outline_step = {
            "cmd": "paint.stroke",
            "params": {
                "name": f"{name} (Enclosed Outline)",
                "points": outline_pts,
                "size": stroke_size,
                "color": stroke_color,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        }
        res = [outline_step]
        if fill_color:
            res.append({
                "cmd": "paint.bucket",
                "params": {
                    "name": f"{name} (Paint Bucket Fill)",
                    "x": int(round(cx)),
                    "y": int(round(cy)),
                    "color": fill_color,
                    "sampleAllLayers": True,
                },
            })
        return res

    return [normalize_step(step, canvas_w, canvas_h)]


def extract_json_from_response(text: str) -> dict[str, Any]:
    """Robustly extract and parse a JSON object from model output, including truncated outputs."""
    raw = text.strip()

    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

    s = raw.find("{")
    if s != -1:
        raw = raw[s:]

    # 1. Clean parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Syntax cleanup: remove trailing commas before closing brackets and line comments
    cleaned = re.sub(r",\s*([\]}])", r"\1", raw)
    cleaned = re.sub(r"//.*?\n", "\n", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 3. Truncated recovery: if model output was cut off mid-step by token limit,
    # find the last complete step object '}' inside the "steps" array and close it.
    pos = cleaned.rfind("}")
    while pos > 0:
        candidate = cleaned[: pos + 1].rstrip().rstrip(",") + "\n  ]\n}"
        try:
            data = json.loads(candidate)
            if isinstance(data, dict) and "steps" in data and len(data["steps"]) > 0:
                logger.info(
                    "Recovered %d valid drawing steps from truncated model response",
                    len(data["steps"]),
                )
                return data
        except Exception:
            pass
        pos = cleaned.rfind("}", 0, pos)

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Decoded JSON is not an object dictionary")
    return data


def parse_prompt_and_images(raw_prompt: str) -> tuple[str, list[Path]]:
    """Parse a prompt string and extract image file paths designated with 'file:<path>'.

    Supports:
      file:/home/jp/apple.png make a green apple
      file:"/path with spaces/img.jpg"
      file:'/path/img.webp'
      file:~/images/apple.png
    """
    pattern = r'(?:^|\s)file:(?:"([^"]+)"|\'([^\']+)\'|(\S+))'
    images: list[Path] = []

    def replacer(match: re.Match) -> str:
        path_str = match.group(1) or match.group(2) or match.group(3)
        if path_str:
            images.append(Path(path_str).expanduser())
        return " "

    clean_text = re.sub(pattern, replacer, raw_prompt)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text, images


def validate_image_files(images: list[Path]) -> None:
    """Validate that reference image files exist and are regular files."""
    for img in images:
        if not img.exists():
            raise FileNotFoundError(f"Reference image not found: {img}")
        if not img.is_file():
            raise ValueError(f"Path is not a regular file: {img}")



def get_detail_guidance(level: int) -> str:
    """Describe target stroke density and detail for any level 1 to 25."""
    lvl = max(1, min(level, 25))
    target_strokes = int(lvl * 10)
    if lvl <= 3:
        desc = "Minimal / quick study: simple expressive gesture lines and basic color blocking."
    elif lvl <= 7:
        desc = "Standard artist detail: multi-pass sketch, layered washes, form shading, clean contours."
    elif lvl <= 15:
        desc = "High detail: dense painterly wash sweeps, directional shading, multi-pass contours, and rich highlights."
    else:
        desc = "Ultra detail / masterwork: rich textured brushwork across all layers, dense cross-hatching, fine line work, and intricate highlights."
    return f"Level {lvl}/25 (~{target_strokes} brushstrokes) - {desc}"


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{max(0, min(255, int(round(r)))):02x}{max(0, min(255, int(round(g)))):02x}{max(0, min(255, int(round(b)))):02x}"


def adjust_color(hex_col: str | None, factor: float) -> str | None:
    if not hex_col or not hex_col.startswith("#"):
        return hex_col
    try:
        r, g, b = hex_to_rgb(hex_col)
        return rgb_to_hex(r * factor, g * factor, b * factor)
    except Exception:
        return hex_col


def is_facial_feature_stroke(name: str) -> bool:
    """Check if a stroke name designates a facial feature that should be protected from broad washes/cross-hatching."""
    n = name.lower()
    return any(k in n for k in (
        "eye", "pupil", "iris", "lid", "lash", "eyelash", "brow", "eyebrow",
        "nose", "nostril", "lip", "mouth", "smile", "chin", "philtrum",
        "cheek", "blush", "catchlight"
    ))


def is_hair_stroke(name: str) -> bool:
    """Check if a stroke represents hair or hair texture."""
    n = name.lower()
    return any(k in n for k in ("hair", "curl", "lock", "tress", "strand", "bangs", "flow"))


def get_face_feature_bounds(steps: list[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    """Find the bounding box (min_x, min_y, max_x, max_y) of facial features (eyes, nose, mouth)."""
    pts: list[list[float]] = []
    for s in steps:
        if not isinstance(s, dict) or s.get("cmd") != "paint.stroke":
            continue
        p = s.get("params") or {}
        name = str(p.get("name") or "").lower()
        if is_facial_feature_stroke(name) and "face:" not in name and "silhouette" not in name and "head" not in name:
            for pt in p.get("points") or []:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    pts.append([float(pt[0]), float(pt[1])])
    if len(pts) < 4:
        return None
    pad = 12.0
    return (
        min(p[0] for p in pts) - pad,
        min(p[1] for p in pts) - pad,
        max(p[0] for p in pts) + pad,
        max(p[1] for p in pts) + pad,
    )


def sanitize_hair_strokes_against_face(
    steps: list[dict[str, Any]],
    face_box: tuple[float, float, float, float] | None,
    allow_face_obstruction: bool = False,
) -> list[dict[str, Any]]:
    """Ensure hair texture strokes do not cut across the facial feature area (eyes, nose, mouth).

    If a hair stroke traverses horizontally across the facial feature zone, split it into
    left-side and right-side locks so the face remains clean and unobstructed.
    """
    if face_box is None or allow_face_obstruction:
        return steps

    fx0, fy0, fx1, fy1 = face_box
    sanitized: list[dict[str, Any]] = []

    for s in steps:
        if not isinstance(s, dict) or s.get("cmd") != "paint.stroke":
            sanitized.append(s)
            continue

        p = s.get("params") or {}
        name = str(p.get("name") or "").lower()

        # Only inspect hair or texture strokes
        if not is_hair_stroke(name) and "texture" not in name:
            sanitized.append(s)
            continue

        pts = p.get("points") or []
        if len(pts) < 2:
            sanitized.append(s)
            continue

        # Check if stroke enters the facial feature box
        pts_in_face = [pt for pt in pts if fx0 <= pt[0] <= fx1 and fy0 <= pt[1] <= fy1]
        if not pts_in_face:
            sanitized.append(s)
            continue

        # If it enters the face box, split into left segment and right segment
        left_pts = [pt for pt in pts if pt[0] < fx0]
        right_pts = [pt for pt in pts if pt[0] > fx1]

        added_any = False
        if len(left_pts) >= 2:
            s_left = dict(s)
            p_left = dict(p)
            p_left["name"] = f"{p.get('name', 'Hair')} (Left Lock)"
            p_left["points"] = left_pts
            s_left["params"] = p_left
            sanitized.append(s_left)
            added_any = True

        if len(right_pts) >= 2:
            s_right = dict(s)
            p_right = dict(p)
            p_right["name"] = f"{p.get('name', 'Hair')} (Right Lock)"
            p_right["points"] = right_pts
            s_right["params"] = p_right
            sanitized.append(s_right)
            added_any = True

        if not added_any:
            logger.info("Suppressed hair stroke '%s' that obstructed the face feature zone", p.get("name"))

    return sanitized


def densify_artwork_plan(
    plan: dict[str, Any],
    detail_level: int,
    target_strokes_per_level: int = 10,
    style: str = "realistic",
) -> dict[str, Any]:
    """Expand and densify artwork brushstrokes to match the requested detail level (1 to 25) and style.

    If an AI model (Ollama / OpenAI) generates a foundation of ~30-50 master strokes,
    this engine generates rich multi-pass washes, form cross-hatching, calligraphy accents,
    and specular highlights shaped by the selected style preset (realistic, dreamlike, abstract,
    sketchy, cartoon, painterly, cubism).
    """
    style_preset = get_style(style)
    steps = plan.get("steps") or []
    existing_strokes = [s for s in steps if isinstance(s, dict) and s.get("cmd") == "paint.stroke"]
    if not existing_strokes:
        plan_copy = dict(plan)
        plan_copy["style"] = style_preset.id
        return plan_copy

    detail = max(1, min(detail_level, 25))
    target = max(len(existing_strokes), int(round(detail * target_strokes_per_level)))
    needed = target - len(existing_strokes)
    if needed <= 0:
        plan_copy = dict(plan)
        plan_copy["style"] = style_preset.id
        return plan_copy

    face_box = get_face_feature_bounds(steps)
    non_feature_strokes = [
        s for s in existing_strokes
        if not is_facial_feature_stroke(str(s.get("params", {}).get("name", "")))
    ]

    washes: list[dict[str, Any]] = []
    shadings: list[dict[str, Any]] = []
    contours: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []

    for s in existing_strokes:
        p = s.get("params") or {}
        name = str(p.get("name") or "").lower()
        size = float(p.get("size") or 10.0)
        is_feature = is_facial_feature_stroke(name)

        if any(k in name for k in ("highlight", "glint", "sparkle", "catchlight", "rim light", "glow")):
            highlights.append(s)
        elif not is_feature and any(k in name for k in ("shade", "shadow", "dark", "under", "belly", "depth", "volume")):
            shadings.append(s)
        elif size <= 8.0 or any(k in name for k in ("ink", "line", "contour", "sketch", "pencil", "pen")):
            if not is_feature:
                contours.append(s)
        elif not is_feature:
            washes.append(s)

    if not washes:
        washes = non_feature_strokes or existing_strokes
    if not shadings:
        shadings = washes
    if not contours:
        contours = non_feature_strokes or existing_strokes
    if not highlights:
        highlights = existing_strokes

    q_wash = int(round(needed * 0.60)) if style_preset.id == "cartoon" else int(round(needed * 0.40))
    q_shade = int(round(needed * 0.22)) if style_preset.id == "cartoon" else int(round(needed * 0.30))
    q_contour = int(round(needed * 0.14)) if style_preset.id == "cartoon" else int(round(needed * 0.18))
    q_hi = needed - (q_wash + q_shade + q_contour)

    children_by_parent: dict[int, list[dict[str, Any]]] = {}
    w_count, sh_count, c_count, h_count = 0, 0, 0, 0

    def add_child(parent_step: dict[str, Any], child_step: dict[str, Any]) -> None:
        p_name = str(parent_step.get("params", {}).get("name", "")).lower()
        if is_hair_stroke(p_name) and face_box is not None:
            c_pts = child_step.get("params", {}).get("points") or []
            fx0, fy0, fx1, fy1 = face_box
            in_face = [pt for pt in c_pts if fx0 <= pt[0] <= fx1 and fy0 <= pt[1] <= fy1]
            if in_face:
                return  # Skip child stroke that would draw across the face
        key = id(parent_step)
        if key not in children_by_parent:
            children_by_parent[key] = []
        children_by_parent[key].append(child_step)

    # 1. Color Wash Sweeps
    for s in washes:
        if w_count >= q_wash:
            break
        p = s.get("params") or {}
        pts = p.get("points") or []
        if len(pts) < 2:
            continue
        name = str(p.get("name") or "Wash")
        size = float(p.get("size") or 25.0)
        col = p.get("color")
        hardness = style_preset.wash_hardness
        opacity = style_preset.wash_opacity

        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        L = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / L, dx / L
        cx_wash = sum(pt[0] for pt in pts) / len(pts)
        cy_wash = sum(pt[1] for pt in pts) / len(pts)

        passes_for_this = max(1, (q_wash - w_count) // max(1, len(washes)) + 1)
        for pass_i in range(1, passes_for_this + 1):
            if w_count >= q_wash:
                break
            w_count += 1
            if style_preset.id == "cartoon":
                # Contract slightly inward toward the wash centroid so fills reinforce interior solidity
                # without bleeding outside black ink contours or duplicating circular suns/dots.
                # For wide horizontal background bands (sky/hills), preserve full X span so edges stay flush.
                shrink = min(0.35, pass_i * 0.08)
                is_wide_band = abs(pts[-1][0] - pts[0][0]) >= 500.0
                off_pts = [
                    [
                        round(pt[0] if is_wide_band else (pt[0] + (cx_wash - pt[0]) * shrink), 1),
                        round(pt[1] + (cy_wash - pt[1]) * shrink, 1),
                    ]
                    for pt in pts
                ]
            else:
                dist = (pass_i * 0.22) * size * (1 if w_count % 2 == 1 else -1)
                wob = style_preset.wobble * 2.0
                off_pts = [
                    [
                        round(pt[0] + nx * dist + math.sin(i * 0.8 + w_count) * wob, 1),
                        round(pt[1] + ny * dist + math.cos(i * 0.8 + w_count) * wob, 1),
                    ]
                    for i, pt in enumerate(pts)
                ]
            wash_color = col if style_preset.id == "cartoon" else style_preset.adjust_color(col, 0.94 if w_count % 2 == 0 else 1.06)
            wash_name = f"{name} (Pencil Gesture {w_count})" if style_preset.id == "pencil" else f"{name} ({style_preset.name} Wash {w_count})"
            wash_size = max(1.5, min(2.8, round(size * 0.1, 1))) if style_preset.id == "pencil" else max(10.0 if style_preset.id == "cartoon" else 8.0, round(size * (0.88 if style_preset.id == "cartoon" else (0.85 + 0.15 * (w_count % 2))), 1))
            wash_hard = 0.6 if style_preset.id == "pencil" else (0.98 if style_preset.id == "cartoon" else round(hardness * 0.9, 2))
            wash_opac = 0.4 if style_preset.id == "pencil" else (1.0 if style_preset.id == "cartoon" else round(max(0.35, opacity * 0.88), 2))
            add_child(
                s,
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": wash_name,
                        "points": off_pts,
                        "size": wash_size,
                        "color": wash_color,
                        "hardness": wash_hard,
                        "opacity": wash_opac,
                    },
                },
            )

    # 2. Form Shading & Cross-Hatching
    for s in shadings:
        if sh_count >= q_shade:
            break
        p = s.get("params") or {}
        pts = p.get("points") or []
        if len(pts) < 2:
            continue
        name = str(p.get("name") or "Shading")
        size = float(p.get("size") or 15.0)
        col = p.get("color")

        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        mid_pt = pts[len(pts) // 2]
        ang = math.atan2(dy, dx) + (math.pi / 3.0 if style_preset.id in ("abstract", "cubism") else math.pi / 4.0)

        passes_for_this = max(1, (q_shade - sh_count) // max(1, len(shadings)) + 1)
        for pass_i in range(1, passes_for_this + 1):
            if sh_count >= q_shade:
                break
            sh_count += 1
            hlen = max(16.0, size * 1.3)
            t_offset = (pass_i - 1) * 12.0 * (1 if pass_i % 2 == 1 else -1)
            cx = mid_pt[0] + (dx / max(1.0, math.hypot(dx, dy))) * t_offset
            cy = mid_pt[1] + (dy / max(1.0, math.hypot(dx, dy))) * t_offset
            hx0 = round(cx - math.cos(ang) * hlen * 0.5, 1)
            hy0 = round(cy - math.sin(ang) * hlen * 0.5, 1)
            hx1 = round(cx + math.cos(ang) * hlen * 0.5, 1)
            hy1 = round(cy + math.sin(ang) * hlen * 0.5, 1)

            if style_preset.id == "sketchy":
                hatch_color = style_preset.adjust_color(col, 0.85) or "#566573"
                hatch_size = max(1.8, min(3.5, round(size * 0.16, 1)))
                hatch_hardness = 0.9
                hatch_opacity = 0.65
                hatch_label = f"{name} (Pencil Hatch {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)
            elif style_preset.id == "cartoon":
                # In Cartoon/Cel style, shadows are smooth contiguous cel curves along pts—never diagonal ticks
                hatch_color = col or "#dce3ea"
                hatch_size = max(5.0, round(size * 0.80, 1))
                hatch_hardness = 0.98
                hatch_opacity = float(p.get("opacity") or 1.0)
                hatch_label = f"{name} (Cel Shadow {sh_count})"
                hatch_pts = [[round(pt[0], 1), round(pt[1], 1)] for pt in pts]
            elif style_preset.id == "dreamlike":
                hatch_color = style_preset.adjust_color(col, 0.95)
                hatch_size = max(6.0, round(size * 0.5, 1))
                hatch_hardness = 0.45
                hatch_opacity = 0.7
                hatch_label = f"{name} (Luminous Shade {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)
            elif style_preset.id == "abstract":
                hatch_color = style_preset.adjust_color(col, 0.8)
                hatch_size = max(3.0, round(size * 0.3, 1))
                hatch_hardness = 0.95
                hatch_opacity = 0.9
                hatch_label = f"{name} (Vector Plane {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)
            elif style_preset.id == "cubism":
                hatch_color = style_preset.adjust_color(col, 0.72)
                hatch_size = max(3.5, round(size * 0.38, 1))
                hatch_hardness = 0.98
                hatch_opacity = 0.95
                hatch_label = f"{name} (Cubist Facet Plane {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)
            elif style_preset.id == "pencil":
                hatch_color = style_preset.adjust_color(col, 0.85) or "#4b5563"
                hatch_size = max(1.2, min(2.4, round(size * 0.12, 1)))
                hatch_hardness = 0.65
                hatch_opacity = 0.45
                hatch_label = f"{name} (Pencil Cross-Hatch {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)
            else:
                hatch_color = style_preset.adjust_color(col, 0.88)
                hatch_size = max(2.0, min(5.0, round(size * 0.22, 1)))
                hatch_hardness = 0.85
                hatch_opacity = 0.7
                hatch_label = f"{name} (Hatch Tone {sh_count})"
                hatch_pts = stroke_line(hx0, hy0, hx1, hy1, steps=8, wobble=style_preset.wobble * 0.4)

            add_child(
                s,
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": hatch_label,
                        "points": hatch_pts,
                        "size": hatch_size,
                        "color": hatch_color,
                        "hardness": hatch_hardness,
                        "opacity": hatch_opacity,
                    },
                },
            )

    # 3. Ink Contours & Line Art
    for s in contours:
        if c_count >= q_contour:
            break
        p = s.get("params") or {}
        pts = p.get("points") or []
        if len(pts) < 2:
            continue
        name = str(p.get("name") or "Ink")
        size = float(p.get("size") or 4.0)
        col = p.get("color")

        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        L = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / L, dx / L

        passes_for_this = max(1, (q_contour - c_count) // max(1, len(contours)) + 1)
        for pass_i in range(1, passes_for_this + 1):
            if c_count >= q_contour:
                break
            c_count += 1
            dist = 0.0 if style_preset.id == "cartoon" else 1.6 * (1 if c_count % 2 == 1 else -1)
            wob = 0.0 if style_preset.id == "cartoon" else style_preset.wobble * 1.5
            off_pts = [
                [
                    round(pt[0] + nx * dist + math.sin(i * 1.2 + c_count) * wob, 1),
                    round(pt[1] + ny * dist + math.cos(i * 1.2 + c_count) * wob, 1),
                ]
                for i, pt in enumerate(pts)
            ]

            if style_preset.id == "cartoon":
                outline_color = "#111116"
                outline_size = max(2.5, round(size * 0.90, 1))
                outline_hardness = 1.0
                outline_opacity = 1.0
                label = f"{name} (Ink Contour {c_count})"
            elif style_preset.id == "sketchy":
                outline_color = style_preset.adjust_color(col, 0.9) or "#2c3e50"
                outline_size = max(1.5, round(size * 0.65 * style_preset.outline_size_scale, 1))
                outline_hardness = 0.88
                outline_opacity = 0.75
                label = f"{name} (Pencil Guide {c_count})"
            elif style_preset.id == "dreamlike":
                outline_color = style_preset.adjust_color(col, 1.05)
                outline_size = max(1.8, round(size * 0.75 * style_preset.outline_size_scale, 1))
                outline_hardness = 0.55
                outline_opacity = 0.75
                label = f"{name} (Ethereal Edge {c_count})"
            elif style_preset.id == "cubism":
                outline_color = "#181512"
                outline_size = max(2.0, round(size * 0.85 * style_preset.outline_size_scale, 1))
                outline_hardness = 0.98
                outline_opacity = 0.98
                label = f"{name} (Cubist Edge Fracture {c_count})"
            elif style_preset.id == "pencil":
                outline_color = style_preset.adjust_color(col, 0.85) or "#374151"
                outline_size = max(1.2, min(2.4, round(size * 0.45 * style_preset.outline_size_scale, 1)))
                outline_hardness = 0.65
                outline_opacity = 0.55
                label = f"{name} (Pencil Rough Contour {c_count})"
            else:
                outline_color = col
                outline_size = max(1.8, round(size * 0.75 * style_preset.outline_size_scale, 1))
                outline_hardness = style_preset.outline_hardness
                outline_opacity = 0.85
                label = f"{name} (Accent Contour {c_count})"

            add_child(
                s,
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": label,
                        "points": off_pts,
                        "size": outline_size,
                        "color": outline_color,
                        "hardness": outline_hardness,
                        "opacity": outline_opacity,
                    },
                },
            )

    # 4. Highlights & Specular Accents
    for s in highlights:
        if h_count >= q_hi:
            break
        p = s.get("params") or {}
        pts = p.get("points") or []
        if len(pts) < 2:
            continue
        name = str(p.get("name") or "Highlight")
        size = float(p.get("size") or 6.0)

        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        mid_pt = pts[len(pts) // 2]
        ang = math.atan2(dy, dx) + math.pi / 2.0

        passes_for_this = max(1, (q_hi - h_count) // max(1, len(highlights)) + 1)
        for pass_i in range(1, passes_for_this + 1):
            if h_count >= q_hi:
                break
            h_count += 1
            if style_preset.id == "cartoon":
                # Keep cartoon catchlights on the exact highlight point without scattering lines outside the eye
                gx0, gy0 = round(mid_pt[0], 1), round(mid_pt[1], 1)
                gx1, gy1 = round(mid_pt[0] + 0.5, 1), round(mid_pt[1] + 0.5, 1)
            else:
                glen = max(8.0, size * 0.8)
                g_off = (pass_i - 1) * 8.0 * (1 if pass_i % 2 == 1 else -1)
                cx = mid_pt[0] + g_off
                cy = mid_pt[1] + g_off
                gx0 = round(cx - math.cos(ang) * glen * 0.5, 1)
                hy_dir = math.sin(ang)
                gy0 = round(cy - hy_dir * glen * 0.5, 1)
                gx1 = round(cx + math.cos(ang) * glen * 0.5, 1)
                gy1 = round(cy + hy_dir * glen * 0.5, 1)

            if style_preset.id == "dreamlike":
                hi_color = "#ffffff" if h_count % 2 == 0 else "#fbfcfc"
                hi_size = max(3.5, round(size * 0.8, 1))
                hi_hardness = 0.5
                hi_opacity = 0.85
                label = f"{name} (Aura Flare {h_count})"
            elif style_preset.id == "cartoon":
                hi_color = "#ffffff"
                hi_size = max(2.5, min(4.2, round(size * 0.75, 1)))
                hi_hardness = 1.0
                hi_opacity = 1.0
                label = f"{name} (Cel Gleam {h_count})"
            elif style_preset.id == "sketchy":
                hi_color = "#fdfefe"
                hi_size = max(2.0, round(size * 0.5, 1))
                hi_hardness = 0.8
                hi_opacity = 0.7
                label = f"{name} (Eraser Light {h_count})"
            elif style_preset.id == "cubism":
                hi_color = "#fefae0" if h_count % 2 == 0 else "#fff8dc"
                hi_size = max(3.0, round(size * 0.7, 1))
                hi_hardness = 0.95
                hi_opacity = 0.95
                label = f"{name} (Facet Plane Light {h_count})"
            elif style_preset.id == "pencil":
                hi_color = "#9ca3af" if h_count % 2 == 0 else "#ffffff"
                hi_size = max(1.2, min(2.0, round(size * 0.35, 1)))
                hi_hardness = 0.6
                hi_opacity = 0.35
                label = f"{name} (Pencil Accent {h_count})"
            else:
                hi_color = "#ffffff"
                hi_size = max(2.5, round(size * 0.65, 1))
                hi_hardness = 1.0
                hi_opacity = 0.95
                label = f"{name} (Specular Glint {h_count})"

            add_child(
                s,
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": label,
                        "points": stroke_line(gx0, gy0, gx1, gy1, steps=6),
                        "size": hi_size,
                        "color": hi_color,
                        "hardness": hi_hardness,
                        "opacity": hi_opacity,
                    },
                },
            )

    allocated = w_count + sh_count + c_count + h_count
    fallback_pool = washes + shadings + contours
    while allocated < needed and fallback_pool:
        for parent in fallback_pool:
            if allocated >= needed:
                break
            p = parent.get("params") or {}
            pts = p.get("points") or []
            if len(pts) < 2:
                continue
            allocated += 1
            name = str(p.get("name") or "Stroke")
            size = float(p.get("size") or 15.0)
            col = p.get("color")
            dx = pts[-1][0] - pts[0][0]
            dy = pts[-1][1] - pts[0][1]
            L = max(1.0, math.hypot(dx, dy))
            nx, ny = -dy / L, dx / L
            dist = (allocated * 0.18) * size * (1 if allocated % 2 == 1 else -1)
            off_pts = [[round(pt[0] + nx * dist, 1), round(pt[1] + ny * dist, 1)] for pt in pts]
            add_child(
                parent,
                {
                    "cmd": "paint.stroke",
                    "params": {
                        "name": f"{name} (Fine Texture {allocated})",
                        "points": off_pts,
                        "size": max(4.0, round(size * 0.7, 1)),
                        "color": style_preset.adjust_color(col, 0.96),
                        "hardness": 0.75,
                        "opacity": 0.8,
                    },
                },
            )

    final_steps: list[dict[str, Any]] = []
    for st in steps:
        final_steps.append(st)
        key = id(st)
        if key in children_by_parent:
            final_steps.extend(children_by_parent[key])

    prompt_str = str(plan.get("title") or "").lower()
    allow_deviate = any(k in prompt_str for k in ("hair over face", "hair in face", "hair over eyes", "covering face", "obscured", "veil", "mask", "hidden face"))
    cleaned_steps = sanitize_hair_strokes_against_face(final_steps, face_box, allow_face_obstruction=allow_deviate)

    plan_copy = dict(plan)
    plan_copy["steps"] = cleaned_steps
    plan_copy["style"] = style_preset.id
    return plan_copy


def compose_with_ollama(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate drawing steps using local Ollama model (with optional vision images)."""
    import ollama

    client = ollama.Client(host=config.ollama_host)
    model = config.ollama_model
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))
    detail_info = get_detail_guidance(detail)

    img_info = f" with {len(images)} reference image(s)" if images else ""
    logger.info(
        "Querying Ollama at %s with model '%s'%s (style: %s, detail %d/25)...",
        config.ollama_host,
        model,
        img_info,
        style_preset.name,
        detail,
    )

    is_portrait = is_portrait_or_face_prompt(prompt, images)
    is_geometric, _, _, _ = parse_geometric_shape_prompt(prompt)
    is_animation = int(getattr(config, "steps", 1)) > 1
    style_system = f"{SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"
    if is_portrait or images:
        style_system = f"{style_system}\n\n{PORTRAIT_PROMPT_INSTRUCTION}"
    if is_geometric:
        style_system = f"{style_system}\n\n{GEOMETRIC_PROMPT_INSTRUCTION}"
    if is_animation:
        style_system = f"{style_system}\n\n{ANIMATION_KEYFRAME_INSTRUCTION}"

    geom_hint = (
        "CRITICAL: The prompt requests a geometric shape. A triangle MUST be an exact 3-sided polygon with straight edges and sharp corners (NEVER round it into a gum drop or oval!).\n"
        if is_geometric
        else ""
    )
    anim_hint = (
        f"\nCRITICAL ANIMATION INSTRUCTION (FRAME 1 OF {config.steps} FRAMES):\n"
        f"This illustration will serve as the initial starting pose (Frame 1 at t=0) for a {config.steps}-step animation.\n"
        f"Draw ONLY ONE SINGLE INSTANCE OF THE SUBJECT in its initial starting position / pose!\n"
        f"STRICTLY FORBIDDEN: Do NOT draw multiple positions, multiple stages of the bounce/motion, multiple copies of the subject, or motion path arcs!\n"
        if is_animation
        else ""
    )

    if images:
        user_content = (
            f"Visual reference image{'s have' if len(images) > 1 else ' has'} been provided.\n"
            f"Carefully study the shapes, anatomy, subject, composition, and colors of the reference.\n"
            f"Create an expressive artist illustration inspired by it for '{prompt}' on an {width}x{height} canvas.\n"
            f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
            f"Color Mood: {style_preset.color_mood}\n"
            f"Requested Detail: {detail_info}\n"
            f"{geom_hint}"
            f"{anim_hint}"
            "Use 3 to 6 key waypoint coordinate points per stroke (the engine automatically smooths curves or keeps polygons sharp).\n"
            "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
        )
        user_msg: dict[str, Any] = {
            "role": "user",
            "content": user_content,
            "images": [str(p) for p in images],
        }
    else:
        user_msg = {
            "role": "user",
            "content": (
                f"Create an expressive artist illustration for '{prompt}' on an {width}x{height} canvas.\n"
                f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
                f"Color Mood: {style_preset.color_mood}\n"
                f"Requested Detail: {detail_info}\n"
                f"{geom_hint}"
                f"{anim_hint}"
                "Use 3 to 6 key waypoint coordinate points per stroke (the engine automatically smooths curves or keeps polygons sharp).\n"
                "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
            ),
        }

    try:
        res = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": style_system},
                user_msg,
            ],
            options={
                "num_ctx": 16384,
                "num_predict": 6144,
                "temperature": 0.35,
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "multimodal" in err_msg.lower() or "does not support images" in err_msg.lower():
            raise ValueError(
                f"Model '{model}' does not support vision/image input. "
                f"Please switch to a vision model (e.g. /model llama3.2-vision:11b or /model gpt-4o-mini)."
            ) from e
        raise

    content = res.message.content or ""
    if not content:
        raise ValueError(f"Ollama model '{model}' returned empty content (done_reason: {getattr(res, 'done_reason', 'unknown')})")

    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    if not isinstance(raw_steps, list):
        raise ValueError("Response did not contain a valid 'steps' array")

    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    base_title = data.get("title") or prompt.title()
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=model)

    bg_fallback = (
        "#ffffff" if style_preset.id == "pencil" else
        "#fdfefe" if style_preset.id == "sketchy" else
        "#111822" if style_preset.id == "abstract" else
        "#16122c" if style_preset.id == "dreamlike" else
        "#1c1917" if style_preset.id == "cubism" else
        "#f8f9fa"
    )

    plan = {
        "title": title,
        "background": normalize_color(data.get("background")) or bg_fallback,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
    }
    return densify_artwork_plan(plan, detail_level=detail, style=config.style)


def compose_with_openai(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate drawing steps using OpenAI-compatible API (with optional vision images)."""
    import base64
    from openai import OpenAI

    client = OpenAI(
        api_key=config.openai_api_key or "sk-dummy",
        base_url=config.openai_base_url,
    )
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))
    detail_info = get_detail_guidance(detail)

    is_portrait = is_portrait_or_face_prompt(prompt, images)
    is_geometric, _, _, _ = parse_geometric_shape_prompt(prompt)
    is_animation = int(getattr(config, "steps", 1)) > 1
    style_system = f"{SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"
    if is_portrait or images:
        style_system = f"{style_system}\n\n{PORTRAIT_PROMPT_INSTRUCTION}"
    if is_geometric:
        style_system = f"{style_system}\n\n{GEOMETRIC_PROMPT_INSTRUCTION}"
    if is_animation:
        style_system = f"{style_system}\n\n{ANIMATION_KEYFRAME_INSTRUCTION}"

    geom_hint = (
        "CRITICAL: The prompt requests a geometric shape. A triangle MUST be an exact 3-sided polygon with straight edges and sharp corners (NEVER round it into a gum drop or oval!).\n"
        if is_geometric
        else ""
    )
    anim_hint = (
        f"\nCRITICAL ANIMATION INSTRUCTION (FRAME 1 OF {config.steps} FRAMES):\n"
        f"This illustration will serve as the initial starting pose (Frame 1 at t=0) for a {config.steps}-step animation.\n"
        f"Draw ONLY ONE SINGLE INSTANCE OF THE SUBJECT in its initial starting position / pose!\n"
        f"STRICTLY FORBIDDEN: Do NOT draw multiple positions, multiple stages of the bounce/motion, multiple copies of the subject, or motion path arcs!\n"
        if is_animation
        else ""
    )

    if images:
        text_instruction = (
            f"Visual reference image{'s have' if len(images) > 1 else ' has'} been provided.\n"
            f"Carefully study the shapes, anatomy, subject, composition, and colors of the reference.\n"
            f"Create an expressive artist illustration inspired by it for '{prompt}' on an {width}x{height} canvas.\n"
            f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
            f"Color Mood: {style_preset.color_mood}\n"
            f"Requested Detail: {detail_info}\n"
            f"{geom_hint}"
            f"{anim_hint}"
            "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
        )
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": text_instruction}]
        for p in images:
            b64_data = base64.b64encode(p.read_bytes()).decode("utf-8")
            ext = p.suffix.lstrip(".").lower() or "png"
            if ext == "jpg":
                ext = "jpeg"
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{ext};base64,{b64_data}"},
            })
        user_msg: dict[str, Any] = {"role": "user", "content": content_parts}
    else:
        user_msg = {
            "role": "user",
            "content": (
                f"Create an expressive artist illustration for '{prompt}' on an {width}x{height} canvas.\n"
                f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
                f"Color Mood: {style_preset.color_mood}\n"
                f"Requested Detail: {detail_info}\n"
                f"{geom_hint}"
                f"{anim_hint}"
                "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
            ),
        }

    response = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": style_system},
            user_msg,
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )

    content = response.choices[0].message.content or "{}"
    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    base_title = data.get("title") or prompt.title()
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=config.openai_model)

    bg_fallback = (
        "#ffffff" if style_preset.id == "pencil" else
        "#fdfefe" if style_preset.id == "sketchy" else
        "#111822" if style_preset.id == "abstract" else
        "#16122c" if style_preset.id == "dreamlike" else
        "#1c1917" if style_preset.id == "cubism" else
        "#f8f9fa"
    )

    plan = {
        "title": title,
        "background": normalize_color(data.get("background")) or bg_fallback,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": config.openai_model.strip().replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
    }
    return densify_artwork_plan(plan, detail_level=detail, style=config.style)


def compose_with_gemini(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate drawing steps using Google Gemini via its official OpenAI-compatible endpoint."""
    import base64
    from openai import OpenAI

    api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or config.openai_api_key or "sk-dummy"
    base_url = config.gemini_base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))
    detail_info = get_detail_guidance(detail)

    is_portrait = is_portrait_or_face_prompt(prompt, images)
    is_geometric, _, _, _ = parse_geometric_shape_prompt(prompt)
    is_animation = int(getattr(config, "steps", 1)) > 1
    style_system = f"{SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"
    if is_portrait or images:
        style_system = f"{style_system}\n\n{PORTRAIT_PROMPT_INSTRUCTION}"
    if is_geometric:
        style_system = f"{style_system}\n\n{GEOMETRIC_PROMPT_INSTRUCTION}"
    if is_animation:
        style_system = f"{style_system}\n\n{ANIMATION_KEYFRAME_INSTRUCTION}"

    geom_hint = (
        "CRITICAL: The prompt requests a geometric shape. A triangle MUST be an exact 3-sided polygon with straight edges and sharp corners (NEVER round it into a gum drop or oval!).\n"
        if is_geometric
        else ""
    )
    anim_hint = (
        f"\nCRITICAL ANIMATION INSTRUCTION (FRAME 1 OF {config.steps} FRAMES):\n"
        f"This illustration will serve as the initial starting pose (Frame 1 at t=0) for a {config.steps}-step animation.\n"
        f"Draw ONLY ONE SINGLE INSTANCE OF THE SUBJECT in its initial starting position / pose!\n"
        f"STRICTLY FORBIDDEN: Do NOT draw multiple positions, multiple stages of the bounce/motion, multiple copies of the subject, or motion path arcs!\n"
        if is_animation
        else ""
    )

    if images:
        text_instruction = (
            f"Visual reference image{'s have' if len(images) > 1 else ' has'} been provided.\n"
            f"Carefully study the shapes, anatomy, subject, composition, and colors of the reference.\n"
            f"Create an expressive artist illustration inspired by it for '{prompt}' on an {width}x{height} canvas.\n"
            f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
            f"Color Mood: {style_preset.color_mood}\n"
            f"Requested Detail: {detail_info}\n"
            f"{geom_hint}"
            f"{anim_hint}"
            "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
        )
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": text_instruction}]
        for p in images:
            b64_data = base64.b64encode(p.read_bytes()).decode("utf-8")
            ext = p.suffix.lstrip(".").lower() or "png"
            if ext == "jpg":
                ext = "jpeg"
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{ext};base64,{b64_data}"},
            })
        user_msg: dict[str, Any] = {"role": "user", "content": content_parts}
    else:
        user_msg = {
            "role": "user",
            "content": (
                f"Create an expressive artist illustration for '{prompt}' on an {width}x{height} canvas.\n"
                f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
                f"Color Mood: {style_preset.color_mood}\n"
                f"Requested Detail: {detail_info}\n"
                f"{geom_hint}"
                f"{anim_hint}"
                "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
            ),
        }

    gemini_model = (config.gemini_model or "gemini-3.8-flash").strip().replace(" ", "-")

    response = client.chat.completions.create(
        model=gemini_model,
        messages=[
            {"role": "system", "content": style_system},
            user_msg,
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )

    content = response.choices[0].message.content or "{}"
    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    base_title = data.get("title") or prompt.title()
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=gemini_model)

    bg_fallback = (
        "#ffffff" if style_preset.id == "pencil" else
        "#fdfefe" if style_preset.id == "sketchy" else
        "#111822" if style_preset.id == "abstract" else
        "#16122c" if style_preset.id == "dreamlike" else
        "#1c1917" if style_preset.id == "cubism" else
        "#f8f9fa"
    )

    plan = {
        "title": title,
        "background": normalize_color(data.get("background")) or bg_fallback,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": gemini_model.replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
    }
    return densify_artwork_plan(plan, detail_level=detail, style=config.style)


def sanitize_pencil_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Sanitize plan for the 'pencil' animation style.

    Enforces:
    - Clean white animation paper background (#ffffff).
    - Strictly NO paint bucket fills (drops paint.bucket).
    - Strictly NO solid paint fills on shapes (fill=None).
    - Soft, light graphite pencil stroke dynamics (hardness <= 0.70, opacity <= 0.65, size <= 3.0).
    - Monochromatic graphite palette mapping.
    """
    style_preset = get_style("pencil")
    clean_plan = dict(plan)
    clean_plan["style"] = "pencil"
    clean_plan["background"] = "#ffffff"

    raw_steps = plan.get("steps") or []
    cleaned_steps: list[dict[str, Any]] = []

    for step in raw_steps:
        cmd = step.get("cmd") or step.get("id") or ""
        # Strictly drop all paint bucket fills
        if cmd == "paint.bucket":
            continue

        step_copy = dict(step)
        params = dict(step.get("params") or {})

        if cmd == "shape.create":
            # Remove solid paint fills from vector shapes
            if params.get("fill"):
                params["fill"] = None
            if params.get("stroke"):
                params["stroke"] = style_preset.adjust_color(params.get("stroke")) or "#374151"
            step_copy["params"] = params
            cleaned_steps.append(step_copy)
        elif cmd == "paint.stroke":
            col = params.get("color")
            params["color"] = style_preset.adjust_color(col) or "#374151"
            size = float(params.get("size") or 3.0)
            if size > 3.0:
                params["size"] = max(1.2, round(min(size * 0.35, 2.8), 1))
            hardness = float(params.get("hardness") or 0.65)
            params["hardness"] = min(hardness, 0.70)
            opacity = float(params.get("opacity") or 0.55)
            params["opacity"] = min(opacity, 0.65)
            step_copy["params"] = params
            cleaned_steps.append(step_copy)
        else:
            step_copy["params"] = params
            cleaned_steps.append(step_copy)

    clean_plan["steps"] = cleaned_steps
    return clean_plan


def plan_artwork(
    prompt: str,
    config: PainterConfig,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> tuple[dict[str, Any], str]:
    """Plan drawing steps for a prompt. Honors config.provider (ollama/openai/gemini) and falls back to procedural."""
    if images is None:
        clean_text, extracted_images = parse_prompt_and_images(prompt)
        prompt = clean_text or (
            f"Recreate an expressive artist illustration inspired by the reference image"
            if extracted_images
            else prompt
        )
        images = extracted_images

    detail = max(1, min(config.detail_level, 25))
    style_preset = get_style(config.style)

    def wrap_plan(p: dict[str, Any], src: str) -> tuple[dict[str, Any], str]:
        if config.style.lower() == "pencil":
            return sanitize_pencil_plan(p), src
        return p, src

    # 0. Explicit offline / procedural fallback requested
    if config.provider in ("none", "fallback", "builtin"):
        logger.info("Using built-in procedural composer for '%s' (style: %s, detail level: %d)", prompt, style_preset.name, detail)
        plan = plan_fallback(prompt, width, height, detail_level=detail, style=config.style, images=images, model="built-in")
        plan = densify_artwork_plan(plan, detail_level=detail, style=config.style)
        return wrap_plan(plan, f"Built-in Composer [{style_preset.name}] (Detail {detail}/25)")

    # 1. If Gemini provider is requested
    if config.provider in ("gemini", "google"):
        try:
            plan = compose_with_gemini(prompt, config, width, height, images=images)
            if plan.get("steps"):
                return wrap_plan(plan, f"Gemini ({config.gemini_model})")
        except Exception as e:
            logger.warning("Gemini composition failed: %s", e)

    # 2. If OpenAI provider is requested
    if config.provider == "openai":
        try:
            plan = compose_with_openai(prompt, config, width, height, images=images)
            if plan.get("steps"):
                return wrap_plan(plan, f"OpenAI ({config.openai_model})")
        except Exception as e:
            logger.warning("OpenAI composition failed: %s", e)

    # 3. Try Ollama (Default or secondary)
    if config.provider == "ollama" or (config.provider not in ("none", "fallback", "builtin") and not config.openai_api_key and not config.openai_base_url and not config.gemini_api_key):
        try:
            plan = compose_with_ollama(prompt, config, width, height, images=images)
            if plan.get("steps"):
                return wrap_plan(plan, f"Ollama ({config.ollama_model})")
        except Exception as e:
            logger.warning("Ollama composition failed: %s", e)

    # 4. Try Gemini as secondary if keys are present and not already tried
    if config.provider not in ("gemini", "google") and config.gemini_api_key:
        try:
            plan = compose_with_gemini(prompt, config, width, height, images=images)
            if plan.get("steps"):
                return wrap_plan(plan, f"Gemini ({config.gemini_model})")
        except Exception as e:
            logger.warning("Gemini composition failed: %s", e)

    # 5. Try OpenAI as secondary if not already tried and keys are present
    if config.provider != "openai" and (config.openai_api_key or config.openai_base_url):
        try:
            plan = compose_with_openai(prompt, config, width, height, images=images)
            if plan.get("steps"):
                return wrap_plan(plan, f"OpenAI ({config.openai_model})")
        except Exception as e:
            logger.warning("OpenAI composition failed: %s", e)

    # 4. Built-in procedural fallback
    logger.info("Using built-in procedural composer for '%s' (style: %s, detail level: %d)", prompt, style_preset.name, detail)
    plan = plan_fallback(prompt, width, height, detail_level=detail, style=config.style, images=images, model="built-in")
    plan = densify_artwork_plan(plan, detail_level=detail, style=config.style)
    return wrap_plan(plan, f"Built-in Composer [{style_preset.name}] (Detail {detail}/25)")


REFINEMENT_SYSTEM_PROMPT = """You are a master artist and art director conducting an iterative refinement feedback pass in PhotoCraft.
You are inspecting a rendered snapshot of the current in-progress digital canvas.

PRIMARY DIRECTIVES & ARTISTIC STANDARDS:
1. FLESH OUT FORGOTTEN, HOLLOW, OR UNPAINTED SHAPES (TOP PRIORITY):
   In the initial drawing pass, secondary line-art shapes or wireframe outlines may have been left unfilled due to step budgets or constraints.
   Carefully inspect the rendered image for hollow shapes (e.g. empty hollow ears showing the background sky through them, unpainted inner ears, hollow horns/antlers, uncolored snout/muzzle, unshaded limbs, or unpainted eyes)!
   Flesh out these forgotten parts by painting clean, solid base color fills inside them using paint.bucket or solid paint.stroke in the subject's proper matching local color.
   Ensure every part of the subject's anatomy is completely solid and filled—never left as a hollow wireframe!

2. ADD FINE DETAILS & SECONDARY ANATOMY FORGOTTEN IN THE FIRST PASS:
   Add the expressive fine details that didn't have room in the initial pass:
   - Facial accents: inner ear shading/creases, nostril dots/indentations on the snout/nose, expressive mouth parting lines, eyebrow character, eye pupils, and crisp white specular catchlight dots.
   - Anatomical accents: hooves, claws, toes, paw pads, knee/joint creases, tail tufts, antler tine tips or ridge grooves, fur/hair tufts (e.g. neck mane or chin dewlap).
   - Ground contact: subtle cast shadow anchors directly under the feet/hooves where they touch the ground, and subtle grass blades at contact points.
   - Crisp contours: trace single, confident vector ink outlines to close any open perimeter gaps.

3. DO NOT HALLUCINATE OCCLUSION REPAIRS OR PAINT OVER SOLID BODY SURFACES:
   If a subject's body, torso, head, or limbs are ALREADY solidly colored and clean, DO NOT paint broad opaque cover strokes across the middle of the body!
   Never place arbitrary geometric blobs, horizontal bars, or random patches across a clean, solid body surface!
   Focus strictly on areas that are hollow, missing, or need specific anatomical and textural detailing.

4. STRICT COLOR PALETTE HARMONY (MATCH THE ACTIVE SUBJECT):
   All new strokes and fills MUST strictly harmonize with and match the existing colors of the subject in the rendered image.
   For example, on a brown moose, use matching brown fur tones (#6d4c41, #795548), tan muzzle tones (#bcaaa4, #d7ccc8), dark brown hooves (#3e2723), or antler tones (#d7ccc8).
   NEVER introduce arbitrary, jarring, or random colors (like bright yellow, neon, or mismatched patches) that do not belong to the subject!

5. STRICT BAN ON "SHADOW SPOTS" / DASH CLUSTERS:
   NEVER generate a scatter of short, disconnected diagonal tick marks, dashed lines, speckles, or spot clusters across the body!
   This looks like dirty measles, noise, or messy scribbles.
   In Cartoon/Cel style and across all art styles, shading must ALWAYS be a single continuous, contiguous shadow plane
   (e.g. ONE smooth, wide crescent stroke along the underside curve, or a solid cel shadow shape), NEVER 10-20 tiny disconnected dash marks!

6. ELIMINATE LOGICAL ERRORS AND STYLE VIOLATIONS:
   Scrutinize the image for logical errors and style violations (e.g. background elements or water lines mistakenly cutting across or intersecting an opaque foreground subject like a duck or moose, inconsistent cartoon/cel inking, or unjoined contours).
   If genuine background intersections or gaps exist, cover and repair them with opaque base strokes matching the subject's local color.

PROGRESSIVE REFINEMENT PIPELINE ACROSS PASSES:
- PASS 1: COMPLETE HOLLOW SHAPES, UNPAINTED REGIONS & BASE ANATOMY
  Inspect the image for unfilled wireframes (e.g. hollow ears, unpainted inner ears, unshaded limbs, missing snout/muzzle tone) and fill them with matching solid base color. (Do NOT paint over solid body areas!).
- PASS 2: FINE ANATOMICAL DETAILS, FACIAL FEATURES & GROUND ANCHORS
  Add secondary anatomy: nostrils, inner ear depth, mouth lines, eye pupils and specular catchlights, hooves/claws, antler ridges, and ground cast shadows.
- PASS 3: VOLUMETRIC FORM MODELING & SURFACE TEXTURE
  Continuous, smooth form shadow sweeps along underside curves (NO spot clusters!). Subtle fur/feather rhythm lines and anatomical planar creases.
- PASS 4: MASTER VECTOR INKING & BRILLIANT SPECULAR LIGHTING
  Weighted master ink contours around the primary silhouette for maximum graphic punch; brilliant specular highlights on head crest, horns/antlers, snout bridge, and eyes.

Output strictly valid JSON matching this schema:
{
  "critique": "Detailed analysis diagnosing hollow/unpainted areas, missing anatomical features, and describing specific corrective phase actions taken.",
  "steps": [
    {
      "cmd": "layer.new.layer",
      "params": {
        "name": "Refinement: Fill Hollow Shapes & Secondary Anatomy"
      }
    },
    {
      "cmd": "paint.stroke",
      "params": {
        "name": "Fill Hollow Ear with Matching Base Color",
        "points": [[240, 250], [255, 270], [230, 270], [240, 250]],
        "size": 12.0,
        "color": "#795548",
        "hardness": 1.0,
        "opacity": 1.0
      }
    },
    {
      "cmd": "layer.new.layer",
      "params": {
        "name": "Refinement: Fine Focal Details & Catchlights"
      }
    },
    {
      "cmd": "paint.stroke",
      "params": {
        "name": "Snout Nostril Definition",
        "points": [[310, 420], [315, 422]],
        "size": 4.0,
        "color": "#3e2723",
        "hardness": 1.0,
        "opacity": 1.0
      }
    },
    {
      "cmd": "paint.stroke",
      "params": {
        "name": "Eye Specular Catchlight Dot",
        "points": [[305, 325], [306, 326]],
        "size": 3.5,
        "color": "#ffffff",
        "hardness": 1.0,
        "opacity": 1.0
      }
    }
  ]
}
"""


def get_refinement_phase_guidance(loop_iteration: int, total_iterations: int = 1, style: str = "realistic") -> str:
    """Return stage-specific artist instructions for progressive refinement loops (Pass 1 to 4)."""
    phase = min(loop_iteration, 4)
    is_cartoon = style.lower() in ("cartoon", "cel")
    is_pencil = style.lower() == "pencil"

    if is_pencil:
        pencil_phases = {
            1: (
                f"=== REFINEMENT PASS 1 OF {total_iterations}: COMPLETE ANATOMICAL ROUGHS & FORGOTTEN FEATURES (PENCIL STYLE) ===\n"
                "MISSION: FLESH OUT HOLLOW AREAS USING ONLY LIGHT GRAPHITE PENCIL STROKES.\n"
                "- STRICT PENCIL ENFORCEMENT: Use ONLY light graphite pencil strokes (#2d3436, #4b5563, #6b7280). ABSOLUTELY NO paint bucket fills, NO solid paint washes, NO hard ink contours!\n"
                "- Infill missing anatomical features (e.g. inner ears, horns, snout lines) with loose gesture and delicate pencil construction lines.\n"
                "- Keep pencil pressure light (opacity <= 0.60, hardness <= 0.65, size <= 2.5)."
            ),
            2: (
                f"=== REFINEMENT PASS 2 OF {total_iterations}: DELICATE DIRECTIONAL CROSS-HATCHING (PENCIL STYLE) ===\n"
                "MISSION: MODEL THREE-DIMENSIONAL VOLUME USING ONLY MINIMAL CROSS-HATCHING.\n"
                "- STRICT RULE: NO PAINT SHADING! Form and depth must be suggested ONLY through fine, directional cross-hatching and diagonal pencil strokes (hardness 0.65, opacity <= 0.50, size <= 2.0).\n"
                "- Keep cross-hatching to a clean minimum, following the structural curvature of the form."
            ),
            3: (
                f"=== REFINEMENT PASS 3 OF {total_iterations}: PRECISION FACIAL & FOCAL DETAILS (PENCIL STYLE) ===\n"
                "MISSION: TIGHTEN FOCAL FACIAL ANATOMY WITH CRISP PENCIL LINEWORK.\n"
                "- Refine focal features with delicate graphite pencil lines (size 1.2-2.0, hardness 0.65): eye contours, iris circles, pupils, expressive mouth lines, and texture accents.\n"
                "- NO thick black marker ink lines!"
            ),
            4: (
                f"=== REFINEMENT PASS 4 OF {total_iterations}: FINAL ANIMATION ROUGH POLISH (PENCIL STYLE) ===\n"
                "MISSION: CLEAN UP ANIMATION KEYFRAME ROUGHS AND ACCENT CONTOURS.\n"
                "- Polish key silhouette contours with weighted graphite lines (size 1.5-2.5, opacity <= 0.65).\n"
                "- Add subtle kneaded-eraser highlights or light graphite accents. NO opaque white paint!"
            ),
        }
        return pencil_phases.get(phase, pencil_phases[1])

    if phase == 1:
        return (
            f"=== REFINEMENT PASS 1 OF {total_iterations}: FLESH OUT HOLLOW AREAS & UNPAINTED BASE SHAPES ===\n"
            "MISSION: COMPLETE UNPAINTED WIREFRAMES AND FORGOTTEN REGIONS.\n"
            "- HOLLOW SHAPE FILLS: Inspect the subject carefully for hollow outlines or wireframe shapes that were left unfilled "
            "(e.g. hollow ears showing background through them, unpainted inner ears, hollow horns/antlers, uncolored snout/muzzle, unshaded limbs). "
            "Fill in each hollow shape with its matching local base color using solid strokes or paint.bucket so every part of the subject is completely solid.\n"
            "- CRITICAL RULE: If the body, torso, and face are ALREADY solidly colored, DO NOT paint broad patches across them! "
            "Never place random shapes across clean, solid body areas.\n"
            "- COLOR HARMONY: Sample and match the existing color palette of the subject (e.g. for a brown moose, use matching brown/tan tones—never arbitrary yellow or mismatched colors!).\n"
            "- STRICT PROHIBITION: DO NOT add noisy shading dots, hatch marks, or shadow spots on Pass 1! Focus on completing hollow shapes and secondary base anatomy."
        )
    elif phase == 2:
        return (
            f"=== REFINEMENT PASS 2 OF {total_iterations}: VOLUMETRIC FORM MODELING & CONTINUOUS SHADOWS ===\n"
            "MISSION: ADD CONTINUOUS FORM SHADOWS AND CLEAN ENVIRONMENTAL GROUNDING.\n"
            "- CONTINUOUS SHADOW PLANES: Add smooth, broad volumetric shadows along the underside curves (e.g. ONE sweeping underside belly shadow curve, "
            "shadow under the neck/head). "
            f"{'In Cartoon/Cel style, shadows MUST be clean, solid contiguous cel-shading shapes—never noisy dots or hatching.' if is_cartoon else 'Shading must be smooth, unified, and continuous.'}\n"
            "- GROUND CONTACT ANCHORS: Anchor the subject with continuous ground cast shadow anchors directly under the feet/hooves (or waterline foam ribbons if on water).\n"
            "- STRICT BAN: NEVER emit rows of small dash marks, speckles, or shadow spots across the body!"
        )
    elif phase == 3:
        return (
            f"=== REFINEMENT PASS 3 OF {total_iterations}: FACIAL FEATURES, FOCAL ANATOMY & FINE DETAILS ===\n"
            "MISSION: ADD PRECISION FACIAL ANATOMY AND FINE DETAILS THAT DIDN'T FIT IN INITIAL PASS.\n"
            "- FACIAL & FOCAL ANATOMY: Refine focal features with high precision: snout nostril dots, inner ear depth/crease lines, expressive mouth/smile lines, "
            "and clean circular eyes with dark pupils.\n"
            "- SECONDARY ANATOMY & DYNAMIC PARTICLES: Detail hooves/claws, antler tines/ridge accents, fur tuft rhythms, or flying water splash particles.\n"
            "- SILHOUETTE UNITY: Close any remaining contour gaps with confident ink lines."
        )
    else:
        return (
            f"=== REFINEMENT PASS {phase} OF {total_iterations}: MASTER VECTOR INKING & BRILLIANT SPECULAR LIGHTING ===\n"
            "MISSION: FINAL GRAPHIC POLISH, MASTER INK CONTOURS, AND BRILLIANT SPECULAR GLEAMS.\n"
            "- MASTER INK CONTOURS: Trace weighted, polished master ink outlines along the primary silhouette and focal contours for maximum contrast and pop.\n"
            "- BRILLIANT SPECULAR HIGHLIGHTS: Add crisp, white specular catchlights on the eye centers, antler/horn tips, snout bridge, and crest gloss.\n"
            "- FINAL CLEANUP: Cover any remaining stray marks with clean background or base tones."
        )


def compose_refinement_with_ollama(
    prompt: str,
    config: PainterConfig,
    current_image: Path,
    loop_iteration: int = 1,
    total_iterations: int = 1,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate targeted refinement brushstrokes using Ollama vision model."""
    import ollama

    client = ollama.Client(host=config.ollama_host)
    model = config.ollama_model
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))

    refinement_images = [str(current_image.resolve())]
    if images:
        for img in images:
            if img.exists() and str(img.resolve()) not in refinement_images:
                refinement_images.append(str(img.resolve()))

    phase_guidance = get_refinement_phase_guidance(loop_iteration, total_iterations, style_preset.id)

    user_text = (
        f"Here is the rendered PNG of the active drawing in progress on a {width}x{height} canvas.\n"
        f"Intended target prompt: '{prompt}'\n"
        f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
        f"Color Mood: {style_preset.color_mood}\n"
        f"Refinement Loop Pass: {loop_iteration} of {total_iterations}\n\n"
        f"{phase_guidance}\n\n"
        "STRICT BAN ON SHADOW SPOTS: Do NOT emit rows of short dashed strokes, spots, or messy speckles across the body! "
        "Every stroke must serve a clear purpose (solid opaque base repair, continuous form shadow, clean boundary inking, or crisp catchlights).\n"
        "Output strictly valid JSON with 'critique' and 'steps'."
    )

    style_system = f"{REFINEMENT_SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"

    try:
        res = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": style_system},
                {
                    "role": "user",
                    "content": user_text,
                    "images": refinement_images,
                },
            ],
            options={
                "num_ctx": 16384,
                "num_predict": 4096,
                "temperature": 0.35,
            },
        )
    except Exception as e:
        err_msg = str(e)
        if "multimodal" in err_msg.lower() or "does not support images" in err_msg.lower():
            raise ValueError(
                f"Model '{model}' does not support vision/image input. "
                f"Please switch to a vision model (e.g. /model llama3.2-vision:11b or /model gpt-4o-mini)."
            ) from e
        raise

    content = res.message.content or ""
    if not content:
        raise ValueError(f"Ollama model '{model}' returned empty content")

    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    if not isinstance(raw_steps, list):
        raise ValueError("Response did not contain a valid 'steps' array")

    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    critique = data.get("critique") or data.get("problems") or (
        f"Refinement Pass {loop_iteration}: Enhancing contrast, defining contours, and adding highlights."
    )

    base_title = data.get("title") or f"{prompt.title()} Refine {loop_iteration}"
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=model)

    return {
        "title": title,
        "critique": str(critique),
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
        "is_refinement": True,
    }


def compose_refinement_with_openai(
    prompt: str,
    config: PainterConfig,
    current_image: Path,
    loop_iteration: int = 1,
    total_iterations: int = 1,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate targeted refinement brushstrokes using OpenAI vision model."""
    import base64
    from openai import OpenAI

    client = OpenAI(
        api_key=config.openai_api_key or "sk-dummy",
        base_url=config.openai_base_url,
    )
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))

    phase_guidance = get_refinement_phase_guidance(loop_iteration, total_iterations, style_preset.id)

    user_text = (
        f"Here is the rendered PNG of the active drawing in progress on a {width}x{height} canvas.\n"
        f"Intended target prompt: '{prompt}'\n"
        f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
        f"Color Mood: {style_preset.color_mood}\n"
        f"Refinement Loop Pass: {loop_iteration} of {total_iterations}\n\n"
        f"{phase_guidance}\n\n"
        "STRICT BAN ON SHADOW SPOTS: Do NOT emit rows of short dashed strokes, spots, or messy speckles across the body! "
        "Every stroke must serve a clear purpose (solid opaque base repair, continuous form shadow, clean boundary inking, or crisp catchlights).\n"
        "Output strictly valid JSON with 'critique' and 'steps'."
    )

    content_parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]

    # In-progress image
    b64_in_prog = base64.b64encode(current_image.read_bytes()).decode("utf-8")
    content_parts.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{b64_in_prog}"},
    })

    # Optional original references
    if images:
        for p in images:
            if p.exists() and p != current_image:
                b64_data = base64.b64encode(p.read_bytes()).decode("utf-8")
                ext = p.suffix.lstrip(".").lower() or "png"
                if ext == "jpg":
                    ext = "jpeg"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{b64_data}"},
                })

    style_system = f"{REFINEMENT_SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"

    response = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": style_system},
            {"role": "user", "content": content_parts},
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )

    content = response.choices[0].message.content or "{}"
    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    critique = data.get("critique") or data.get("problems") or (
        f"Refinement Pass {loop_iteration}: Enhancing contrast, defining contours, and adding highlights."
    )

    base_title = data.get("title") or f"{prompt.title()} Refine {loop_iteration}"
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=config.openai_model)

    return {
        "title": title,
        "critique": str(critique),
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": config.openai_model.strip().replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
        "is_refinement": True,
    }


def compose_refinement_with_gemini(
    prompt: str,
    config: PainterConfig,
    current_image: Path,
    loop_iteration: int = 1,
    total_iterations: int = 1,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate targeted refinement brushstrokes using Google Gemini via OpenAI-compatible endpoint."""
    import base64
    from openai import OpenAI

    api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or config.openai_api_key or "sk-dummy"
    base_url = config.gemini_base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    style_preset = get_style(config.style)
    detail = max(1, min(config.detail_level, 25))

    phase_guidance = get_refinement_phase_guidance(loop_iteration, total_iterations, style_preset.id)

    user_text = (
        f"Here is the rendered PNG of the active drawing in progress on a {width}x{height} canvas.\n"
        f"Intended target prompt: '{prompt}'\n"
        f"Artistic Style: {style_preset.name.upper()} - {style_preset.description}\n"
        f"Color Mood: {style_preset.color_mood}\n"
        f"Refinement Loop Pass: {loop_iteration} of {total_iterations}\n\n"
        f"{phase_guidance}\n\n"
        "STRICT BAN ON SHADOW SPOTS: Do NOT emit rows of short dashed strokes, spots, or messy speckles across the body! "
        "Every stroke must serve a clear purpose (solid opaque base repair, continuous form shadow, clean boundary inking, or crisp catchlights).\n"
        "Output strictly valid JSON with 'critique' and 'steps'."
    )

    content_parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]

    # In-progress image
    b64_in_prog = base64.b64encode(current_image.read_bytes()).decode("utf-8")
    content_parts.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{b64_in_prog}"},
    })

    # Optional original references
    if images:
        for p in images:
            if p.exists() and p != current_image:
                b64_data = base64.b64encode(p.read_bytes()).decode("utf-8")
                ext = p.suffix.lstrip(".").lower() or "png"
                if ext == "jpg":
                    ext = "jpeg"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{b64_data}"},
                })

    style_system = f"{REFINEMENT_SYSTEM_PROMPT}\n\n{style_preset.ai_guidance}"
    gemini_model = (config.gemini_model or "gemini-3.8-flash").strip().replace(" ", "-")

    response = client.chat.completions.create(
        model=gemini_model,
        messages=[
            {"role": "system", "content": style_system},
            {"role": "user", "content": content_parts},
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )

    content = response.choices[0].message.content or "{}"
    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    normalized_steps: list[dict[str, Any]] = []
    for st in raw_steps:
        if isinstance(st, dict):
            normalized_steps.extend(expand_step(st, width, height))

    critique = data.get("critique") or data.get("problems") or (
        f"Refinement Pass {loop_iteration}: Enhancing contrast, defining contours, and adding highlights."
    )

    base_title = data.get("title") or f"{prompt.title()} Refine {loop_iteration}"
    title = format_document_title(base_title, style=config.style, detail_level=detail, model=gemini_model)

    return {
        "title": title,
        "critique": str(critique),
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": gemini_model.replace(":", "-").replace("/", "-"),
        "steps": normalized_steps,
        "is_refinement": True,
    }


def plan_refinement_artwork(
    prompt: str,
    config: PainterConfig,
    current_image: Path,
    loop_iteration: int = 1,
    total_iterations: int = 1,
    width: int = 800,
    height: int = 800,
    images: list[Path] | None = None,
) -> tuple[dict[str, Any], str]:
    """Plan iterative refinement steps given in-progress canvas PNG snapshot.

    Submits current_image back to the AI with stage-specific phase instructions to identify problems
    and generate corrective brushstrokes to get closer to the intended target.
    Honors config.provider and falls back gracefully to procedural plan_refinement_fallback.
    """
    style_preset = get_style(config.style)

    def wrap_plan(p: dict[str, Any], src: str) -> tuple[dict[str, Any], str]:
        if config.style.lower() == "pencil":
            return sanitize_pencil_plan(p), src
        return p, src

    # 0. Offline / procedural fallback requested
    if config.provider in ("none", "fallback", "builtin"):
        logger.info("Using built-in procedural refiner for '%s' (style: %s, loop: %d/%d)", prompt, style_preset.name, loop_iteration, total_iterations)
        plan = plan_refinement_fallback(
            prompt,
            width,
            height,
            detail_level=config.detail_level,
            style=config.style,
            current_image=current_image,
            loop_iteration=loop_iteration,
            total_iterations=total_iterations,
            model="built-in",
        )
        return wrap_plan(plan, f"Built-in Refiner [{style_preset.name}] (Pass {loop_iteration}/{total_iterations})")

    # 1. If Gemini provider is requested
    if config.provider in ("gemini", "google"):
        try:
            plan = compose_refinement_with_gemini(
                prompt, config, current_image, loop_iteration=loop_iteration, total_iterations=total_iterations, width=width, height=height, images=images
            )
            if plan.get("steps"):
                return wrap_plan(plan, f"Gemini ({config.gemini_model}) Pass {loop_iteration}/{total_iterations}")
        except Exception as e:
            logger.warning("Gemini refinement composition failed: %s", e)

    # 2. If OpenAI provider is requested
    if config.provider == "openai":
        try:
            plan = compose_refinement_with_openai(
                prompt, config, current_image, loop_iteration=loop_iteration, total_iterations=total_iterations, width=width, height=height, images=images
            )
            if plan.get("steps"):
                return wrap_plan(plan, f"OpenAI ({config.openai_model}) Pass {loop_iteration}/{total_iterations}")
        except Exception as e:
            logger.warning("OpenAI refinement composition failed: %s", e)

    # 3. Try Ollama (Default or secondary)
    if config.provider == "ollama" or (config.provider not in ("none", "fallback", "builtin") and not config.openai_api_key and not config.openai_base_url and not config.gemini_api_key):
        try:
            plan = compose_refinement_with_ollama(
                prompt, config, current_image, loop_iteration=loop_iteration, total_iterations=total_iterations, width=width, height=height, images=images
            )
            if plan.get("steps"):
                return wrap_plan(plan, f"Ollama ({config.ollama_model}) Pass {loop_iteration}/{total_iterations}")
        except Exception as e:
            logger.warning("Ollama refinement composition failed: %s", e)

    # 4. Try Gemini as secondary if keys are present and not already tried
    if config.provider not in ("gemini", "google") and config.gemini_api_key:
        try:
            plan = compose_refinement_with_gemini(
                prompt, config, current_image, loop_iteration=loop_iteration, total_iterations=total_iterations, width=width, height=height, images=images
            )
            if plan.get("steps"):
                return wrap_plan(plan, f"Gemini ({config.gemini_model}) Pass {loop_iteration}/{total_iterations}")
        except Exception as e:
            logger.warning("Gemini refinement composition failed: %s", e)

    # 5. Try OpenAI as secondary if not already tried and keys are present
    if config.provider != "openai" and (config.openai_api_key or config.openai_base_url):
        try:
            plan = compose_refinement_with_openai(
                prompt, config, current_image, loop_iteration=loop_iteration, total_iterations=total_iterations, width=width, height=height, images=images
            )
            if plan.get("steps"):
                return wrap_plan(plan, f"OpenAI ({config.openai_model}) Pass {loop_iteration}/{total_iterations}")
        except Exception as e:
            logger.warning("OpenAI refinement composition failed: %s", e)

    # 4. Built-in procedural fallback
    logger.info("Using built-in procedural refiner fallback for '%s' (style: %s, pass %d/%d)", prompt, style_preset.name, loop_iteration, total_iterations)
    plan = plan_refinement_fallback(
        prompt,
        width,
        height,
        detail_level=config.detail_level,
        style=config.style,
        current_image=current_image,
        loop_iteration=loop_iteration,
        total_iterations=total_iterations,
        model="built-in",
    )
    return wrap_plan(plan, f"Built-in Refiner [{style_preset.name}] (Pass {loop_iteration}/{total_iterations})")



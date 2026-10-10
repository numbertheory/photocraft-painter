"""Composition engine that translates user prompts into PhotoCraft drawing commands."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from photocraft_painter.fallback_composer import plan_fallback
from photocraft_painter.strokes import smooth_path

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a master artist, painter, and illustrator for PhotoCraft, a native graphic design and painting application.
Your goal is to plan and generate drawing commands that recreate an authentic human artist drawing the user's prompt on a digital canvas.
Keep your internal reasoning very short and concise (under 150 words). Immediately output the JSON illustration plan.

An artist typically works in layers:
1. "Pencil Sketch": loose, expressive sketch lines outlining the subject's anatomy and gestures.
2. "Color Wash": painterly brush strokes blocking in color, textures, and backgrounds.
3. "Shading & Form": deeper tonal brush strokes modeling 3D volume and shadows.
4. "Ink Contours": crisp, confident pen/brush contour lines defining edges and fine details.
5. "Highlights": sparkling accents, glints, and white dabs.

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
        "name": "Sketch: Gesture Curve",
        "points": [[200, 300], [250, 260], [350, 260], [400, 300]],
        "size": 3.0,
        "color": "#7f8c8d",
        "hardness": 0.8
      }
    },
    {
      "cmd": "shape.create",
      "params": {
        "kind": "ellipse",
        "rect": [200, 200, 400, 300],
        "fill": "#ffd700",
        "name": "Color Backdrop"
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
2. "layer.new.layer": Creates a new raster layer to organize the artwork.
   - "name": descriptive layer name (e.g. "Pencil Sketch", "Paint Fill", "Ink Outlines")
3. "shape.create": For backdrop blocks or clean shapes.
   - "kind": "ellipse", "rect", "roundedRect", "polygon", "star"
   - "rect": [x, y, width, height] (3rd and 4th values MUST be WIDTH and HEIGHT, NOT x2/y2!)
   - "fill": hex string or null

Canvas size is 800x800 pixels. Generate expressive steps according to the requested detail level.
Output ONLY the JSON object.
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

    # 1. Layer creation command
    if cmd in ("layer.new.layer", "layer.new", "new.layer"):
        name = str(raw_params.get("name") or "Layer")
        return {"cmd": "layer.new.layer", "params": {"name": name}}

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
            elif len(valid_pts) <= 6:
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

        return {"cmd": "paint.stroke", "params": clean_params}

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


def compose_with_ollama(
    prompt: str, config: PainterConfig, width: int = 800, height: int = 800
) -> dict[str, Any]:
    """Generate drawing steps using local Ollama model."""
    import ollama

    client = ollama.Client(host=config.ollama_host)
    model = config.ollama_model
    detail = max(1, min(config.detail_level, 25))
    detail_info = get_detail_guidance(detail)

    logger.info("Querying Ollama at %s with model '%s' (detail %d/25)...", config.ollama_host, model, detail)

    res = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Create an expressive artist illustration for '{prompt}' on an {width}x{height} canvas.\n"
                    f"Requested Detail: {detail_info}\n"
                    "Use 3 to 6 key waypoint coordinate points per stroke (the engine automatically smooths them into detailed curves).\n"
                    "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
                ),
            },
        ],
        options={
            "num_ctx": 16384,
            "num_predict": 6144,
            "temperature": 0.35,
        },
    )

    content = res.message.content or ""
    if not content:
        raise ValueError(f"Ollama model '{model}' returned empty content (done_reason: {getattr(res, 'done_reason', 'unknown')})")

    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    if not isinstance(raw_steps, list):
        raise ValueError("Response did not contain a valid 'steps' array")

    normalized_steps = [normalize_step(st, width, height) for st in raw_steps if isinstance(st, dict)]

    return {
        "title": data.get("title") or prompt.title(),
        "background": normalize_color(data.get("background")) or "#f8f9fa",
        "width": width,
        "height": height,
        "detail_level": detail,
        "steps": normalized_steps,
    }


def compose_with_openai(
    prompt: str, config: PainterConfig, width: int = 800, height: int = 800
) -> dict[str, Any]:
    """Generate drawing steps using OpenAI-compatible API."""
    from openai import OpenAI

    client = OpenAI(
        api_key=config.openai_api_key or "sk-dummy",
        base_url=config.openai_base_url,
    )
    detail = max(1, min(config.detail_level, 25))
    detail_info = get_detail_guidance(detail)

    response = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Create an expressive artist illustration for '{prompt}' on an {width}x{height} canvas.\n"
                    f"Requested Detail: {detail_info}\n"
                    "Use layers, sketch lines, brush strokes, shading, and inking contours. Output pure JSON."
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )

    content = response.choices[0].message.content or "{}"
    data = extract_json_from_response(content)
    raw_steps = data.get("steps") or []
    normalized_steps = [normalize_step(st, width, height) for st in raw_steps if isinstance(st, dict)]

    return {
        "title": data.get("title") or prompt.title(),
        "background": normalize_color(data.get("background")) or "#f8f9fa",
        "width": width,
        "height": height,
        "detail_level": detail,
        "steps": normalized_steps,
    }


def plan_artwork(
    prompt: str, config: PainterConfig, width: int = 800, height: int = 800
) -> tuple[dict[str, Any], str]:
    """Plan drawing steps for a prompt. Defaults to Ollama, supports OpenAI, and falls back to procedural."""
    detail = max(1, min(config.detail_level, 25))

    # 1. Try Ollama (Default)
    if config.provider == "ollama" or (not config.openai_api_key and not config.openai_base_url):
        try:
            plan = compose_with_ollama(prompt, config, width, height)
            if plan.get("steps"):
                return plan, f"Ollama ({config.ollama_model})"
        except Exception as e:
            logger.warning("Ollama composition failed: %s", e)

    # 2. Try OpenAI if explicitly configured or as secondary option
    if config.openai_api_key or config.openai_base_url:
        try:
            plan = compose_with_openai(prompt, config, width, height)
            if plan.get("steps"):
                return plan, f"OpenAI ({config.openai_model})"
        except Exception as e:
            logger.warning("OpenAI composition failed: %s", e)

    # 3. Built-in procedural fallback
    logger.info("Using built-in procedural composer for '%s' (detail level: %d)", prompt, detail)
    plan = plan_fallback(prompt, width, height, detail_level=detail)
    return plan, f"Built-in Painterly Composer (Detail {detail}/25)"

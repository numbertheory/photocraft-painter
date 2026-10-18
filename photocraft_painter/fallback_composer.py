"""Built-in painterly and vector artwork compositions simulating a human artist with adjustable detail levels (1 to 25)."""

from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Any

from photocraft_painter.strokes import (
    stroke_arc,
    stroke_bezier,
    stroke_enclosed_loop,
    stroke_enclosed_oval,
    stroke_enclosed_rect,
    stroke_hatching,
    stroke_line,
    stroke_painterly_fill,
    stroke_polygon,
    stroke_regular_polygon_vertices,
    stroke_sketch_oval,
    stroke_sketchy_polygon_lines,
    stroke_triangle,
)
from photocraft_painter.styles import STYLE_PRESETS, get_style


def format_document_title(
    base_title: str,
    style: str | None = None,
    detail_level: int | None = None,
    model: str | None = None,
) -> str:
    """Format document title for PhotoCraft with no slashes, <=25 char base title, and bracketed metadata.

    Example: "Woman on Staircase [Painterly][Detail 5][kimi-k3-cloud]"
    """
    raw = str(base_title or "Artwork")

    # Extract existing bracketed and parenthesized metadata if not explicitly provided
    extracted_style = None
    extracted_detail = None
    extracted_model = None

    for b in re.findall(r"\[(.*?)\]", raw):
        b_clean = b.strip()
        m_det = re.match(r"^Detail\s*(\d+)(?:/\d+)?$", b_clean, re.IGNORECASE)
        if m_det:
            if extracted_detail is None:
                extracted_detail = int(m_det.group(1))
            continue
        if b_clean.lower() in STYLE_PRESETS or b_clean.title() in [s.name for s in STYLE_PRESETS.values()]:
            if extracted_style is None:
                extracted_style = b_clean.lower()
            continue
        if extracted_model is None and b_clean:
            extracted_model = b_clean

    for p in re.findall(r"\((.*?)\)", raw):
        p_clean = p.strip()
        m_det = re.match(r"^Detail\s*(\d+)(?:/\d+)?$", p_clean, re.IGNORECASE)
        if m_det and extracted_detail is None:
            extracted_detail = int(m_det.group(1))

    # 1. Clean base title: strip existing bracketed tags and parentheses
    clean = re.sub(r"\[.*?\]", " ", raw)
    clean = re.sub(r"\(.*?\)", " ", clean)
    clean = clean.replace("/", " ").replace("\\", " ").replace(":", " ").replace('"', "").replace("'", "")
    clean = re.sub(r"\s+", " ", clean).strip()

    # Truncate to at most 25 characters without trailing punctuation
    short_title = clean[:25].strip().rstrip(" -_:,.")
    if not short_title:
        short_title = "Artwork"

    # 2. Style tag
    effective_style = style if style is not None else (extracted_style or "realistic")
    style_preset = get_style(effective_style)
    style_name = style_preset.name.strip().title().replace("/", "-").replace(":", "-")

    # 3. Detail tag (strictly NO slashes)
    effective_detail = detail_level if detail_level is not None else (extracted_detail if extracted_detail is not None else 5)
    detail = max(1, min(int(effective_detail), 25))
    detail_tag = f"Detail {detail}"

    # 4. Model tag (replace colons and slashes with dashes)
    effective_model = model if model is not None else (extracted_model or "built-in")
    clean_model = str(effective_model).strip().replace(":", "-").replace("/", "-").replace("\\", "-")
    clean_model = clean_model.replace("[", "").replace("]", "").strip(" -_")
    if not clean_model:
        clean_model = "built-in"

    return f"{short_title} [{style_name}][{detail_tag}][{clean_model}]"


def plan_painterly_rubber_duck(
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an artist sketching and painting a rubber duck.
    
    A higher detail_level (1 to 25) scales the number and density of brushstrokes across all layers.
    At detail level 5, ~50-60 brush strokes are generated; at detail level 25, ~250 brush strokes are generated.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    # =========================================================================
    # STAGE 1: PENCIL SKETCH (Loose graphite guide lines)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Pencil Sketch"}})

    # Water horizon sketch
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Waterline",
            "points": stroke_line(s(60), s(520), s(740), s(520), steps=20, wobble=0.6),
            "size": 3.0,
            "color": "#95a5a6",
            "hardness": 0.8,
            "opacity": 0.7,
        },
    })

    # Body gesture oval
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Body Oval",
            "points": stroke_sketch_oval(s(320), s(420), s(150), s(105), tilt_deg=-4, passes=1.0 + 0.04 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.85,
            "opacity": 0.7,
        },
    })

    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Head Gesture",
                "points": stroke_sketch_oval(s(460), s(290), s(85), s(80), passes=1.0 + 0.04 * detail),
                "size": 3.0,
                "color": "#7f8c8d",
                "hardness": 0.85,
                "opacity": 0.7,
            },
        })

    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Beak Wedge",
                "points": stroke_bezier((s(520), s(310)), (s(570), s(305)), (s(590), s(335)), (s(520), s(345))),
                "size": 2.8,
                "color": "#7f8c8d",
                "hardness": 0.8,
                "opacity": 0.7,
            },
        })

    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Breast Curve",
                "points": stroke_bezier((s(230), s(450)), (s(320), s(510)), (s(420), s(490)), (s(460), s(400))),
                "size": 2.8,
                "color": "#95a5a6",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })

    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Spine Tangent",
                "points": stroke_bezier((s(220), s(390)), (s(300), s(370)), (s(380), s(345)), (s(430), s(310))),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
                "opacity": 0.5,
            },
        })

    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Tail Feather Axis",
                "points": stroke_bezier((s(220), s(390)), (s(160), s(365)), (s(170), s(430)), (s(220), s(440))),
                "size": 2.5,
                "color": "#7f8c8d",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })

    if detail >= 12:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Eye Placement Crosshair H",
                "points": stroke_line(s(435), s(275), s(455), s(275)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Eye Placement Crosshair V",
                "points": stroke_line(s(445), s(265), s(445), s(285)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })

    if detail >= 16:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Water Ripple Oval 1",
                "points": stroke_sketch_oval(s(330), s(535), s(220), s(35), passes=1.1),
                "size": 2.2,
                "color": "#aed6f1",
                "hardness": 0.7,
                "opacity": 0.6,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Water Ripple Oval 2",
                "points": stroke_sketch_oval(s(350), s(560), s(260), s(42), passes=1.0),
                "size": 2.0,
                "color": "#aed6f1",
                "hardness": 0.7,
                "opacity": 0.5,
            },
        })

    if detail >= 20:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Crown Plumage Tangent",
                "points": stroke_bezier((s(430), s(250)), (s(460), s(240)), (s(490), s(250)), (s(510), s(270))),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
                "opacity": 0.5,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Neck Curve Guide",
                "points": stroke_bezier((s(430), s(340)), (s(450), s(370)), (s(440), s(390)), (s(430), s(410))),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
                "opacity": 0.5,
            },
        })

    if detail >= 24:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Deep Reflection Axis",
                "points": stroke_line(s(250), s(620), s(480), s(620)),
                "size": 1.8,
                "color": "#aed6f1",
                "hardness": 0.7,
                "opacity": 0.45,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Chest Bulge Tangent",
                "points": stroke_arc(s(440), s(440), s(30), s(30), 20, 120),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
                "opacity": 0.45,
            },
        })

    # =========================================================================
    # STAGE 2: WATER BASE (Broad painterly brush sweeps)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Water Paint Wash"}})

    water_layers = [
        ("Water Wash: Deep Abyss", (0, s(730)), (s(250), s(710)), (s(550), s(740)), (width, s(720)), 90.0, "#1a5276", 0.95),
        ("Water Wash: Mid Deep", (0, s(670)), (s(280), s(650)), (s(580), s(680)), (width, s(660)), 82.0, "#1f618d", 0.92),
        ("Water Wash: Deep Surface", (0, s(615)), (s(300), s(595)), (s(600), s(625)), (width, s(605)), 74.0, "#2471a3", 0.9),
        ("Water Wash: Mid", (0, s(565)), (s(320), s(545)), (s(580), s(575)), (width, s(560)), 65.0, "#2980b9", 0.9),
        ("Water Wash: Upper Mid", (0, s(535)), (s(340), s(525)), (s(590), s(545)), (width, s(530)), 54.0, "#2e86c1", 0.88),
        ("Water Wash: Surface Swell", (0, s(520)), (s(360), s(512)), (s(600), s(530)), (width, s(518)), 46.0, "#3498db", 0.88),
        ("Water Wash: Horizon Glint", (0, s(512)), (s(380), s(505)), (s(620), s(518)), (width, s(510)), 36.0, "#5dade2", 0.85),
    ]

    w_passes = 1 if detail == 1 else (2 if detail == 2 else (3 if detail <= 5 else min(16, 3 + (detail - 5) // 2 * 2 + (detail % 2))))
    for i in range(w_passes):
        base_layer = water_layers[min(i, len(water_layers) - 1)]
        offset_y = s((i - 3) * 12) if i >= len(water_layers) else 0
        p0 = (base_layer[1][0], base_layer[1][1] + offset_y)
        p1 = (base_layer[2][0], base_layer[2][1] + offset_y)
        p2 = (base_layer[3][0], base_layer[3][1] + offset_y)
        p3 = (base_layer[4][0], base_layer[4][1] + offset_y)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Water Wash: Pass {i+1}",
                "points": stroke_bezier(p0, p1, p2, p3, steps=25),
                "size": max(28.0, base_layer[5] - i * 2.0),
                "color": base_layer[6],
                "hardness": 0.5,
                "opacity": base_layer[7],
            },
        })

    # =========================================================================
    # STAGE 3: COLOR WASH (Painterly yellow & orange blocking)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Duck Body Paint"}})

    if detail <= 5:
        body_sweeps = int(round(3 + (detail - 1) * 1.0))
        head_sweeps = int(round(2 + (detail - 1) * 1.0))
    else:
        body_sweeps = int(round(7 + (detail - 5) * 1.75))
        head_sweeps = int(round(6 + (detail - 5) * 1.35))

    body_spacing = s(190.0 / (body_sweeps + 1))
    head_spacing = s(150.0 / (head_sweeps + 1))
    body_brush_size = max(18.0, s(body_spacing * 2.4))
    head_brush_size = max(15.0, s(head_spacing * 2.4))

    # Body yellow fill strokes
    raw_body_sweeps = stroke_painterly_fill(s(320), s(420), s(140), s(95), spacing=body_spacing)
    for idx in range(body_sweeps):
        sweep = raw_body_sweeps[idx % len(raw_body_sweeps)]
        col = "#ffd700" if (idx % 2 == 0 or detail < 4) else ("#ffda33" if idx % 3 == 0 else "#ffe04d")
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Paint Wash: Body Sweep {idx+1}",
                "points": sweep,
                "size": body_brush_size,
                "color": col,
                "hardness": 0.6,
                "opacity": 0.95,
            },
        })

    # Head yellow fill strokes
    raw_head_sweeps = stroke_painterly_fill(s(460), s(290), s(80), s(75), spacing=head_spacing)
    for idx in range(head_sweeps):
        sweep = raw_head_sweeps[idx % len(raw_head_sweeps)]
        col = "#ffd700" if (idx % 2 == 0 or detail < 4) else "#ffe04d"
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Paint Wash: Head Sweep {idx+1}",
                "points": sweep,
                "size": head_brush_size,
                "color": col,
                "hardness": 0.6,
                "opacity": 0.95,
            },
        })

    # Tail feather wash
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Paint Wash: Tail Base",
            "points": stroke_bezier((s(210), s(410)), (s(160), s(380)), (s(170), s(440)), (s(210), s(440))),
            "size": s(32.0),
            "color": "#ffd700",
            "hardness": 0.65,
        },
    })
    # Beak base wash
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Paint Wash: Beak Base",
            "points": stroke_bezier((s(515), s(325)), (s(555), s(320)), (s(580), s(335)), (s(520), s(345))),
            "size": s(24.0),
            "color": "#ff7a00",
            "hardness": 0.7,
        },
    })

    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Tail Tip",
                "points": stroke_bezier((s(185), s(395)), (s(145), s(370)), (s(155), s(420)), (s(185), s(420))),
                "size": s(22.0),
                "color": "#ffca00",
                "hardness": 0.7,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Beak Top Lip",
                "points": stroke_bezier((s(510), s(318)), (s(545), s(315)), (s(565), s(325)), (s(515), s(330))),
                "size": s(16.0),
                "color": "#ff9100",
                "hardness": 0.75,
            },
        })
    if detail >= 10:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Tail Accent Feather",
                "points": stroke_bezier((s(195), s(405)), (s(150), s(390)), (s(160), s(430)), (s(195), s(430))),
                "size": s(16.0),
                "color": "#ffd700",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Beak Corner Tint",
                "points": stroke_bezier((s(505), s(330)), (s(525), s(335)), (s(540), s(342)), (s(515), s(345))),
                "size": s(12.0),
                "color": "#e65100",
                "hardness": 0.75,
            },
        })
    if detail >= 18:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Tail Feather Fringe",
                "points": stroke_line(s(160), s(385), s(175), s(425)),
                "size": s(10.0),
                "color": "#ffc107",
                "hardness": 0.75,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Paint Wash: Beak Lower Lip Tone",
                "points": stroke_bezier((s(520), s(340)), (s(550), s(342)), (s(565), s(338)), (s(530), s(345))),
                "size": s(11.0),
                "color": "#f57c00",
                "hardness": 0.8,
            },
        })

    # =========================================================================
    # STAGE 4: SHADOWS & VOLUME (Warm shading brush strokes)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Shading & Form"}})

    # Under-belly shadow curve
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shading: Under-Belly",
            "points": stroke_arc(s(320), s(420), s(142), s(95), 40, 160, steps=30),
            "size": s(22.0),
            "color": "#e69500",
            "hardness": 0.6,
            "opacity": 0.85,
        },
    })

    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Wing Underside",
                "points": stroke_bezier((s(260), s(425)), (s(320), s(465)), (s(380), s(465)), (s(400), s(420))),
                "size": s(16.0),
                "color": "#d48800",
                "hardness": 0.7,
                "opacity": 0.85,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Beak Crease",
                "points": stroke_line(s(515), s(345), s(575), s(335), steps=15),
                "size": s(9.0),
                "color": "#cc5200",
                "hardness": 0.8,
            },
        })
    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Cheek Blush",
                "points": stroke_bezier((s(430), s(335)), (s(445), s(340)), (s(460), s(335)), (s(450), s(340))),
                "size": s(16.0),
                "color": "#ff8585",
                "hardness": 0.5,
                "opacity": 0.7,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Under-Chin Shadow",
                "points": stroke_bezier((s(420), s(350)), (s(450), s(365)), (s(480), s(355)), (s(470), s(340))),
                "size": s(15.0),
                "color": "#d48800",
                "hardness": 0.65,
                "opacity": 0.8,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Duck Water Contact Shadow",
                "points": stroke_bezier((s(200), s(515)), (s(320), s(525)), (s(440), s(525)), (s(480), s(505))),
                "size": s(18.0),
                "color": "#154360",
                "hardness": 0.6,
                "opacity": 0.75,
            },
        })

    # Cross-hatching belly texture
    if detail >= 4:
        hatch = 2 if detail == 4 else int(round(4 + (detail - 5) * 1.7))
        hatch_strokes = stroke_hatching(s(310), s(485), s(160), s(35), count=hatch, angle_deg=35)
        for h_idx, h_pts in enumerate(hatch_strokes, start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Shading: Cross-Hatch {h_idx}",
                    "points": h_pts,
                    "size": s(4.0),
                    "color": "#c67d00",
                    "hardness": 0.8,
                    "opacity": 0.65,
                },
            })

    # Wing shading hatching
    if detail >= 8:
        wing_hatch = int(round((detail - 8) * 1.25))
        wing_strokes = stroke_hatching(s(300), s(430), s(100), s(30), count=wing_hatch, angle_deg=-25)
        for w_idx, w_pts in enumerate(wing_strokes, start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Shading: Wing Hatch {w_idx}",
                    "points": w_pts,
                    "size": s(3.5),
                    "color": "#b77900",
                    "hardness": 0.8,
                    "opacity": 0.6,
                },
            })

    # =========================================================================
    # STAGE 5: INKING & CONTOUR LINES (Confident ink pen & brush lines)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Ink Outlines"}})

    # Base 8 ink strokes
    base_inks = [
        ("Ink: Tail Feather", stroke_bezier((s(210), s(385)), (s(165), s(370)), (s(175), s(435)), (s(230), s(455))), s(6.5), "#2c3e50"),
        ("Ink: Back to Neck", stroke_bezier((s(230), s(385)), (s(300), s(375)), (s(380), s(355)), (s(405), s(340))), s(7.0), "#2c3e50"),
        ("Ink: Breast & Belly", stroke_bezier((s(225), s(455)), (s(320), s(515)), (s(420), s(505)), (s(470), s(410))), s(7.5), "#2c3e50"),
        ("Ink: Head Crown", stroke_arc(s(460), s(290), s(82), s(78), 150, 360, steps=35), s(6.5), "#2c3e50"),
        ("Ink: Beak Outline", stroke_bezier((s(495), s(315)), (s(555), s(310)), (s(585), s(332)), (s(515), s(350))), s(6.0), "#873600"),
        ("Ink: Wing Contour", stroke_bezier((s(250), s(415)), (s(315), s(375)), (s(395), s(420)), (s(330), s(470))), s(7.0), "#34495e"),
        ("Ink: Eye Contour", stroke_arc(s(445), s(275), s(15), s(18), 0, 360, steps=25), s(5.0), "#1a1a1a"),
        ("Ink: Eye Pupil", stroke_arc(s(447), s(277), s(9), s(12), 0, 360, steps=20), s(11.0), "#1a1a1a"),
    ]
    for ink_name, ink_pts, ink_sz, ink_col in base_inks:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": ink_name,
                "points": ink_pts,
                "size": ink_sz,
                "color": ink_col,
                "hardness": 0.95,
            },
        })

    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Wing Secondary Feather 1",
                "points": stroke_bezier((s(280), s(425)), (s(325), s(410)), (s(365), s(435)), (s(320), s(460))),
                "size": s(4.5),
                "color": "#2c3e50",
                "hardness": 0.9,
            },
        })
    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Beak Smile Crease",
                "points": stroke_bezier((s(505), s(330)), (s(540), s(328)), (s(570), s(332)), (s(575), s(335))),
                "size": s(4.5),
                "color": "#6e2c00",
                "hardness": 0.95,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Breast Plumage Accent 1",
                "points": stroke_arc(s(435), s(460), s(15), s(12), 40, 160, steps=15),
                "size": s(3.5),
                "color": "#2c3e50",
                "hardness": 0.9,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Breast Plumage Accent 2",
                "points": stroke_arc(s(405), s(480), s(18), s(14), 40, 160, steps=15),
                "size": s(3.5),
                "color": "#2c3e50",
                "hardness": 0.9,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Wing Secondary Feather 2",
                "points": stroke_bezier((s(300), s(435)), (s(340), s(425)), (s(370), s(440)), (s(340), s(455))),
                "size": s(4.0),
                "color": "#2c3e50",
                "hardness": 0.9,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Tail Feather Rib",
                "points": stroke_line(s(185), s(390), s(205), s(425)),
                "size": s(3.0),
                "color": "#2c3e50",
                "hardness": 0.9,
            },
        })
    if detail >= 12:
        for idx, (p0, p1) in enumerate([
            ((s(420), s(440)), (s(435), s(455))),
            ((s(390), s(460)), (s(405), s(475))),
            ((s(360), s(475)), (s(375), s(490))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Feather Texture {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1], steps=10),
                    "size": s(2.8),
                    "color": "#2c3e50",
                    "hardness": 0.9,
                },
            })
    if detail >= 16:
        for idx, (p0, p1, p2, p3) in enumerate([
            ((s(230), s(410)), (s(250), s(430)), (s(270), s(440)), (s(290), s(450))),
            ((s(310), s(390)), (s(330), s(410)), (s(350), s(420)), (s(370), s(425))),
            ((s(470), s(330)), (s(480), s(350)), (s(485), s(370)), (s(480), s(390))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Calligraphy Contour {idx}",
                    "points": stroke_bezier(p0, p1, p2, p3, steps=15),
                    "size": s(3.2),
                    "color": "#34495e",
                    "hardness": 0.95,
                },
            })
    if detail >= 20:
        for idx, (cx, cy) in enumerate([
            (s(445), s(310)), (s(430), s(320)), (s(460), s(330))
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Stipple Plumage {idx}",
                    "points": stroke_arc(cx, cy, s(8), s(6), 30, 150),
                    "size": s(2.5),
                    "color": "#2c3e50",
                    "hardness": 0.9,
                },
            })
    if detail >= 24:
        for idx, (p0, p1) in enumerate([
            ((s(525), s(335)), (s(545), s(338))),
            ((s(180), s(410)), (s(195), s(430))),
            ((s(330), s(450)), (s(345), s(465))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Fine Accent {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1]),
                    "size": s(2.2),
                    "color": "#1a1a1a",
                    "hardness": 0.95,
                },
            })

    # =========================================================================
    # STAGE 6: HIGHLIGHTS & ACCENTS (Glints, sparkles, foam & bubbles)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "6. Highlights & Foam"}})

    # Eye sparkle dot
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Eye Sparkle",
            "points": stroke_line(s(450), s(273), s(450), s(274), steps=4),
            "size": s(6.0),
            "color": "#ffffff",
            "hardness": 1.0,
        },
    })

    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Head Glint",
                "points": stroke_arc(s(460), s(290), s(60), s(60), 220, 260, steps=15),
                "size": s(7.0),
                "color": "#fff3a8",
                "hardness": 0.7,
                "opacity": 0.85,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Detail: Water Ripple 1",
                "points": stroke_bezier((s(150), s(525)), (s(300), s(545)), (s(460), s(545)), (s(620), s(525))),
                "size": s(5.0),
                "color": "#ffffff",
                "hardness": 0.8,
                "opacity": 0.85,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Detail: Bubble 1",
                "points": stroke_arc(s(140), s(485), s(13), s(13), 0, 360, steps=20),
                "size": s(3.0),
                "color": "#ffffff",
                "hardness": 0.9,
            },
        })
    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Detail: Water Ripple 2",
                "points": stroke_bezier((s(210), s(555)), (s(340), s(570)), (s(450), s(570)), (s(560), s(555))),
                "size": s(4.5),
                "color": "#d4efdf",
                "hardness": 0.8,
                "opacity": 0.75,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Detail: Bubble 2",
                "points": stroke_arc(s(180), s(460), s(9), s(9), 0, 360, steps=16),
                "size": s(2.5),
                "color": "#ffffff",
                "hardness": 0.9,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Beak Specular",
                "points": stroke_bezier((s(525), s(322)), (s(545), s(320)), (s(560), s(325)), (s(540), s(324))),
                "size": s(4.0),
                "color": "#fff9c4",
                "hardness": 0.85,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Back Rim Light",
                "points": stroke_bezier((s(240), s(382)), (s(300), s(372)), (s(370), s(355)), (s(400), s(342))),
                "size": s(4.0),
                "color": "#ffffff",
                "hardness": 0.8,
                "opacity": 0.75,
            },
        })

    # Shimmer lines scaling with detail
    if detail >= 5:
        shimmers = int(round(1 + (detail - 5) * 1.2))
        for sh_idx in range(shimmers):
            sy = s(580 + (sh_idx % 8) * 22)
            sx = s(200 + (sh_idx * 37) % 240)
            sw = s(80 + (sh_idx * 29) % 140)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Detail: Water Shimmer {sh_idx+1}",
                    "points": stroke_line(sx, sy, sx + sw, sy, steps=12),
                    "size": s(3.0),
                    "color": "#85c1e9" if sh_idx % 2 == 0 else "#aed6f1",
                    "hardness": 0.7,
                    "opacity": 0.65,
                },
            })

    # Extra bubbles scaling with detail
    if detail >= 10:
        extra_b = int(round((detail - 10) * 0.5))
        for b_idx in range(extra_b):
            bx = s(100 + (b_idx * 67) % 550)
            by = s(470 + (b_idx * 43) % 90)
            br = s(6 + (b_idx % 7))
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Detail: Extra Bubble {b_idx+1}",
                    "points": stroke_arc(bx, by, br, br, 0, 360, steps=16),
                    "size": s(2.2),
                    "color": "#ffffff",
                    "hardness": 0.9,
                },
            })

    bg = "#eef7fa"
    if style_preset.id == "sketchy":
        bg = "#fdfefe"
    elif style_preset.id == "pencil":
        bg = "#ffffff"
    elif style_preset.id == "dreamlike":
        bg = "#16122c"
    elif style_preset.id == "cartoon":
        bg = "#ffffff"
    elif style_preset.id == "abstract":
        bg = "#111822"
    elif style_preset.id == "cubism":
        bg = "#1c1917"

    return {
        "title": format_document_title("Painterly Rubber Duck", style=style, detail_level=detail, model=model),
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_painterly_sunset(
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an artist painting a mountain sunset.
    
    A higher detail_level (1 to 25) scales the number and density of brushstrokes across all layers.
    At detail level 5, ~50-60 brush strokes are generated; at detail level 25, ~250 brush strokes are generated.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    # 1. Sketch layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Composition Sketch"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Horizon Line",
            "points": stroke_line(0, s(520), width, s(520)),
            "size": 3.0,
            "color": "#aed6f1",
            "hardness": 0.7,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Mountain Ridge",
            "points": stroke_bezier((0, s(500)), (s(250), s(320)), (s(450), s(380)), (s(750), s(480))),
            "size": 3.0,
            "color": "#d7bde2",
            "hardness": 0.7,
        },
    })
    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Sun Guide",
                "points": stroke_sketch_oval(s(400), s(360), s(65), s(65), passes=1.0),
                "size": 2.5,
                "color": "#f9e79f",
                "hardness": 0.7,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Foreland Line",
                "points": stroke_line(0, s(680), width, s(680)),
                "size": 2.5,
                "color": "#aed6f1",
                "hardness": 0.6,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Reflection Axis",
                "points": stroke_line(s(400), s(520), s(400), s(750)),
                "size": 2.0,
                "color": "#f9e79f",
                "hardness": 0.6,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Peak 1 Guide",
                "points": stroke_line(s(220), s(340), s(300), s(520)),
                "size": 2.0,
                "color": "#d7bde2",
                "hardness": 0.6,
            },
        })
    if detail >= 12:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Peak 2 Guide",
                "points": stroke_line(s(520), s(360), s(600), s(520)),
                "size": 2.0,
                "color": "#d7bde2",
                "hardness": 0.6,
            },
        })
    if detail >= 16:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Foothills Guide",
                "points": stroke_bezier((s(80), s(480)), (s(200), s(460)), (s(350), s(500)), (s(450), s(510))),
                "size": 2.0,
                "color": "#d7bde2",
                "hardness": 0.6,
            },
        })
    if detail >= 20:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Shoreline Guide",
                "points": stroke_line(0, s(535), width, s(535)),
                "size": 1.8,
                "color": "#aed6f1",
                "hardness": 0.6,
            },
        })
    if detail >= 24:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Atmospheric Zenith Guide",
                "points": stroke_line(0, s(120), width, s(120)),
                "size": 1.8,
                "color": "#aed6f1",
                "hardness": 0.5,
            },
        })

    # 2. Sky gradient paint wash
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Sunset Sky Wash"}})
    all_colors = [
        "#511818", "#641e16", "#78281f", "#922b21", "#a93226", "#b03a2e",
        "#c0392b", "#d35400", "#dc7633", "#e67e22", "#eb984e", "#f39c12",
        "#f5b041", "#f8c471", "#f7dc6f", "#f9e79f", "#fcf3cf", "#fef9e7"
    ]
    if detail <= 5:
        sky_bands = int(round(3 + (detail - 1) * 1.75))
    else:
        sky_bands = int(round(10 + (detail - 5) * 1.25))

    spacing = 490.0 / sky_bands
    for i in range(sky_bands):
        y = s(30 + i * spacing)
        col_idx = int(round(i / max(1, sky_bands - 1) * (len(all_colors) - 1)))
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Sky Wash: Band {i+1}",
                "points": stroke_bezier((0, y), (s(250), y - s(10)), (s(550), y + s(10)), (width, y)),
                "size": max(18.0, s(spacing * 1.4)),
                "color": all_colors[col_idx],
                "hardness": 0.45,
                "opacity": 0.9,
            },
        })

    # 3. Sun & Rays
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Sun & Rays"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sun: Glowing Disk",
            "points": stroke_arc(s(400), s(360), s(55), s(55), 0, 360),
            "size": s(50.0),
            "color": "#fff9c4",
            "hardness": 0.6,
        },
    })
    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sun: Core Halo",
                "points": stroke_arc(s(400), s(360), s(25), s(25), 0, 360),
                "size": s(35.0),
                "color": "#ffffff",
                "hardness": 0.8,
            },
        })
    if detail <= 5:
        rays = max(0, (detail - 2) * 2)
    else:
        rays = int(round(6 + (detail - 5) * 1.2))
    for ri in range(rays):
        angle_deg = -30.0 + ri * (60.0 / max(1, rays - 1)) if rays > 1 else 0.0
        rad = angle_deg * 3.14159 / 180.0
        rx = s(400 + math.cos(rad) * 280)
        ry = s(360 - math.sin(rad) * 240)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Sun: Ray {ri+1}",
                "points": stroke_line(s(400), s(360), rx, ry, steps=15),
                "size": max(3.0, s(12.0 - ri * 0.2)),
                "color": "#fef9e7",
                "hardness": 0.4,
                "opacity": 0.65,
            },
        })

    # 4. Mountain Silhouettes & Crags
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Mountain Silhouettes & Crags"}})
    mountains = [
        [(s(40), s(520)), (s(220), s(340)), (s(380), s(520)), "#4a235a"],
        [(s(320), s(520)), (s(520), s(360)), (s(700), s(520)), "#341f47"],
        [(s(600), s(520)), (s(720), s(420)), (s(800), s(520)), "#2c193e"],
        [(0, s(520)), (s(100), s(430)), (s(240), s(520)), "#211330"],
    ]
    for idx, (p0, p1, p2, col) in enumerate(mountains, start=1):
        steps.append({
            "cmd": "shape.create",
            "params": {
                "kind": "polygon",
                "rect": [p0[0], p1[1], p2[0] - p0[0], p0[1] - p1[1]],
                "sides": 3,
                "fill": col,
                "name": f"Mountain Silhouette {idx}",
            },
        })
    if detail <= 5:
        crags = max(0, (detail - 1) * 2)
    else:
        crags = int(round(8 + (detail - 5) * 2.1))
    for ci in range(crags):
        cx0 = s(120 + (ci * 43) % 550)
        cy0 = s(410 + (ci * 29) % 95)
        cx1 = cx0 + s(25 + (ci * 17) % 35)
        cy1 = cy0 + s(30 + (ci * 13) % 45)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Mountain Texture: Ridge Crag {ci+1}",
                "points": stroke_line(cx0, cy0, cx1, cy1, steps=10, wobble=0.5),
                "size": max(2.5, s(6.0 - (ci % 4) * 0.8)),
                "color": "#5b2c6f" if ci % 2 == 0 else "#6c3483",
                "hardness": 0.8,
                "opacity": 0.7,
            },
        })

    # 5. Lake & Shimmer Reflections
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Lake & Shimmer"}})
    steps.append({
        "cmd": "shape.create",
        "params": {"kind": "rect", "rect": [0, s(520), width, s(280)], "fill": "#1b2631", "name": "Lake Deep Water"},
    })
    if detail <= 5:
        ripples = int(round(4 + (detail - 1) * 5.0))
    else:
        ripples = int(round(24 + (detail - 5) * 5.0))
    for i in range(ripples):
        y = s(530 + i * (250.0 / ripples))
        w = s(120 + i * (460.0 / ripples))
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Lake Shimmer: Ripple {i+1}",
                "points": stroke_line(s(400) - w * 0.5, y, s(400) + w * 0.5, y, steps=12),
                "size": max(2.0, s(8.0 - i * 0.05)),
                "color": "#f39c12" if i % 2 == 0 else "#f5b041",
                "hardness": 0.6,
                "opacity": max(0.35, 0.85 - i * 0.003),
            },
        })

    bg = "#110e1b"
    if style_preset.id == "sketchy":
        bg = "#fbfaf5"
    elif style_preset.id == "pencil":
        bg = "#ffffff"
    elif style_preset.id == "dreamlike":
        bg = "#0d0a21"
    elif style_preset.id == "cartoon":
        bg = "#f0f4f8"
    elif style_preset.id == "abstract":
        bg = "#0f141c"
    elif style_preset.id == "cubism":
        bg = "#1c1917"

    return {
        "title": format_document_title("Mountain Sunset at Dusk", style=style, detail_level=detail, model=model),
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_painterly_racecar(
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an artist sketching and painting an aerodynamic racecar.
    
    A higher detail_level (1 to 25) scales the number and density of brushstrokes across all layers.
    At detail level 5, ~50-60 brush strokes are generated; at detail level 25, ~250 brush strokes are generated.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    # 1. PENCIL SKETCH
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Pencil Sketch"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Ground Line",
            "points": stroke_line(s(60), s(550), s(740), s(550), steps=20, wobble=0.6),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
            "opacity": 0.6,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Chassis Profile",
            "points": stroke_bezier((s(100), s(520)), (s(220), s(410)), (s(560), s(420)), (s(700), s(510))),
            "size": 3.2,
            "color": "#7f8c8d",
            "hardness": 0.85,
            "opacity": 0.7,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Front Wheel Guide",
            "points": stroke_sketch_oval(s(220), s(530), s(55), s(55), passes=1.0 + 0.04 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Rear Wheel Guide",
            "points": stroke_sketch_oval(s(580), s(530), s(60), s(60), passes=1.0 + 0.04 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
        },
    })
    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Cockpit Canopy",
                "points": stroke_bezier((s(320), s(450)), (s(400), s(370)), (s(490), s(380)), (s(540), s(460))),
                "size": 2.8,
                "color": "#95a5a6",
                "hardness": 0.8,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Rear Wing Spoiler",
                "points": stroke_line(s(640), s(420), s(720), s(410), steps=15, wobble=0.4),
                "size": 2.8,
                "color": "#95a5a6",
                "hardness": 0.8,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Front Splitter Guide",
                "points": stroke_line(s(80), s(535), s(170), s(535)),
                "size": 2.5,
                "color": "#95a5a6",
                "hardness": 0.8,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Hood Center Ridge",
                "points": stroke_line(s(160), s(490), s(320), s(440)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 12:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Diffuser Fin 1",
                "points": stroke_line(s(660), s(530), s(710), s(515)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Diffuser Fin 2",
                "points": stroke_line(s(670), s(540), s(720), s(525)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 16:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Sidepod Intake",
                "points": stroke_bezier((s(350), s(460)), (s(380), s(450)), (s(420), s(455)), (s(450), s(470))),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Side Vent Louver",
                "points": stroke_line(s(390), s(470), s(430), s(470)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 20:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Rear Flare Arch",
                "points": stroke_arc(s(580), s(510), s(70), s(50), 160, 340),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Front Flare Arch",
                "points": stroke_arc(s(220), s(510), s(65), s(45), 160, 340),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 24:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Canard Flap 1",
                "points": stroke_line(s(100), s(500), s(130), s(490)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Canard Flap 2",
                "points": stroke_line(s(110), s(515), s(140), s(505)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })

    # 2. CAR BODY WASH
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Car Body Paint"}})
    if detail <= 5:
        sweeps = int(round(4 + (detail - 1) * 3.25))
    else:
        sweeps = int(round(17 + (detail - 5) * 2.8))
    for i in range(sweeps):
        t = i / max(1, sweeps - 1)
        y = s(450 + t * 75)
        x0 = s(120 + t * 35)
        x1 = s(690 - t * 25)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Body Paint: Red Sweep {i+1}",
                "points": stroke_line(x0, y, x1, y, steps=15, wobble=0.6),
                "size": max(10.0, s(36.0 - t * 12)),
                "color": "#e74c3c" if i % 2 == 0 else "#c0392b",
                "hardness": 0.65,
                "opacity": 0.88,
            },
        })

    # 3. WHEELS & COCKPIT
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Wheels & Canopy"}})
    for cx, r, name in [(s(220), s(48), "Front"), (s(580), s(52), "Rear")]:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Tire: {name} Rubber",
                "points": stroke_sketch_oval(cx, s(530), r, r, passes=1.5),
                "size": s(22.0),
                "color": "#1c2833",
                "hardness": 0.85,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Rim: {name} Alloy Rim",
                "points": stroke_sketch_oval(cx, s(530), r * 0.55, r * 0.55, passes=1.0),
                "size": s(10.0),
                "color": "#bdc3c7",
                "hardness": 0.9,
            },
        })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Cockpit: Tinted Windshield",
            "points": stroke_bezier((s(340), s(440)), (s(410), s(385)), (s(480), s(395)), (s(530), s(450))),
            "size": s(26.0),
            "color": "#2c3e50",
            "hardness": 0.7,
            "opacity": 0.9,
        },
    })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rim: Front Star Spokes",
                "points": stroke_line(s(205), s(530), s(235), s(530)),
                "size": s(5.0),
                "color": "#ecf0f1",
                "hardness": 0.95,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rim: Rear Star Spokes",
                "points": stroke_line(s(565), s(530), s(595), s(530)),
                "size": s(5.5),
                "color": "#ecf0f1",
                "hardness": 0.95,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Wheel: Front Brake Caliper",
                "points": stroke_arc(s(220), s(530), s(34), s(34), 40, 80),
                "size": s(6.0),
                "color": "#e74c3c",
                "hardness": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Body: Aerodynamic Side Mirror",
                "points": stroke_bezier((s(370), s(435)), (s(360), s(425)), (s(380), s(420)), (s(385), s(430))),
                "size": s(6.0),
                "color": "#17202a",
                "hardness": 0.9,
            },
        })
    if detail >= 14:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Wheel: Rear Brake Caliper",
                "points": stroke_arc(s(580), s(530), s(37), s(37), 40, 80),
                "size": s(6.5),
                "color": "#e74c3c",
                "hardness": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Cockpit: Racing Halo Rollcage",
                "points": stroke_arc(s(440), s(410), s(35), s(25), 180, 360),
                "size": s(5.0),
                "color": "#34495e",
                "hardness": 0.95,
            },
        })
    if detail >= 20:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rim: Front Center Lock Nut",
                "points": stroke_sketch_oval(s(220), s(530), s(8), s(8), passes=1.0),
                "size": s(4.0),
                "color": "#c0392b",
                "hardness": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rim: Rear Center Lock Nut",
                "points": stroke_sketch_oval(s(580), s(530), s(8), s(8), passes=1.0),
                "size": s(4.0),
                "color": "#c0392b",
                "hardness": 1.0,
            },
        })

    # 4. SHADING & SPEED SHADOWS
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Shading & Shadows"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shadow: Under-Car Asphalt Shadow",
            "points": stroke_line(s(140), s(555), s(680), s(555), steps=20),
            "size": s(22.0),
            "color": "#111116",
            "hardness": 0.6,
            "opacity": 0.75,
        },
    })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Rocker Panel Dark",
                "points": stroke_line(s(280), s(525), s(520), s(525), steps=15),
                "size": s(12.0),
                "color": "#78281f",
                "hardness": 0.8,
            },
        })
    if detail <= 5:
        hatch = max(0, (detail - 3) * 3)
    else:
        hatch = int(round(6 + (detail - 5) * 2.7))
    for hi in range(hatch):
        hx = s(160 + (hi % 8) * 45)
        hy = s(465 + (hi // 8) * 18)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Hatching: Tone Stroke {hi+1}",
                "points": stroke_line(hx, hy, hx + s(25), hy + s(18), steps=8),
                "size": max(1.8, s(3.0 - (hi % 3) * 0.4)),
                "color": "#641e16" if hi % 2 == 0 else "#4a1510",
                "hardness": 0.85,
                "opacity": 0.8,
            },
        })

    # 5. INK CONTOURS
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Ink Outlines"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Aerodynamic Roofline",
            "points": stroke_bezier((s(100), s(520)), (s(220), s(410)), (s(560), s(415)), (s(700), s(510))),
            "size": 3.6,
            "color": "#17202a",
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Front Splitter",
            "points": stroke_line(s(80), s(535), s(160), s(535)),
            "size": 3.5,
            "color": "#17202a",
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Rear Wing Winglet",
            "points": stroke_line(s(640), s(415), s(720), s(405)),
            "size": 3.5,
            "color": "#17202a",
            "hardness": 0.95,
        },
    })
    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Door Seam Cutline",
                "points": stroke_line(s(370), s(440), s(370), s(520)),
                "size": 2.8,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Headlight Bezel",
                "points": stroke_line(s(105), s(505), s(145), s(495)),
                "size": 2.8,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Front Arch Rim",
                "points": stroke_arc(s(220), s(530), s(56), s(56), 170, 350),
                "size": 3.0,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Rear Arch Rim",
                "points": stroke_arc(s(580), s(530), s(61), s(61), 170, 350),
                "size": 3.0,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Diffuser Strake 1",
                "points": stroke_line(s(650), s(540), s(690), s(530)),
                "size": 2.5,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Diffuser Strake 2",
                "points": stroke_line(s(660), s(545), s(700), s(535)),
                "size": 2.5,
                "color": "#17202a",
                "hardness": 0.95,
            },
        })
    if detail >= 12:
        for idx, (p0, p1) in enumerate([
            ((s(300), s(450)), (s(340), s(445))),
            ((s(430), s(445)), (s(470), s(450))),
            ((s(500), s(455)), (s(540), s(460))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Body Panel Seam {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1]),
                    "size": 2.2,
                    "color": "#17202a",
                    "hardness": 0.95,
                },
            })
    if detail >= 16:
        for idx, (p0, p1) in enumerate([
            ((s(140), s(515)), (s(170), s(515))),
            ((s(620), s(515)), (s(650), s(515))),
            ((s(480), s(410)), (s(520), s(420))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Aero Contour Rib {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1]),
                    "size": 2.2,
                    "color": "#17202a",
                    "hardness": 0.95,
                },
            })
    if detail >= 20:
        for idx, (p0, p1) in enumerate([
            ((s(95), s(525)), (s(125), s(525))),
            ((s(630), s(430)), (s(670), s(420))),
            ((s(270), s(510)), (s(310), s(510))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Chassis Accent {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1]),
                    "size": 2.0,
                    "color": "#17202a",
                    "hardness": 0.95,
                },
            })
    if detail >= 24:
        for idx, (p0, p1) in enumerate([
            ((s(150), s(490)), (s(180), s(485))),
            ((s(530), s(490)), (s(560), s(495))),
            ((s(670), s(490)), (s(695), s(495))),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Precision Seam {idx}",
                    "points": stroke_line(p0[0], p0[1], p1[0], p1[1]),
                    "size": 1.8,
                    "color": "#17202a",
                    "hardness": 0.95,
                },
            })

    # 6. HIGHLIGHTS & SPEED ACCENTS
    steps.append({"cmd": "layer.new.layer", "params": {"name": "6. Highlights & Speed Trails"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Hood Specular Glint",
            "points": stroke_bezier((s(240), s(450)), (s(320), s(430)), (s(420), s(435)), (s(480), s(460))),
            "size": 4.0,
            "color": "#ffffff",
            "hardness": 0.85,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Headlight Glow",
            "points": stroke_line(s(110), s(505), s(140), s(500)),
            "size": 7.0,
            "color": "#fff9c4",
            "hardness": 0.7,
        },
    })
    if detail <= 5:
        trails = int(round(2 + (detail - 1) * 2.0))
    else:
        trails = int(round(10 + (detail - 5) * 2.9))
    for si in range(trails):
        sy = s(390 + (si % 12) * 14)
        sx0 = s(680 + (si % 5) * 12)
        sx1 = s(750 + (si % 4) * 14)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Speed Accent: Trail {si+1}",
                "points": stroke_line(sx0, sy, sx1, sy, steps=10),
                "size": max(1.5, s(3.8 - (si % 6) * 0.4)),
                "color": "#e74c3c" if si % 2 == 0 else "#f39c12",
                "hardness": 0.75,
                "opacity": 0.8,
            },
        })

    bg = "#141419"
    if style_preset.id == "sketchy":
        bg = "#fdfefe"
    elif style_preset.id == "pencil":
        bg = "#ffffff"
    elif style_preset.id == "dreamlike":
        bg = "#140e26"
    elif style_preset.id == "cartoon":
        bg = "#ffffff"
    elif style_preset.id == "abstract":
        bg = "#161b22"
    elif style_preset.id == "cubism":
        bg = "#1c1917"

    return {
        "title": format_document_title("Painterly Racecar", style=style, detail_level=detail, model=model),
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_painterly_pikachu(
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an authentic artist illustrating Pikachu.
    
    Uses completely enclosed bounding outlines and the Paint Bucket tool for clean, solid color blocking
    (body, ears, ear-tips, cheeks, eyes, mouth), followed by soft form shading, highlights, and crisp inking.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    yellow_body = "#fedb00"
    amber_shadow = "#d4ac0d" if style_preset.id != "sketchy" else "#566573"
    ear_tip_black = "#181818"
    cheek_red = "#e74c3c" if style_preset.id != "sketchy" else "#7f8c8d"
    cheek_rim = "#c0392b" if style_preset.id != "sketchy" else "#2c3e50"
    mouth_dark = "#922b21" if style_preset.id != "sketchy" else "#2c3e50"
    tongue_pink = "#f1948a" if style_preset.id != "sketchy" else "#bdc3c7"
    ink_color = "#151515" if style_preset.id != "sketchy" else "#1c2833"
    bg_color = (
        "#ffffff" if style_preset.id == "pencil" else
        "#fdfefe" if style_preset.id == "sketchy" else
        "#111822" if style_preset.id == "abstract" else
        "#16122c" if style_preset.id == "dreamlike" else
        "#1c1917" if style_preset.id == "cubism" else
        "#f9fafb"
    )

    # 1. Pencil Sketch
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Pencil Sketch: Pikachu"}})

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Head Gesture Oval",
            "points": stroke_sketch_oval(s(400), s(380), s(150), s(135), passes=1.05),
            "size": 3.0,
            "color": "#95a5a6",
            "hardness": 0.8,
            "opacity": 0.65,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Torso Gesture Oval",
            "points": stroke_sketch_oval(s(400), s(520), s(165), s(140), passes=1.05),
            "size": 3.0,
            "color": "#95a5a6",
            "hardness": 0.8,
            "opacity": 0.65,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Left Ear Vector Axis",
            "points": stroke_line(s(310), s(290), s(140), s(90)),
            "size": 2.5,
            "color": "#bdc3c7",
            "hardness": 0.75,
            "opacity": 0.6,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Right Ear Vector Axis",
            "points": stroke_line(s(490), s(290), s(660), s(90)),
            "size": 2.5,
            "color": "#bdc3c7",
            "hardness": 0.75,
            "opacity": 0.6,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Eye Line Axis",
            "points": stroke_line(s(280), s(380), s(520), s(380)),
            "size": 2.0,
            "color": "#bdc3c7",
            "hardness": 0.7,
            "opacity": 0.5,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Center Facial Symmetry Axis",
            "points": stroke_line(s(400), s(250), s(400), s(580)),
            "size": 2.0,
            "color": "#bdc3c7",
            "hardness": 0.7,
            "opacity": 0.5,
        },
    })

    # 2. Base Flats: Enclosed Bounding Outlines & Paint Bucket Fills
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Base Flats: Paint Bucket"}})

    # Left Ear
    left_ear_pts = [
        (s(270), s(290)),
        (s(220), s(210)),
        (s(170), s(140)),
        (s(135), s(90)),
        (s(165), s(85)),
        (s(225), s(145)),
        (s(275), s(215)),
        (s(315), s(275)),
        (s(270), s(290)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Left Ear (Enclosed)",
            "points": stroke_enclosed_loop(left_ear_pts),
            "size": 4.5,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Left Ear Yellow Base Fill",
            "x": int(s(220)),
            "y": int(s(180)),
            "color": yellow_body,
            "sampleAllLayers": True,
        },
    })

    # Left Ear Black Tip
    left_tip_pts = [
        (s(180), s(140)),
        (s(135), s(90)),
        (s(165), s(85)),
        (s(215), s(135)),
        (s(180), s(140)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Left Ear Black Tip (Enclosed)",
            "points": stroke_enclosed_loop(left_tip_pts),
            "size": 4.5,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Left Ear Tip Black Fill",
            "x": int(s(160)),
            "y": int(s(105)),
            "color": ear_tip_black,
            "sampleAllLayers": True,
        },
    })

    # Right Ear
    right_ear_pts = [
        (s(485), s(275)),
        (s(525), s(215)),
        (s(575), s(145)),
        (s(635), s(85)),
        (s(665), s(90)),
        (s(630), s(140)),
        (s(580), s(210)),
        (s(530), s(290)),
        (s(485), s(275)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Right Ear (Enclosed)",
            "points": stroke_enclosed_loop(right_ear_pts),
            "size": 4.5,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Right Ear Yellow Base Fill",
            "x": int(s(580)),
            "y": int(s(180)),
            "color": yellow_body,
            "sampleAllLayers": True,
        },
    })

    # Right Ear Black Tip
    right_tip_pts = [
        (s(585), s(135)),
        (s(635), s(85)),
        (s(665), s(90)),
        (s(620), s(140)),
        (s(585), s(135)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Right Ear Black Tip (Enclosed)",
            "points": stroke_enclosed_loop(right_tip_pts),
            "size": 4.5,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Right Ear Tip Black Fill",
            "x": int(s(640)),
            "y": int(s(105)),
            "color": ear_tip_black,
            "sampleAllLayers": True,
        },
    })

    # Body & Head Silhouette
    body_pts = [
        (s(315), s(285)),
        (s(360), s(265)),
        (s(400), s(260)),
        (s(440), s(265)),
        (s(485), s(285)),
        (s(535), s(335)),
        (s(565), s(395)),
        (s(575), s(455)),
        (s(565), s(525)),
        (s(535), s(585)),
        (s(475), s(630)),
        (s(400), s(640)),
        (s(325), s(630)),
        (s(265), s(585)),
        (s(235), s(525)),
        (s(225), s(455)),
        (s(235), s(395)),
        (s(265), s(335)),
        (s(315), s(285)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Pikachu Silhouette (Enclosed)",
            "points": stroke_enclosed_loop(body_pts),
            "size": 5.0,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Pikachu Body Yellow Fill",
            "x": int(s(400)),
            "y": int(s(420)),
            "color": yellow_body,
            "sampleAllLayers": True,
        },
    })

    # Red Cheeks
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Left Cheek Circle (Enclosed)",
            "points": stroke_enclosed_oval(s(275), s(465), s(36), s(34)),
            "size": 4.0,
            "color": cheek_rim,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Left Cheek Red Fill",
            "x": int(s(275)),
            "y": int(s(465)),
            "color": cheek_red,
            "sampleAllLayers": True,
        },
    })

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Right Cheek Circle (Enclosed)",
            "points": stroke_enclosed_oval(s(525), s(465), s(36), s(34)),
            "size": 4.0,
            "color": cheek_rim,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Right Cheek Red Fill",
            "x": int(s(525)),
            "y": int(s(465)),
            "color": cheek_red,
            "sampleAllLayers": True,
        },
    })

    # Eyes
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Left Eye (Enclosed)",
            "points": stroke_enclosed_oval(s(335), s(375), s(24), s(28)),
            "size": 3.8,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Left Eye Black Fill",
            "x": int(s(335)),
            "y": int(s(375)),
            "color": ear_tip_black,
            "sampleAllLayers": True,
        },
    })

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Right Eye (Enclosed)",
            "points": stroke_enclosed_oval(s(465), s(375), s(24), s(28)),
            "size": 3.8,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Right Eye Black Fill",
            "x": int(s(465)),
            "y": int(s(375)),
            "color": ear_tip_black,
            "sampleAllLayers": True,
        },
    })

    # Mouth
    mouth_pts = [
        (s(365), s(450)),
        (s(385), s(458)),
        (s(400), s(455)),
        (s(415), s(458)),
        (s(435), s(450)),
        (s(425), s(495)),
        (s(400), s(515)),
        (s(375), s(495)),
        (s(365), s(450)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Mouth (Enclosed)",
            "points": stroke_enclosed_loop(mouth_pts),
            "size": 3.6,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Mouth Interior Deep Red Fill",
            "x": int(s(400)),
            "y": int(s(480)),
            "color": mouth_dark,
            "sampleAllLayers": True,
        },
    })

    tongue_pts = [
        (s(380), s(485)),
        (s(400), s(478)),
        (s(420), s(485)),
        (s(415), s(505)),
        (s(400), s(512)),
        (s(385), s(505)),
        (s(380), s(485)),
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Bounding Outline: Tongue Arc (Enclosed)",
            "points": stroke_enclosed_loop(tongue_pts),
            "size": 3.0,
            "color": mouth_dark,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Tongue Warm Pink Fill",
            "x": int(s(400)),
            "y": int(s(495)),
            "color": tongue_pink,
            "sampleAllLayers": True,
        },
    })

    # 3. Form Shading
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Form Shading & Depth"}})

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shading: Under-Chin Shadow",
            "points": stroke_bezier((s(320), s(580)), (s(400), s(610)), (s(480), s(580)), (s(480), s(580))),
            "size": max(12.0, s(22.0)),
            "color": amber_shadow,
            "hardness": 0.65,
            "opacity": 0.75,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shading: Left Ear Base Tone",
            "points": stroke_bezier((s(270), s(290)), (s(300), s(270)), (s(320), s(260)), (s(340), s(270))),
            "size": max(8.0, s(16.0)),
            "color": amber_shadow,
            "hardness": 0.65,
            "opacity": 0.7,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shading: Right Ear Base Tone",
            "points": stroke_bezier((s(460), s(270)), (s(480), s(260)), (s(500), s(270)), (s(530), s(290))),
            "size": max(8.0, s(16.0)),
            "color": amber_shadow,
            "hardness": 0.65,
            "opacity": 0.7,
        },
    })

    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Left Cheek Form Shadow",
                "points": stroke_arc(s(275), s(475), s(38), s(35), 40, 140),
                "size": max(6.0, s(12.0)),
                "color": amber_shadow,
                "hardness": 0.6,
                "opacity": 0.65,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Shading: Right Cheek Form Shadow",
                "points": stroke_arc(s(525), s(475), s(38), s(35), 40, 140),
                "size": max(6.0, s(12.0)),
                "color": amber_shadow,
                "hardness": 0.6,
                "opacity": 0.65,
            },
        })

    if detail >= 6:
        extra_shading = min(15, detail - 5)
        for idx in range(extra_shading):
            t_shade = (idx + 1) / (extra_shading + 1)
            sy = s(530 + t_shade * 70)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Shading: Lower Torso Depth {idx+1}",
                    "points": stroke_line(s(360 - idx * 5), sy, s(440 + idx * 5), sy),
                    "size": max(6.0, s(14.0 - idx * 0.5)),
                    "color": amber_shadow,
                    "hardness": 0.6,
                    "opacity": 0.6,
                },
            })

    # 4. Highlights & Catchlights
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Highlights & Catchlights"}})

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Left Eye Primary Catchlight",
            "points": stroke_sketch_oval(s(327), s(368), s(8), s(10), passes=1.0),
            "size": 3.0,
            "color": "#ffffff",
            "hardness": 0.95,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Left Eye Catchlight White Fill",
            "x": int(s(327)),
            "y": int(s(368)),
            "color": "#ffffff",
            "sampleAllLayers": True,
        },
    })

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Right Eye Primary Catchlight",
            "points": stroke_sketch_oval(s(457), s(368), s(8), s(10), passes=1.0),
            "size": 3.0,
            "color": "#ffffff",
            "hardness": 0.95,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Paint Bucket: Right Eye Catchlight White Fill",
            "x": int(s(457)),
            "y": int(s(368)),
            "color": "#ffffff",
            "sampleAllLayers": True,
        },
    })

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Left Eye Secondary Pupil Glint",
            "points": [[s(342), s(384), 0.9], [s(344), s(386), 0.9]],
            "size": 3.2,
            "color": "#ffffff",
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Right Eye Secondary Pupil Glint",
            "points": [[s(472), s(384), 0.9], [s(474), s(386), 0.9]],
            "size": 3.2,
            "color": "#ffffff",
            "hardness": 0.95,
        },
    })

    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Left Cheek Specular Arc",
                "points": stroke_arc(s(275), s(455), s(22), s(18), 120, 220),
                "size": 2.8,
                "color": "#ffb3ba",
                "hardness": 0.85,
                "opacity": 0.85,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Right Cheek Specular Arc",
                "points": stroke_arc(s(525), s(455), s(22), s(18), 120, 220),
                "size": 2.8,
                "color": "#ffb3ba",
                "hardness": 0.85,
                "opacity": 0.85,
            },
        })

    # 5. Crisp Ink Contours
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Crisp Ink Contours & Expressions"}})

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Pikachu Nose Dot",
            "points": [[s(397), s(415), 1.0], [s(403), s(415), 1.0], [s(400), s(418), 1.0]],
            "size": 4.0,
            "color": ink_color,
            "hardness": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Left Upper Lip Arc",
            "points": stroke_bezier((s(365), s(450)), (s(380), s(460)), (s(395), s(460)), (s(400), s(453))),
            "size": 3.4,
            "color": ink_color,
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Right Upper Lip Arc",
            "points": stroke_bezier((s(400), s(453)), (s(405), s(460)), (s(420), s(460)), (s(435), s(450))),
            "size": 3.4,
            "color": ink_color,
            "hardness": 0.95,
        },
    })

    if detail >= 4:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Left Ear Silhouette Definition",
                "points": stroke_bezier((s(270), s(290)), (s(220), s(210)), (s(170), s(140)), (s(135), s(90))),
                "size": 3.6,
                "color": ink_color,
                "hardness": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Right Ear Silhouette Definition",
                "points": stroke_bezier((s(530), s(290)), (s(580), s(210)), (s(630), s(140)), (s(665), s(90))),
                "size": 3.6,
                "color": ink_color,
                "hardness": 0.95,
            },
        })

    title = format_document_title("Painterly Pikachu", style=style, detail_level=detail, model=model)
    return {
        "title": title,
        "background": bg_color,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_cubist_dynamic_artwork(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "cubism",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an authentic Analytical & Synthetic Cubist artwork for any prompt.

    Deconstructs the subject into interpenetrating angular geometric planes, multi-perspective
    viewpoints, and high-contrast volumetric facet lighting that leaps off the canvas.
    """
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    # Palette
    canvas_bg = "#1c1917"
    ink_fracture = "#181512"
    guide_axis = "#7d6b55"
    ochre_facet = "#c29b62"
    gold_facet = "#d4ac0d"
    sienna_facet = "#a06535"
    terracotta_facet = "#8c4d2d"
    ivory_facet = "#faead6"
    shadow_facet = "#34495e"
    umber_deep = "#2c2118"
    specular_hi = "#fefae0"

    # 1. Construction & Multi-Perspective Axes
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"1. Analytical Axes: {prompt.title()}"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Diagonal Perspective Grid 1",
            "points": stroke_line(s(100), s(160), s(700), s(640), steps=20),
            "size": 2.2,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.6,
            "linear": True,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Counter-Diagonal Perspective Grid 2",
            "points": stroke_line(s(700), s(160), s(100), s(640), steps=20),
            "size": 2.2,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.6,
            "linear": True,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Vertical Fracture Divide",
            "points": stroke_line(s(400), s(120), s(400), s(680), steps=20),
            "size": 2.2,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.6,
            "linear": True,
        },
    })

    # 2. Background Planar Shards
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Background Spatial Shards"}})
    bg_shards = [
        ("Background Facet: Upper Left Shard", [[s(0), s(0)], [s(350), s(0)], [s(220), s(300)], [s(0), s(220)]], "#2d251f", (s(120), s(100))),
        ("Background Facet: Upper Right Shard", [[s(500), s(0)], [s(800), s(0)], [s(800), s(300)], [s(620), s(200)]], "#3a3128", (s(680), s(100))),
        ("Background Facet: Lower Left Shadow", [[s(0), s(400)], [s(220), s(520)], [s(180), s(800)], [s(0), s(800)]], "#222b35", (s(80), s(620))),
        ("Background Facet: Lower Right Earth", [[s(600), s(500)], [s(800), s(440)], [s(800), s(800)], [s(560), s(800)]], "#3e2d22", (s(700), s(650))),
    ]
    for shard_name, poly_verts, f_col, (cx_pt, cy_pt) in bg_shards:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"{shard_name} (Boundary)",
                "points": stroke_polygon(poly_verts, wobble=0.0, steps_per_side=15, closed=True),
                "size": 3.6,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{shard_name} (Fill)",
                "x": int(round(cx_pt)),
                "y": int(round(cy_pt)),
                "color": f_col,
                "sampleAllLayers": True,
            },
        })

    # 3. Core Subject: Multi-Perspective Angular Facets
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"3. Core Subject Facets ({prompt.title()})"}})
    subject_facets = [
        (
            f"Facet: Frontal Key-Lit Plane ({prompt})",
            [[s(320), s(260)], [s(440), s(220)], [s(460), s(380)], [s(340), s(400)]],
            ivory_facet,
            (s(390), s(315)),
        ),
        (
            f"Facet: Isometric Top Perspective ({prompt})",
            [[s(320), s(260)], [s(440), s(220)], [s(480), s(160)], [s(360), s(180)]],
            gold_facet,
            (s(400), s(205)),
        ),
        (
            f"Facet: Profile Angled Projection ({prompt})",
            [[s(220), s(350)], [s(340), s(280)], [s(340), s(460)], [s(240), s(500)]],
            terracotta_facet,
            (s(285), s(395)),
        ),
        (
            f"Facet: Central Diagonal Ridge Plane ({prompt})",
            [[s(340), s(400)], [s(460), s(380)], [s(520), s(480)], [s(380), s(520)]],
            ochre_facet,
            (s(425), s(445)),
        ),
        (
            f"Facet: Deep Volumetric Shadow Plane ({prompt})",
            [[s(460), s(380)], [s(560), s(320)], [s(580), s(480)], [s(520), s(480)]],
            shadow_facet,
            (s(530), s(415)),
        ),
        (
            f"Facet: Lower Supporting Base Bevel ({prompt})",
            [[s(280), s(520)], [s(520), s(480)], [s(500), s(600)], [s(300), s(620)]],
            sienna_facet,
            (s(400), s(555)),
        ),
        (
            f"Facet: Base Cavity Umber Wedge ({prompt})",
            [[s(300), s(620)], [s(500), s(600)], [s(480), s(660)], [s(320), s(670)]],
            umber_deep,
            (s(400), s(635)),
        ),
    ]

    for f_name, poly_verts, f_col, (cx_pt, cy_pt) in subject_facets:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"{f_name} (Boundary)",
                "points": stroke_polygon(poly_verts, wobble=0.0, steps_per_side=15, closed=True),
                "size": 4.0,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{f_name} (Fill)",
                "x": int(round(cx_pt)),
                "y": int(round(cy_pt)),
                "color": f_col,
                "sampleAllLayers": True,
            },
        })

    # 4. Chiaroscuro Form Hatching & Master Fracture Lines
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Chiaroscuro Hatching & Fracture Lines"}})
    hatch_count = 6 + detail * 2
    for h_i in range(1, hatch_count + 1):
        t_h = h_i / (hatch_count + 1)
        hx0 = s(460 + (t_h - 0.5) * 40)
        hy0 = s(380 + t_h * 80)
        hx1 = hx0 + s(35)
        hy1 = hy0 - s(25)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Cubist Facet Plane Hatch {h_i}",
                "points": stroke_line(hx0, hy0, hx1, hy1, steps=8),
                "size": 2.5,
                "color": ink_fracture,
                "hardness": 0.95,
                "opacity": 0.8,
                "linear": True,
            },
        })

    fracture_edges = [
        ("Master Fracture: Frontal Facet Corner", [[s(320), s(260)], [s(440), s(220)], [s(460), s(380)], [s(340), s(400)]], 4.5),
        ("Master Fracture: Profile Projection Ridge", [[s(220), s(350)], [s(340), s(280)], [s(340), s(460)]], 4.2),
        ("Master Fracture: Central Spatial Ridge", [[s(340), s(400)], [s(460), s(380)], [s(520), s(480)]], 4.4),
        ("Master Fracture: Base Contour Ridge", [[s(280), s(520)], [s(520), s(480)], [s(500), s(600)]], 4.2),
    ]
    for e_name, e_pts, e_sz in fracture_edges:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": e_name,
                "points": stroke_polygon(e_pts, wobble=0.0, steps_per_side=12, closed=False),
                "size": e_sz,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })

    # 5. 3D Facet High-Relief Highlights
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. 3D Facet High-Relief Highlights"}})
    relief_lights = [
        ("Relief Highlight: Frontal Planar Apex", (s(325), s(262)), (s(360), s(250)), 4.0, specular_hi),
        ("Relief Highlight: Top Perspective Ridge", (s(360), s(185)), (s(430), s(215)), 3.8, specular_hi),
        ("Relief Highlight: Profile Projection Leading Edge", (s(225), s(355)), (s(265), s(330)), 4.2, "#ffffff"),
        ("Relief Highlight: Central Ridge Vertex", (s(455), s(375)), (s(470), s(385)), 4.5, "#ffffff"),
        ("Relief Highlight: Base Bevel Facet Glint", (s(320), s(525)), (s(380), s(515)), 3.5, specular_hi),
    ]
    for l_name, (lx0, ly0), (lx1, ly1), l_sz, l_col in relief_lights:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": l_name,
                "points": stroke_line(lx0, ly0, lx1, ly1, steps=8),
                "size": l_sz,
                "color": l_col,
                "hardness": 0.98,
                "opacity": 0.95,
                "linear": True,
            },
        })

    if detail >= 6:
        extra_facets = int(round((detail - 5) * 1.5))
        for ef_i in range(min(extra_facets, 30)):
            ang_f = (ef_i * 0.45) % math.pi
            ef_cx = s(400 + math.cos(ang_f) * (70 + (ef_i % 4) * 35))
            ef_cy = s(400 + math.sin(ang_f) * (70 + (ef_i % 4) * 35))
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Cubist Micro-Facet Edge {ef_i + 1}",
                    "points": stroke_line(ef_cx - s(15), ef_cy - s(10), ef_cx + s(15), ef_cy + s(10), steps=6),
                    "size": 2.2,
                    "color": ink_fracture if ef_i % 2 == 0 else specular_hi,
                    "hardness": 0.95,
                    "opacity": 0.85,
                    "linear": True,
                },
            })

    title = format_document_title(f"Cubist {prompt.title()}", style="cubism", detail_level=detail, model=model)
    return {
        "title": title,
        "width": width,
        "height": height,
        "background": canvas_bg,
        "detail_level": detail,
        "style": "cubism",
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_dynamic_artwork(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate an authentic custom painterly study dynamically themed around any arbitrary prompt.
    
    A higher detail_level (1 to 25) scales the number and density of brushstrokes across all layers.
    At detail level 5, ~50-60 brush strokes are generated; at detail level 25, ~250 brush strokes are generated.
    """
    style_preset = get_style(style)
    if style_preset.id == "cubism":
        return plan_cubist_dynamic_artwork(prompt, width, height, detail_level=detail_level, style=style, model=model)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    # Choose a harmonious palette deterministically seeded by the prompt
    h = sum(ord(c) for c in prompt.lower())
    palettes = [
        {"bg": "#121820", "wash": "#3498db", "mid": "#2980b9", "dark": "#1b4f72", "accent": "#f39c12", "ink": "#0e1724"},
        {"bg": "#1e141a", "wash": "#e74c3c", "mid": "#c0392b", "dark": "#78281f", "accent": "#f1c40f", "ink": "#181014"},
        {"bg": "#111b15", "wash": "#2ecc71", "mid": "#27ae60", "dark": "#196f3d", "accent": "#f39c12", "ink": "#0b140e"},
        {"bg": "#191522", "wash": "#9b59b6", "mid": "#8e44ad", "dark": "#512e5f", "accent": "#1abc9c", "ink": "#130f1b"},
        {"bg": "#1d1916", "wash": "#e67e22", "mid": "#d35400", "dark": "#873600", "accent": "#3498db", "ink": "#17120e"},
    ]
    pal = dict(palettes[h % len(palettes)])
    if style_preset.id == "sketchy":
        pal = {"bg": "#fdfefe", "wash": "#7f8c8d", "mid": "#566573", "dark": "#2c3e50", "accent": "#bdc3c7", "ink": "#1c2833"}
    elif style_preset.id == "dreamlike":
        pal = {
            "bg": "#120d24",
            "wash": style_preset.adjust_color(pal["wash"], 1.1) or "#a569bd",
            "mid": style_preset.adjust_color(pal["mid"], 1.0) or "#8e44ad",
            "dark": style_preset.adjust_color(pal["dark"], 0.9) or "#4a235a",
            "accent": "#f9e79f",
            "ink": "#2e1c4a",
        }
    elif style_preset.id == "cartoon":
        pal = {
            "bg": "#ffffff",
            "wash": style_preset.adjust_color(pal["wash"], 1.15) or "#e74c3c",
            "mid": style_preset.adjust_color(pal["mid"], 1.1) or "#c0392b",
            "dark": style_preset.adjust_color(pal["dark"], 1.0) or "#922b21",
            "accent": "#f1c40f",
            "ink": "#000000",
        }
    elif style_preset.id == "abstract":
        pal = {
            "bg": "#17202a",
            "wash": style_preset.adjust_color(pal["wash"], 1.2) or "#e67e22",
            "mid": style_preset.adjust_color(pal["mid"], 1.1) or "#d35400",
            "dark": style_preset.adjust_color(pal["dark"], 0.8) or "#1b2631",
            "accent": "#00ffff",
            "ink": "#fdfefe",
        }
    elif style_preset.id == "pencil":
        pal = {
            "bg": "#ffffff",
            "wash": "#6b7280",
            "mid": "#4b5563",
            "dark": "#374151",
            "accent": "#9ca3af",
            "ink": "#374151",
        }

    # 1. Sketch layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"1. Sketch: {prompt.title()}"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"Sketch: Gesture Oval ({prompt})",
            "points": stroke_sketch_oval(s(400), s(400), s(160), s(140), passes=1.0 + 0.04 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
            "opacity": 0.7,
        },
    })
    if detail >= 2:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Dynamic Gesture Arc",
                "points": stroke_bezier((s(240), s(520)), (s(360), s(260)), (s(440), s(260)), (s(560), s(520))),
                "size": 3.0,
                "color": "#95a5a6",
                "hardness": 0.8,
            },
        })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Center Balance Axis",
                "points": stroke_line(s(400), s(240), s(400), s(560)),
                "size": 2.5,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Secondary Counter-Oval",
                "points": stroke_sketch_oval(s(400), s(400), s(110), s(90), passes=1.0),
                "size": 2.5,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Dynamic Tangent",
                "points": stroke_bezier((s(260), s(340)), (s(340), s(300)), (s(460), s(300)), (s(540), s(340))),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 12:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Diagonal Guide 1",
                "points": stroke_line(s(280), s(280), s(520), s(520)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Diagonal Guide 2",
                "points": stroke_line(s(280), s(520), s(520), s(280)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 16:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Harmonic Arc 1",
                "points": stroke_arc(s(400), s(400), s(190), s(170), 30, 150),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Harmonic Arc 2",
                "points": stroke_arc(s(400), s(400), s(190), s(170), 210, 330),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.7,
            },
        })
    if detail >= 20:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Focal Crosshair H",
                "points": stroke_line(s(370), s(380), s(430), s(380)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.6,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Focal Crosshair V",
                "points": stroke_line(s(400), s(350), s(400), s(410)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.6,
            },
        })
    if detail >= 24:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Outer Envelope 1",
                "points": stroke_line(s(200), s(400), s(600), s(400)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.5,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Outer Envelope 2",
                "points": stroke_line(s(400), s(200), s(400), s(600)),
                "size": 1.8,
                "color": "#bdc3c7",
                "hardness": 0.5,
            },
        })

    # 2. Base Flats: Enclosed Bounding Outlines & Paint Bucket Fills
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Base Color Flats: Paint Bucket"}})

    # Main silhouette bounding outline (strictly enclosed)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"Bounding Outline: Silhouette ({prompt})",
            "points": stroke_enclosed_oval(s(400), s(400), s(165), s(145)),
            "size": 4.5,
            "color": pal["ink"],
            "hardness": 0.95,
            "opacity": 1.0,
        },
    })
    if style_preset.id != "pencil":
        # Clean Paint Bucket flood fill inside the completely enclosed boundary
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"Paint Bucket: Silhouette Base Flat ({prompt})",
                "x": int(s(400)),
                "y": int(s(400)),
                "color": pal["wash"],
                "sampleAllLayers": True,
            },
        })

    if detail >= 2:
        # Inner focal zone bounding contour + secondary fill
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Bounding Outline: Inner Focal Zone",
                "points": stroke_enclosed_oval(s(400), s(400), s(115), s(95)),
                "size": 3.8 if style_preset.id != "pencil" else 2.2,
                "color": pal["ink"],
                "hardness": 0.95 if style_preset.id != "pencil" else 0.65,
                "opacity": 1.0 if style_preset.id != "pencil" else 0.55,
            },
        })
        if style_preset.id != "pencil":
            steps.append({
                "cmd": "paint.bucket",
                "params": {
                    "name": "Paint Bucket: Inner Focal Flat",
                    "x": int(s(400)),
                    "y": int(s(400)),
                    "color": pal["mid"],
                    "sampleAllLayers": True,
                },
            })

    # Painterly surface glazes and textures over the solid flat (scales with detail level)
    if detail <= 5:
        glazes = int(round(2 + (detail - 1) * 1.0))
    else:
        glazes = int(round(6 + (detail - 5) * 1.5))
    for i in range(glazes):
        t = (i + 1) / (glazes + 1)
        y = s(310 + t * 180)
        w = s(80 + (1.0 - abs(t - 0.5) * 2) * 60)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Color Glaze: Texture Accents {i+1}",
                "points": stroke_line(s(400) - w, y, s(400) + w, y, steps=10, wobble=0.3),
                "size": max(8.0, s(20.0 - t * 4)),
                "color": pal["wash"] if i % 2 == 0 else pal["mid"],
                "hardness": 0.6,
                "opacity": 0.55,
            },
        })

    # 3. Form Shading
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Form & Volume Shading"}})
    if detail <= 5:
        shading = int(round(2 + (detail - 1) * 2.5))
    else:
        shading = int(round(12 + (detail - 5) * 3.1))
    for si in range(shading):
        st = si / max(1, shading - 1)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Shading: Form Tone {si+1}",
                "points": stroke_bezier((s(270 + st * 40), s(450 + st * 30)), (s(380), s(520)), (s(460), s(520)), (s(530 - st * 30), s(460 + st * 20))),
                "size": max(8.0, s(24.0 - si * 0.2)),
                "color": pal["dark"],
                "hardness": 0.7,
                "opacity": 0.85,
            },
        })

    # 4. Ink Contours
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Ink Contours"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Main Silhouette Outline",
            "points": stroke_sketch_oval(s(400), s(400), s(165), s(145), passes=1.0),
            "size": 3.8,
            "color": pal["ink"],
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Interior Rhythm Arc",
            "points": stroke_bezier((s(260), s(420)), (s(380), s(320)), (s(450), s(320)), (s(540), s(440))),
            "size": 3.2,
            "color": pal["ink"],
            "hardness": 0.95,
        },
    })
    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Focal Contour Arc",
                "points": stroke_arc(s(400), s(400), s(120), s(100), 200, 340),
                "size": 3.0,
                "color": pal["ink"],
                "hardness": 0.95,
            },
        })
    if detail >= 5:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Core Crest Rim",
                "points": stroke_arc(s(400), s(370), s(70), s(60), 160, 320),
                "size": 2.8,
                "color": pal["ink"],
                "hardness": 0.95,
            },
        })
    if detail >= 8:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Interior Rhythm Line 1",
                "points": stroke_line(s(350), s(360), s(450), s(440)),
                "size": 2.5,
                "color": pal["ink"],
                "hardness": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Ink: Interior Rhythm Line 2",
                "points": stroke_line(s(450), s(360), s(350), s(440)),
                "size": 2.5,
                "color": pal["ink"],
                "hardness": 0.95,
            },
        })
    if detail >= 12:
        for idx in range(3):
            ay = s(360 + idx * 30)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Calligraphy Accent {idx+1}",
                    "points": stroke_line(s(340), ay, s(460), ay),
                    "size": 2.2,
                    "color": pal["ink"],
                    "hardness": 0.95,
                },
            })
    if detail >= 16:
        for idx in range(3):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Stipple Ring {idx+1}",
                    "points": stroke_arc(s(400), s(400), s(90 + idx * 25), s(70 + idx * 20), 40, 140),
                    "size": 2.0,
                    "color": pal["ink"],
                    "hardness": 0.95,
                },
            })
    if detail >= 20:
        for idx in range(3):
            ax = s(330 + idx * 70)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Form Cadence {idx+1}",
                    "points": stroke_line(ax, s(350), ax, s(450)),
                    "size": 1.8,
                    "color": pal["ink"],
                    "hardness": 0.95,
                },
            })
    if detail >= 24:
        for idx in range(3):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Ink: Fine Detailing {idx+1}",
                    "points": stroke_arc(s(400), s(400), s(140 + idx * 15), s(120 + idx * 10), 10, 80),
                    "size": 1.8,
                    "color": pal["ink"],
                    "hardness": 0.95,
                },
            })

    # 5. Highlights & Accents
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Specular Highlights"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Primary Focal Glint",
            "points": stroke_line(s(370), s(320), s(410), s(310)),
            "size": 5.0,
            "color": "#ffffff",
            "hardness": 0.85,
            "opacity": 0.95,
        },
    })
    if detail <= 5:
        accents = int(round(1 + (detail - 1) * 2.25))
    else:
        accents = int(round(10 + (detail - 5) * 2.1))
    for ai in range(accents):
        ay = s(310 + (ai % 10) * 18)
        ax = s(320 + (ai * 37) % 160)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Accent: Tint {ai+1}",
                "points": stroke_line(ax, ay, ax + s(30), ay),
                "size": max(2.0, s(6.0 - (ai % 5) * 0.6)),
                "color": pal["accent"],
                "hardness": 0.75,
                "opacity": 0.85,
            },
        })

    return {
        "title": format_document_title(prompt.title(), style=style, detail_level=detail, model=model),
        "width": width,
        "height": height,
        "background": pal["bg"],
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def is_portrait_or_face_prompt(prompt: str, images: list[Path] | None = None) -> bool:
    """Detect whether a prompt or reference image depicts a human face or portrait."""
    lowered = prompt.lower()

    # Negative override: explicit non-portrait subjects unless portrait words are also present
    non_portraits = (
        "car", "racecar", "auto", "vehicle", "duck", "rubber duck",
        "sunset", "mountain", "landscape", "pikachu", "pokemon", "building", "cityscape"
    )
    tokens = set(re.findall(r"\b[a-z0-9_'-]+\b", lowered))
    portrait_keys = (
        "woman", "man", "girl", "boy", "person", "lady", "gentleman", "child", "baby",
        "human", "people", "figure", "portrait", "face", "head", "self-portrait",
        "bust", "profile", "visage", "goddess", "god", "queen", "king", "prince", "princess",
        "model", "actress", "actor", "venus", "bov", "botticelli", "mona", "lisa", "monalisa",
        "eyes", "lips", "smile", "cheeks",
    )

    if any(k in tokens for k in portrait_keys):
        return True

    # Multi-word phrases
    phrases = (
        "draw a man", "draw a woman", "man or woman", "birth of venus", "mona lisa",
        "portrait of", "face of", "human figure", "girl with", "woman with", "man with"
    )
    if any(ph in lowered for ph in phrases):
        return True

    if images:
        for img in images:
            stem = img.stem.lower()
            stem_tokens = set(re.findall(r"\b[a-z0-9_'-]+\b", stem.replace("-", " ").replace("_", " ")))
            if any(k in stem_tokens for k in portrait_keys):
                return True
            if "bov" in stem or "venus" in stem or "portrait" in stem or "face" in stem:
                return True

    return False


def plan_cubist_portrait(
    prompt: str = "portrait",
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "cubism",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an authentic Analytical & Synthetic Cubist portrait.

    Deconstructs the human subject into interpenetrating geometric planes, polyhedral facets,
    and multiple simultaneous perspectives (e.g. interlocking profile nose/brow intersecting
    frontal eye, cheek, and lips), with sharp angular edges and high-contrast volumetric facet
    lighting that leaps dramatically off the 2D surface.
    """
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    lowered = prompt.lower()
    is_venus = any(k in lowered for k in ("venus", "bov", "botticelli", "goddess", "aphrodite"))
    is_male = any(k in lowered for k in ("man", "male", "gentleman", "boy", "guy", "king", "prince"))

    # Earthy Analytical Cubism Palette
    canvas_bg = "#1c1917"       # Raw umber / deep charcoal canvas
    ink_fracture = "#181512"    # Pitch charcoal fracture line
    guide_axis = "#7d6b55"      # Earthy umber drafting axis
    ochre_facet = "#c29b62"     # Raw ochre key-lit planar facet
    gold_facet = "#d4a34b"      # Golden amber profile facet
    sienna_facet = "#a06535"    # Warm burnt sienna midtone facet
    terracotta_facet = "#8c4d2d"# Terracotta pop facet
    ivory_facet = "#faead6"     # Radiant frontal ivory facet
    shadow_facet = "#34495e"    # Cool slate counter-shadow facet
    umber_deep = "#2c2118"      # Deep raw umber cavity shadow
    lip_profile = "#b85955"     # Profile lip facet
    lip_frontal = "#d97736"     # Frontal terracotta lip facet
    lip_shadow = "#4a1c18"      # Deep angular lip parting
    iris_col = "#5c4033" if is_male else "#6e7a48"
    specular_hi = "#fefae0"     # Ivory specular high-relief highlight

    # =========================================================================
    # LAYER 1: ANALYTICAL CONSTRUCTION & MULTI-PERSPECTIVE AXES
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Analytical Construction: Multi-Perspective Axes"}})

    # Central bisecting facial ridge axis
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Central Bisecting Facial Ridge",
            "points": stroke_line(s(410), s(140), s(420), s(530), steps=20),
            "size": 2.5,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.65,
            "linear": True,
        },
    })
    # Diagonal perspective fracture line 1 (45 deg)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Diagonal Spatial Fracture 1",
            "points": stroke_line(s(120), s(180), s(680), s(620), steps=20),
            "size": 2.0,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.55,
            "linear": True,
        },
    })
    # Diagonal perspective fracture line 2 (counter-angle)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Counter-Diagonal Spatial Fracture 2",
            "points": stroke_line(s(680), s(160), s(160), s(660), steps=20),
            "size": 2.0,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.55,
            "linear": True,
        },
    })
    # Dual eye-line axes (differing angles reflecting multiple viewpoints)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Profile Viewpoint Eye-Axis",
            "points": stroke_line(s(330), s(310), s(410), s(290), steps=12),
            "size": 2.0,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.6,
            "linear": True,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Analytical Axis: Frontal Viewpoint Eye-Axis",
            "points": stroke_line(s(410), s(320), s(520), s(310), steps=12),
            "size": 2.0,
            "color": guide_axis,
            "hardness": 0.95,
            "opacity": 0.6,
            "linear": True,
        },
    })

    # =========================================================================
    # LAYER 2: BACKGROUND PLANAR SHARDS & SPATIAL FRACTURES
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Background Spatial Shards"}})

    bg_shards = [
        (
            "Background Facet: Upper Left Shard",
            [[s(0), s(0)], [s(340), s(0)], [s(210), s(280)], [s(0), s(200)]],
            "#2d251f",
            (s(120), s(100)),
        ),
        (
            "Background Facet: Upper Right Shard",
            [[s(520), s(0)], [s(800), s(0)], [s(800), s(280)], [s(640), s(180)]],
            "#3a3128",
            (s(680), s(100)),
        ),
        (
            "Background Facet: Lower Left Slate Shadow",
            [[s(0), s(420)], [s(200), s(520)], [s(170), s(800)], [s(0), s(800)]],
            "#222b35",
            (s(80), s(620)),
        ),
        (
            "Background Facet: Lower Right Terracotta Ground",
            [[s(620), s(510)], [s(800), s(450)], [s(800), s(800)], [s(560), s(800)]],
            "#3e2d22",
            (s(700), s(650)),
        ),
    ]
    for shard_name, poly_verts, f_col, (cx_pt, cy_pt) in bg_shards:
        outline_pts = stroke_polygon(poly_verts, wobble=0.0, steps_per_side=15, closed=True)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"{shard_name} (Boundary)",
                "points": outline_pts,
                "size": 3.6,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{shard_name} (Fill)",
                "x": int(round(cx_pt)),
                "y": int(round(cy_pt)),
                "color": f_col,
                "sampleAllLayers": True,
            },
        })

    # =========================================================================
    # LAYER 3: TORSO & ANGULAR SHOULDERS (DUAL PERSPECTIVE)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Torso & Shoulders: Multi-Perspective Planes"}})

    # Left shoulder seen in 3/4 profile trapezoid
    left_shoulder_verts = [[s(180), s(620)], [s(390), s(520)], [s(370), s(780)], [s(120), s(780)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shoulder Facet: Left Profile Plane (Boundary)",
            "points": stroke_polygon(left_shoulder_verts, wobble=0.0, steps_per_side=16, closed=True),
            "size": 4.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Shoulder Facet: Left Profile Plane (Fill)",
            "x": int(s(260)),
            "y": int(s(660)),
            "color": terracotta_facet,
            "sampleAllLayers": True,
        },
    })

    # Right shoulder seen in frontal planar triangle
    right_shoulder_verts = [[s(420), s(520)], [s(660), s(610)], [s(720), s(780)], [s(440), s(780)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Shoulder Facet: Right Frontal Plane (Boundary)",
            "points": stroke_polygon(right_shoulder_verts, wobble=0.0, steps_per_side=16, closed=True),
            "size": 4.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Shoulder Facet: Right Frontal Plane (Fill)",
            "x": int(s(550)),
            "y": int(s(670)),
            "color": ochre_facet,
            "sampleAllLayers": True,
        },
    })

    # Neck column: Key-lit facet & shadow facet
    neck_light_verts = [[s(380), s(450)], [s(430), s(450)], [s(435), s(535)], [s(390), s(535)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Neck Facet: Key-Lit Planar Column (Boundary)",
            "points": stroke_polygon(neck_light_verts, wobble=0.0, steps_per_side=12, closed=True),
            "size": 3.8,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Neck Facet: Key-Lit Planar Column (Fill)",
            "x": int(s(410)),
            "y": int(s(490)),
            "color": gold_facet,
            "sampleAllLayers": True,
        },
    })

    neck_shadow_verts = [[s(430), s(450)], [s(475), s(460)], [s(485), s(540)], [s(435), s(535)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Neck Facet: Umber Shadow Column (Boundary)",
            "points": stroke_polygon(neck_shadow_verts, wobble=0.0, steps_per_side=12, closed=True),
            "size": 3.8,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Neck Facet: Umber Shadow Column (Fill)",
            "x": int(s(455)),
            "y": int(s(495)),
            "color": umber_deep,
            "sampleAllLayers": True,
        },
    })

    # =========================================================================
    # LAYER 4: DECONSTRUCTED HEAD & FACIAL PLANES
    # Multi-perspective: Profile planes on left + Frontal planes on right
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Deconstructed Head & Facial Planes"}})

    head_facets = [
        (
            "Head Facet: Profile Forehead & Temple",
            [[s(340), s(180)], [s(415), s(150)], [s(410), s(280)], [s(325), s(260)]],
            ochre_facet,
            (s(370), s(220)),
        ),
        (
            "Head Facet: Frontal Forehead Key-Light Plane",
            [[s(415), s(150)], [s(515), s(185)], [s(485), s(290)], [s(410), s(280)]],
            ivory_facet,
            (s(455), s(230)),
        ),
        (
            "Head Facet: Profile Nose & Brow Projection",
            # Sharp angular triangle jutting out in pure profile to the left!
            [[s(410), s(280)], [s(335), s(355)], [s(415), s(385)]],
            gold_facet,
            (s(385), s(340)),
        ),
        (
            "Head Facet: Left Profile Cheek & Jaw Plane",
            [[s(325), s(260)], [s(415), s(385)], [s(385), s(470)], [s(305), s(380)]],
            sienna_facet,
            (s(355), s(380)),
        ),
        (
            "Head Facet: Frontal Right Cheek & Zygomatic Plane",
            [[s(410), s(280)], [s(485), s(290)], [s(525), s(395)], [s(435), s(415)]],
            ivory_facet,
            (s(465), s(350)),
        ),
        (
            "Head Facet: Central Chiaroscuro Shadow Ridge",
            # Interlocking central shadow facet providing dramatic 3D volumetric pop!
            [[s(415), s(385)], [s(435), s(415)], [s(440), s(475)], [s(385), s(470)]],
            shadow_facet,
            (s(418), s(435)),
        ),
        (
            "Head Facet: Angular Chin & Mandible Bevel",
            [[s(385), s(470)], [s(440), s(475)], [s(455), s(525)], [s(375), s(515)]],
            terracotta_facet,
            (s(415), s(495)),
        ),
    ]

    for f_name, poly_verts, f_col, (cx_pt, cy_pt) in head_facets:
        outline_pts = stroke_polygon(poly_verts, wobble=0.0, steps_per_side=15, closed=True)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"{f_name} (Boundary)",
                "points": outline_pts,
                "size": 4.0,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{f_name} (Fill)",
                "x": int(round(cx_pt)),
                "y": int(round(cy_pt)),
                "color": f_col,
                "sampleAllLayers": True,
            },
        })

    # =========================================================================
    # LAYER 5: MULTI-PERSPECTIVE FACIAL FEATURES
    # Profile eye & brow on left, Frontal eye & brow on right, Angular lips
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Multi-Perspective Facial Features"}})

    # 1. Profile Eyebrow (Angular chevron on left profile facet)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Profile Eyebrow Chevron",
            "points": stroke_polygon([[s(325), s(255)], [s(365), s(260)], [s(395), s(275)]], wobble=0.0, steps_per_side=10, closed=False),
            "size": 4.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })
    # 2. Profile Eye (Sideways triangular almond eye angled in profile view)
    prof_eye_verts = [[s(350), s(290)], [s(385), s(285)], [s(380), s(310)], [s(350), s(290)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Profile Eye Contour",
            "points": stroke_polygon(prof_eye_verts, wobble=0.0, steps_per_side=12, closed=True),
            "size": 3.6,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Profile Eye Sclera Fill",
            "x": int(s(370)),
            "y": int(s(295)),
            "color": "#fffef5",
            "sampleAllLayers": True,
        },
    })
    # Profile pupil & iris
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Profile Pupil & Iris",
            "points": stroke_polygon([[s(365), s(288)], [s(375), s(288)], [s(372), s(305)], [s(365), s(288)]], wobble=0.0, steps_per_side=8, closed=True),
            "size": 3.0,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Profile Pupil Fill",
            "x": int(s(370)),
            "y": int(s(295)),
            "color": iris_col,
            "sampleAllLayers": True,
        },
    })

    # 3. Frontal Eyebrow (Right side)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Frontal Eyebrow Arch",
            "points": stroke_polygon([[s(430), s(295)], [s(470), s(285)], [s(510), s(296)]], wobble=0.0, steps_per_side=10, closed=False),
            "size": 4.0,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    # 4. Frontal Eye (Almond eye in direct frontal gaze)
    front_eye_verts = [[s(440), s(320)], [s(475), s(305)], [s(508), s(322)], [s(472), s(335)], [s(440), s(320)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Frontal Eye Contour",
            "points": stroke_polygon(front_eye_verts, wobble=0.0, steps_per_side=12, closed=True),
            "size": 3.6,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Frontal Eye Sclera Fill",
            "x": int(s(475)),
            "y": int(s(320)),
            "color": "#fffef5",
            "sampleAllLayers": True,
        },
    })
    # Frontal iris & pupil
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Frontal Iris Boundary",
            "points": stroke_polygon([[s(465), s(310)], [s(485), s(310)], [s(485), s(330)], [s(465), s(330)]], wobble=0.0, steps_per_side=8, closed=True),
            "size": 3.0,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Frontal Iris Fill",
            "x": int(s(475)),
            "y": int(s(320)),
            "color": iris_col,
            "sampleAllLayers": True,
        },
    })
    # Catchlight glint on frontal eye
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Eye Specular Catchlight",
            "points": [[s(472), s(316), 1.0], [s(474), s(316), 1.0]],
            "size": 4.0,
            "color": "#ffffff",
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })

    # 5. Dual-Perspective Angular Lips
    # Upper lip profile facet
    lip_prof_verts = [[s(375), s(430)], [s(410), s(422)], [s(412), s(435)], [s(375), s(430)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Upper Lip Profile Facet (Boundary)",
            "points": stroke_polygon(lip_prof_verts, wobble=0.0, steps_per_side=8, closed=True),
            "size": 3.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Upper Lip Profile Facet (Fill)",
            "x": int(s(395)),
            "y": int(s(428)),
            "color": lip_profile,
            "sampleAllLayers": True,
        },
    })
    # Upper lip frontal facet
    lip_front_verts = [[s(410), s(422)], [s(455), s(428)], [s(435), s(438)], [s(412), s(435)], [s(410), s(422)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Upper Lip Frontal Facet (Boundary)",
            "points": stroke_polygon(lip_front_verts, wobble=0.0, steps_per_side=8, closed=True),
            "size": 3.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Upper Lip Frontal Facet (Fill)",
            "x": int(s(428)),
            "y": int(s(430)),
            "color": lip_frontal,
            "sampleAllLayers": True,
        },
    })
    # Lower lip angular planar facet
    lip_lower_verts = [[s(385), s(438)], [s(445), s(442)], [s(420), s(460)], [s(385), s(438)]]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Lower Lip Planar Facet (Boundary)",
            "points": stroke_polygon(lip_lower_verts, wobble=0.0, steps_per_side=10, closed=True),
            "size": 3.2,
            "color": ink_fracture,
            "hardness": 1.0,
            "polygon": True,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Feature: Lower Lip Planar Facet (Fill)",
            "x": int(s(415)),
            "y": int(s(448)),
            "color": terracotta_facet,
            "sampleAllLayers": True,
        },
    })
    # Lip parting fracture line
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Feature: Lip Parting Fracture Line",
            "points": stroke_polygon([[s(375), s(435)], [s(412), s(435)], [s(445), s(442)]], wobble=0.0, steps_per_side=8, closed=False),
            "size": 3.6,
            "color": lip_shadow,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })

    # =========================================================================
    # LAYER 6: FACETED HAIR SHARDS (PLANAR LOCKS)
    # Angular polygons strictly framing head and cheeks without obstructing features
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "6. Faceted Hair Shards"}})

    hair_shards = [
        (
            "Hair Shard: Left Profile Temple Mass",
            [[s(290), s(160)], [s(340), s(180)], [s(310), s(320)], [s(240), s(260)]],
            "#4a3328",
            (s(290), s(230)),
        ),
        (
            "Hair Shard: Left Flowing Planar Lock",
            [[s(240), s(260)], [s(310), s(320)], [s(280), s(450)], [s(210), s(400)]],
            ochre_facet,
            (s(260), s(360)),
        ),
        (
            "Hair Shard: Right Crown Faceted Shard",
            [[s(515), s(185)], [s(600), s(210)], [s(560), s(330)], [s(485), s(290)]],
            gold_facet,
            (s(540), s(250)),
        ),
        (
            "Hair Shard: Right Cascading Terracotta Lock",
            [[s(560), s(330)], [s(650), s(380)], [s(610), s(510)], [s(525), s(395)]],
            sienna_facet,
            (s(580), s(400)),
        ),
    ]

    for h_name, poly_verts, f_col, (cx_pt, cy_pt) in hair_shards:
        outline_pts = stroke_polygon(poly_verts, wobble=0.0, steps_per_side=15, closed=True)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"{h_name} (Boundary)",
                "points": outline_pts,
                "size": 4.2,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{h_name} (Fill)",
                "x": int(round(cx_pt)),
                "y": int(round(cy_pt)),
                "color": f_col,
                "sampleAllLayers": True,
            },
        })

    # =========================================================================
    # LAYER 7: CHIAROSCURO FORM HATCHING & MASTER FRACTURE LINES
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "7. Chiaroscuro Form Hatching & Fractures"}})

    # Planar directional hatching across shadow planes (angled at math.pi / 3.0)
    hatch_count = 6 + detail * 2
    for h_i in range(1, hatch_count + 1):
        t_h = h_i / (hatch_count + 1)
        hx0 = s(415 + (t_h - 0.5) * 20)
        hy0 = s(390 + t_h * 70)
        hx1 = hx0 - s(35)
        hy1 = hy0 + s(25)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Chiaroscuro: Central Shadow Facet Hatch {h_i}",
                "points": stroke_line(hx0, hy0, hx1, hy1, steps=8),
                "size": 2.5,
                "color": "#181512",
                "hardness": 0.95,
                "opacity": 0.75,
                "linear": True,
            },
        })

    # Master fracture lines tracing structural ridges with pitch charcoal
    ridge_lines = [
        ("Master Fracture: Nose Bridge Profile Ridge", [[s(410), s(280)], [s(335), s(355)], [s(415), s(385)]], 4.8),
        ("Master Fracture: Frontal Zygomatic Crest", [[s(410), s(280)], [s(485), s(290)], [s(525), s(395)]], 4.2),
        ("Master Fracture: Mandible & Chin Bevel", [[s(385), s(470)], [s(440), s(475)], [s(455), s(525)], [s(375), s(515)]], 4.4),
        ("Master Fracture: Head Crown Fracture Axis", [[s(340), s(180)], [s(415), s(150)], [s(515), s(185)]], 4.0),
    ]
    for r_name, r_pts, r_size in ridge_lines:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": r_name,
                "points": stroke_polygon(r_pts, wobble=0.0, steps_per_side=12, closed=False),
                "size": r_size,
                "color": ink_fracture,
                "hardness": 1.0,
                "opacity": 1.0,
                "polygon": True,
            },
        })

    # =========================================================================
    # LAYER 8: 3D FACET HIGH-RELIEF HIGHLIGHTS (LEAPING OFF THE CANVAS)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "8. 3D Facet High-Relief Highlights"}})

    relief_highlights = [
        ("Relief Highlight: Profile Nose Tip Vertex", (s(335), s(352)), (s(345), s(358)), 5.2, "#ffffff"),
        ("Relief Highlight: Nose Bridge Leading Edge", (s(350), s(338)), (s(390), s(302)), 3.6, specular_hi),
        ("Relief Highlight: Frontal Cheek Crest Apex", (s(455), s(330)), (s(495), s(350)), 3.8, specular_hi),
        ("Relief Highlight: Forehead Planar Corner", (s(415), s(158)), (s(450), s(170)), 3.6, specular_hi),
        ("Relief Highlight: Cupid's Bow Facet Gleam", (s(408), s(422)), (s(418), s(424)), 4.0, "#ffffff"),
        ("Relief Highlight: Chin Bevel Facet Light", (s(410), s(485)), (s(435), s(488)), 3.4, specular_hi),
    ]
    for hi_name, (x0, y0), (x1, y1), hi_sz, hi_col in relief_highlights:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": hi_name,
                "points": stroke_line(x0, y0, x1, y1, steps=8),
                "size": hi_sz,
                "color": hi_col,
                "hardness": 0.98,
                "opacity": 0.95,
                "linear": True,
            },
        })

    # Extra micro-facets and texture scaling with detail level (1 to 25)
    if detail >= 6:
        extra_facets = int(round((detail - 5) * 1.5))
        for ef_i in range(min(extra_facets, 30)):
            ang_f = (ef_i * 0.45) % math.pi
            ef_cx = s(410 + math.cos(ang_f) * (60 + (ef_i % 4) * 30))
            ef_cy = s(340 + math.sin(ang_f) * (60 + (ef_i % 4) * 30))
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Cubist Micro-Facet Edge {ef_i + 1}",
                    "points": stroke_line(ef_cx - s(15), ef_cy - s(10), ef_cx + s(15), ef_cy + s(10), steps=6),
                    "size": 2.2,
                    "color": ink_fracture if ef_i % 2 == 0 else specular_hi,
                    "hardness": 0.95,
                    "opacity": 0.85,
                    "linear": True,
                },
            })

    base_title = "The Birth of Venus" if is_venus else ("Classical Male Study" if is_male else f"{prompt.title()} Study")
    title = format_document_title(base_title, style="cubism", detail_level=detail, model=model)

    return {
        "title": title,
        "width": width,
        "height": height,
        "background": canvas_bg,
        "detail_level": detail,
        "style": "cubism",
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_painterly_portrait(
    prompt: str = "portrait",
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate drawing steps recreating an authentic classical portrait (e.g. Botticelli's Venus or Renaissance study).

    Enforces strict Back-to-Front (Z-order) depth layering:
    1. Background & Atmosphere: Serene Mediterranean sky/sea wash drawn first.
    2. Rear Flowing Hair (Backdrop): Large billowing hair masses drawn BEFORE the head and body.
    3. Shoulders & Torso: Sloping porcelain shoulders and upper chest base with paint.bucket.
    4. Head & Face Base: Watertight head contour filled with opaque paint.bucket skin tone, cleanly masking rear hair.
    5. Facial Features: High-fidelity almond eyes, eyelids, irises, pupils, catchlights, sculpted nose, and cupid's bow lips.
    6. Foreground Framing Hair: Only delicate framing curls and tendrils on outer contours, NEVER obstructing facial features!
    7. Specular Highlights: Crisp eye catchlights, lip gloss, and lustrous golden hair sheen.
    """
    style_preset = get_style(style)
    if style_preset.id == "cubism":
        return plan_cubist_portrait(prompt, width, height, detail_level=detail_level, style=style, model=model)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    lowered = prompt.lower()
    is_male = any(k in lowered for k in ("man", "male", "gentleman", "boy", "guy", "king", "prince", "father", "son"))
    is_venus = any(k in lowered for k in ("venus", "bov", "botticelli", "goddess", "aphrodite")) or not is_male

    # Harmonious classical palette
    sky_wash = "#96b5c6"
    sky_breeze = "#bad3e0"
    skin_base = "#faead6"
    skin_fill = "#fceddb"
    skin_contour = "#d4ab88"
    skin_shadow = "#c99b75"
    cheek_blush = "#f4b49e"
    lip_rose_upper = "#b85955"
    lip_rose_lower = "#c96b67"
    lip_parting = "#6b2d28"

    if is_male:
        hair_base = "#4a3328"
        hair_wave = "#5d4233"
        hair_dark = "#2b1c14"
        hair_gold = "#8c6751"
        hair_specular = "#cfb39f"
        eye_iris = "#5c4033"
        eyebrow_col = "#332014"
    else:
        hair_base = "#d4a34b"
        hair_wave = "#c68f3a"
        hair_dark = "#8e5b23"
        hair_gold = "#fbe29d"
        hair_specular = "#fffde6"
        eye_iris = "#6e7a48"  # Botticelli hazel-amber
        eyebrow_col = "#8a5d2a"

    if style_preset.id == "sketchy":
        bg_color = "#fdfefe"
        sky_wash = "#d5dbdb"
        skin_base = "#f2f4f4"
        skin_fill = "#f8f9f9"
        hair_base = "#7f8c8d"
        hair_wave = "#566573"
        hair_gold = "#bdc3c7"
    elif style_preset.id == "pencil":
        bg_color = "#ffffff"
        sky_wash = "#ffffff"
        skin_base = "#f2f4f4"
        skin_fill = "#ffffff"
        hair_base = "#6b7280"
        hair_wave = "#4b5563"
        hair_gold = "#9ca3af"
    elif style_preset.id == "dreamlike":
        bg_color = "#21163e"
        sky_wash = "#3a256a"
        skin_fill = "#fff2e6"
        hair_gold = "#ffeaa7"
    elif style_preset.id == "cartoon":
        bg_color = "#ffffff"
        sky_wash = "#aed6f1"
    else:
        bg_color = "#96b5c6"

    # =========================================================================
    # LAYER 1: PENCIL SKETCH (Loose graphite guide lines)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Pencil Sketch: Portrait Gesture"}})

    # Head gesture oval
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Head Gesture Oval",
            "points": stroke_sketch_oval(s(445), s(310), s(85), s(115), tilt_deg=-6, passes=1.0 + 0.03 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
            "opacity": 0.65,
        },
    })
    # Neck & shoulder guide
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Neck Axis",
            "points": stroke_bezier((s(445), s(420)), (s(450), s(460)), (s(455), s(500)), (s(460), s(540))),
            "size": 2.5,
            "color": "#95a5a6",
            "hardness": 0.75,
            "opacity": 0.6,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Shoulder Silhouette",
            "points": stroke_bezier((s(230), s(670)), (s(360), s(570)), (s(450), s(540)), (s(670), s(670))),
            "size": 3.0,
            "color": "#95a5a6",
            "hardness": 0.8,
            "opacity": 0.6,
        },
    })
    # Eye crosshair axis
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Facial Eye Axis",
            "points": stroke_line(s(395), s(316), s(505), s(316)),
            "size": 2.0,
            "color": "#bdc3c7",
            "hardness": 0.75,
            "opacity": 0.5,
        },
    })

    if detail >= 3:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Flowing Hair Gesture Axis",
                "points": stroke_bezier((s(510), s(230)), (s(640), s(160)), (s(720), s(180)), (s(760), s(260))),
                "size": 2.5,
                "color": "#95a5a6",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })

    # =========================================================================
    # LAYER 2: BACKGROUND & MEDITERRANEAN ATMOSPHERE
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Background & Atmosphere"}})

    # Broad painterly sky/sea sweeps
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Atmosphere: Serene Horizon Wash",
            "points": stroke_line(s(40), s(160), s(760), s(160), steps=20),
            "size": max(40.0, s(90.0)),
            "color": sky_wash,
            "hardness": 0.35,
            "opacity": 0.7,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Atmosphere: Lower Maritime Wash",
            "points": stroke_line(s(40), s(360), s(760), s(360), steps=20),
            "size": max(40.0, s(90.0)),
            "color": sky_breeze,
            "hardness": 0.35,
            "opacity": 0.6,
        },
    })

    if detail >= 5:
        # Zephyr atmospheric breeze curves blowing from upper left
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Atmosphere: Zephyr Breeze Stream 1",
                "points": stroke_bezier((s(60), s(120)), (s(220), s(150)), (s(360), s(180)), (s(450), s(210))),
                "size": 6.0,
                "color": sky_breeze,
                "hardness": 0.45,
                "opacity": 0.5,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Atmosphere: Zephyr Breeze Stream 2",
                "points": stroke_bezier((s(80), s(220)), (s(240), s(250)), (s(360), s(280)), (s(440), s(300))),
                "size": 5.0,
                "color": sky_breeze,
                "hardness": 0.45,
                "opacity": 0.45,
            },
        })

    # =========================================================================
    # LAYER 3: REAR FLOWING HAIR (BACKDROP)
    # Strictly drawn BEFORE head and body so it is completely in the background!
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Rear Flowing Hair (Backdrop)"}})

    # 1. Left Rear Hair Mass: enclosed contour + paint bucket fill
    left_rear_pts = [
        [s(380), s(260)],
        [s(330), s(360)],
        [s(320), s(480)],
        [s(360), s(510)],
        [s(390), s(440)],
        [s(380), s(260)],
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rear Hair: Left Backdrop Mass (Enclosed)",
            "points": stroke_enclosed_loop(left_rear_pts),
            "size": 4.5,
            "color": hair_dark,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Rear Hair: Left Base Tone Fill",
            "x": int(s(345)),
            "y": int(s(420)),
            "color": hair_base,
            "sampleAllLayers": True,
        },
    })

    # 2. Right Rear Billowing Hair: iconic large billowing locks blowing to the right
    right_rear_pts = [
        [s(480), s(210)],
        [s(580), s(150)],
        [s(680), s(120)],
        [s(760), s(160)],
        [s(770), s(220)],
        [s(740), s(320)],
        [s(760), s(440)],
        [s(710), s(510)],
        [s(640), s(460)],
        [s(540), s(440)],
        [s(500), s(380)],
        [s(510), s(290)],
        [s(480), s(210)],
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rear Hair: Right Billowing Mass (Enclosed)",
            "points": stroke_enclosed_loop(right_rear_pts),
            "size": 4.5,
            "color": hair_dark,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Rear Hair: Right Base Tone Fill",
            "x": int(s(640)),
            "y": int(s(290)),
            "color": hair_base,
            "sampleAllLayers": True,
        },
    })

    # Layered painterly waves within the billowing rear hair
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rear Hair: Upper Wind Billow Wave",
            "points": stroke_bezier((s(510), s(220)), (s(620), s(160)), (s(710), s(140)), (s(755), s(180))),
            "size": max(6.0, s(12.0)),
            "color": hair_wave,
            "hardness": 0.8,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rear Hair: Center Flowing Ribbon Wave",
            "points": stroke_bezier((s(520), s(270)), (s(640), s(240)), (s(720), s(260)), (s(750), s(320))),
            "size": max(6.0, s(12.0)),
            "color": hair_dark,
            "hardness": 0.8,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rear Hair: Lower Billow Swirl",
            "points": stroke_bezier((s(510), s(340)), (s(610), s(360)), (s(700), s(390)), (s(740), s(460))),
            "size": max(6.0, s(11.0)),
            "color": hair_wave,
            "hardness": 0.8,
            "opacity": 0.9,
        },
    })

    if detail >= 6:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rear Hair: Crest Wave Accent",
                "points": stroke_bezier((s(590), s(160)), (s(670), s(140)), (s(730), s(160)), (s(760), s(210))),
                "size": max(4.0, s(7.0)),
                "color": hair_gold,
                "hardness": 0.85,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rear Hair: Left Lock Ribbon",
                "points": stroke_bezier((s(370), s(280)), (s(340), s(370)), (s(330), s(440)), (s(350), s(490))),
                "size": max(4.0, s(8.0)),
                "color": hair_wave,
                "hardness": 0.8,
            },
        })

    # =========================================================================
    # LAYER 4: SHOULDERS, NECK & TORSO
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Shoulders & Torso"}})

    torso_pts = [
        [s(220), s(680)],
        [s(340), s(590)],
        [s(410), s(530)],
        [s(490), s(540)],
        [s(580), s(590)],
        [s(680), s(680)],
        [s(220), s(680)],
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Torso: Shoulder Contour (Enclosed)",
            "points": stroke_enclosed_loop(torso_pts),
            "size": 4.5,
            "color": skin_contour,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Torso: Alabaster Skin Base Fill",
            "x": int(s(450)),
            "y": int(s(620)),
            "color": skin_base,
            "sampleAllLayers": True,
        },
    })

    # Collarbone & neck modeling
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Torso: Left Clavicle Curve",
            "points": stroke_bezier((s(360), s(575)), (s(390), s(572)), (s(420), s(578)), (s(445), s(582))),
            "size": 3.0,
            "color": skin_contour,
            "hardness": 0.75,
            "opacity": 0.65,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Torso: Right Clavicle Curve",
            "points": stroke_bezier((s(460), s(582)), (s(485), s(578)), (s(515), s(572)), (s(545), s(575))),
            "size": 3.0,
            "color": skin_contour,
            "hardness": 0.75,
            "opacity": 0.65,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Torso: Neck Hollow Shadow",
            "points": stroke_bezier((s(425), s(450)), (s(450), s(460)), (s(475), s(450)), (s(485), s(440))),
            "size": 8.0,
            "color": skin_shadow,
            "hardness": 0.45,
            "opacity": 0.5,
        },
    })

    # =========================================================================
    # LAYER 5: HEAD & FACE BASE (SKIN FLAT)
    # Completely covers any rear hair and sky passing behind the head!
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Head & Face Base (Skin Flat)"}})

    face_contour_pts = [
        [s(445), s(195)],  # Top center forehead
        [s(495), s(235)],  # Right temple
        [s(500), s(325)],  # Right cheek
        [s(480), s(385)],  # Right jaw
        [s(445), s(425)],  # Chin tip
        [s(410), s(385)],  # Left jaw
        [s(390), s(320)],  # Left cheek
        [s(400), s(235)],  # Left temple
        [s(445), s(195)],  # Close back to top
    ]
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Face: Head Silhouette Bounding Outline (Enclosed)",
            "points": stroke_enclosed_loop(face_contour_pts),
            "size": 4.5,
            "color": skin_contour,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.bucket",
        "params": {
            "name": "Face: Luminous Alabaster Skin Flat",
            "x": int(s(445)),
            "y": int(s(310)),
            "color": skin_fill,
            "sampleAllLayers": True,
        },
    })

    # =========================================================================
    # LAYER 6: FACIAL FEATURES & RENAISSANCE ANATOMY
    # High fidelity eyes, eyelids, pupils, catchlights, nose bridge, nostrils, and lips
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "6. Facial Features & Modeling"}})

    # --- Eyebrows ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eyebrow Arch",
            "points": stroke_bezier((s(398), s(298)), (s(418), s(290)), (s(428), s(292)), (s(436), s(295))),
            "size": 2.6,
            "color": eyebrow_col,
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eyebrow Arch",
            "points": stroke_bezier((s(464), s(296)), (s(476), s(292)), (s(496), s(295)), (s(508), s(304))),
            "size": 2.6,
            "color": eyebrow_col,
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })

    # --- Left Eye (Viewer's Left) ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eye Upper Lid Lashline",
            "points": stroke_bezier((s(404), s(314)), (s(414), s(308)), (s(426), s(310)), (s(434), s(316))),
            "size": 2.6,
            "color": "#3e2714",
            "hardness": 0.95,
            "opacity": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eye Lower Lid",
            "points": stroke_bezier((s(406), s(317)), (s(416), s(322)), (s(426), s(321)), (s(432), s(318))),
            "size": 1.8,
            "color": "#795548",
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eye Iris",
            "points": stroke_enclosed_oval(s(419), s(315), s(4.0), s(4.0)),
            "size": 2.2,
            "color": eye_iris,
            "hardness": 0.9,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eye Pupil",
            "points": [[s(419), s(315)], [s(419.5), s(315.5)]],
            "size": max(2.5, s(3.5)),
            "color": "#1a0f08",
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Eye Specular Catchlight",
            "points": [[s(418), s(314)], [s(418.5), s(314.5)]],
            "size": max(1.8, s(2.2)),
            "color": "#ffffff",
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })

    # --- Right Eye (Viewer's Right) ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eye Upper Lid Lashline",
            "points": stroke_bezier((s(466), s(316)), (s(476), s(311)), (s(488), s(313)), (s(498), s(320))),
            "size": 2.6,
            "color": "#3e2714",
            "hardness": 0.95,
            "opacity": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eye Lower Lid",
            "points": stroke_bezier((s(468), s(319)), (s(478), s(325)), (s(488), s(324)), (s(496), s(322))),
            "size": 1.8,
            "color": "#795548",
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eye Iris",
            "points": stroke_enclosed_oval(s(481), s(317), s(4.0), s(4.0)),
            "size": 2.2,
            "color": eye_iris,
            "hardness": 0.9,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eye Pupil",
            "points": [[s(481), s(317)], [s(481.5), s(317.5)]],
            "size": max(2.5, s(3.5)),
            "color": "#1a0f08",
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Eye Specular Catchlight",
            "points": [[s(480), s(316)], [s(480.5), s(316.5)]],
            "size": max(1.8, s(2.2)),
            "color": "#ffffff",
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })

    # --- Sculpted Nose ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Nose Bridge Line",
            "points": stroke_bezier((s(442), s(305)), (s(444), s(330)), (s(446), s(355)), (s(444), s(372))),
            "size": 2.2,
            "color": skin_contour,
            "hardness": 0.8,
            "opacity": 0.75,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Nose Tip Bulb",
            "points": stroke_bezier((s(439), s(372)), (s(444), s(375)), (s(448), s(373)), (s(450), s(371))),
            "size": 2.0,
            "color": skin_contour,
            "hardness": 0.8,
            "opacity": 0.8,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Left Nostril",
            "points": stroke_bezier((s(435), s(370)), (s(437), s(373)), (s(439), s(372)), (s(440), s(370))),
            "size": 1.8,
            "color": "#8d5b38",
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Right Nostril",
            "points": stroke_bezier((s(448), s(370)), (s(449), s(373)), (s(452), s(373)), (s(454), s(371))),
            "size": 1.8,
            "color": "#8d5b38",
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })

    # --- Renaissance Rose Lips ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Upper Lip Cupid's Bow",
            "points": stroke_bezier((s(433), s(396)), (s(440), s(393)), (s(443), s(395)), (s(454), s(398))),
            "size": 2.5,
            "color": lip_rose_upper,
            "hardness": 0.9,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Mouth Parting Line",
            "points": stroke_bezier((s(433), s(397)), (s(439), s(397)), (s(448), s(397)), (s(454), s(398))),
            "size": 2.0,
            "color": lip_parting,
            "hardness": 0.95,
            "opacity": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Lower Lip Curve",
            "points": stroke_bezier((s(435), s(398)), (s(440), s(406)), (s(448), s(405)), (s(452), s(399))),
            "size": 2.8,
            "color": lip_rose_lower,
            "hardness": 0.85,
            "opacity": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Lower Lip Gloss Highlight",
            "points": stroke_line(s(442), s(403), s(446), s(403)),
            "size": 2.0,
            "color": "#f8d7da",
            "hardness": 0.7,
            "opacity": 0.8,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Feature: Chin Groove Shadow",
            "points": stroke_line(s(439), s(411), s(447), s(411)),
            "size": 2.5,
            "color": skin_contour,
            "hardness": 0.65,
            "opacity": 0.6,
        },
    })

    # --- Cheek Blush Modeling ---
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Modeling: Left Cheek Blush",
            "points": stroke_bezier((s(395), s(340)), (s(402), s(350)), (s(410), s(355)), (s(415), s(345))),
            "size": max(12.0, s(22.0)),
            "color": cheek_blush,
            "hardness": 0.25,
            "opacity": 0.35,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Facial Modeling: Right Cheek Blush",
            "points": stroke_bezier((s(475), s(345)), (s(482), s(355)), (s(490), s(350)), (s(495), s(340))),
            "size": max(12.0, s(22.0)),
            "color": cheek_blush,
            "hardness": 0.25,
            "opacity": 0.35,
        },
    })

    # =========================================================================
    # LAYER 7: FOREGROUND FRAMING HAIR & TENDRILS
    # Only delicate framing tendrils on the outer edges, NEVER crossing the face!
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "7. Foreground Framing Hair"}})

    # Forehead hairline framing curls
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Framing Hair: Forehead Left Hairline Curl",
            "points": stroke_bezier((s(420), s(215)), (s(408), s(228)), (s(402), s(245)), (s(398), s(265))),
            "size": max(3.5, s(6.0)),
            "color": hair_wave,
            "hardness": 0.85,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Framing Hair: Forehead Right Hairline Curl",
            "points": stroke_bezier((s(465), s(215)), (s(480), s(228)), (s(490), s(245)), (s(496), s(265))),
            "size": max(3.5, s(6.0)),
            "color": hair_wave,
            "hardness": 0.85,
        },
    })

    # Cascading tendrils down the left cheek outer edge onto chest
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Framing Hair: Left Outer Cheek Tendril",
            "points": stroke_bezier((s(392), s(260)), (s(378), s(330)), (s(365), s(420)), (s(380), s(520))),
            "size": max(4.0, s(7.0)),
            "color": hair_gold,
            "hardness": 0.85,
        },
    })

    # Cascading tendrils down the right cheek outer edge over shoulder
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Framing Hair: Right Outer Cheek Tendril",
            "points": stroke_bezier((s(500), s(260)), (s(515), s(340)), (s(530), s(430)), (s(510), s(520))),
            "size": max(4.0, s(7.0)),
            "color": hair_gold,
            "hardness": 0.85,
        },
    })

    # Botticelli's iconic spiral lock resting over the neck and chest
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Framing Hair: Botticelli Chest Spiral Lock",
            "points": stroke_bezier((s(465), s(440)), (s(452), s(475)), (s(472), s(515)), (s(460), s(550))),
            "size": max(3.5, s(6.0)),
            "color": hair_gold,
            "hardness": 0.85,
        },
    })

    # =========================================================================
    # LAYER 8: SPECULAR HIGHLIGHTS & HAIR SHEEN
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "8. Specular Highlights & Glints"}})

    # Nose tip and forehead specular highlights
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Nose Tip Specular Point",
            "points": [[s(445), s(370)], [s(445.5), s(370.5)]],
            "size": max(2.5, s(3.5)),
            "color": "#ffffff",
            "hardness": 1.0,
            "opacity": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Forehead Radiance Glow",
            "points": stroke_line(s(440), s(235), s(450), s(235)),
            "size": max(5.0, s(9.0)),
            "color": "#fffef0",
            "hardness": 0.35,
            "opacity": 0.65,
        },
    })
    # Golden hair luster threads
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Right Billowing Hair Luster 1",
            "points": stroke_bezier((s(620), s(155)), (s(680), s(135)), (s(730), s(150)), (s(760), s(190))),
            "size": max(2.5, s(4.0)),
            "color": hair_specular,
            "hardness": 0.9,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Highlight: Right Billowing Hair Luster 2",
            "points": stroke_bezier((s(640), s(235)), (s(700), s(245)), (s(740), s(290)), (s(755), s(330))),
            "size": max(2.5, s(4.0)),
            "color": hair_specular,
            "hardness": 0.9,
            "opacity": 0.9,
        },
    })

    # =========================================================================
    # SCALING DETAIL DENSITY (Detail 1 to 25)
    # =========================================================================
    if detail > 5:
        extra_density = detail - 5
        # 1. Extra rear hair billow ribbons (in rear hair layer)
        for i in range(min(extra_density * 2, 20)):
            hy = s(160 + (i % 6) * 45)
            hx0 = s(540 + (i % 4) * 25)
            hx1 = s(730 + (i % 3) * 15)
            steps.insert(len(steps) - 15, {
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Rear Hair: Wind Wave Detail {i+1}",
                    "points": stroke_bezier((hx0, hy), (hx0 + s(70), hy - s(20)), (hx1 - s(40), hy + s(10)), (hx1, hy + s(30))),
                    "size": max(2.5, s(5.0 - (i % 3) * 0.8)),
                    "color": hair_wave if i % 2 == 0 else hair_dark,
                    "hardness": 0.8,
                    "opacity": 0.85,
                },
            })

        # 2. Extra foreground framing golden curl tendrils (on sides)
        for j in range(min(extra_density * 2, 20)):
            side = 1 if j % 2 == 0 else -1
            bx = s(505 + (j % 5) * 8) if side == 1 else s(385 - (j % 5) * 8)
            by = s(280 + j * 12)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Framing Hair: Fine Golden Strand {j+1}",
                    "points": stroke_bezier((bx, by), (bx + side * s(15), by + s(40)), (bx + side * s(8), by + s(80)), (bx + side * s(20), by + s(120))),
                    "size": max(1.8, s(3.2 - (j % 4) * 0.3)),
                    "color": hair_gold if j % 2 == 0 else hair_specular,
                    "hardness": 0.9,
                    "opacity": 0.85,
                },
            })

        # 3. Extra specular luster glints
        for k in range(min(extra_density, 12)):
            gx = s(600 + (k * 29) % 150)
            gy = s(140 + (k * 37) % 250)
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Highlight: Hair Specular Glint {k+1}",
                    "points": stroke_line(gx, gy, gx + s(18), gy + s(6)),
                    "size": max(1.8, s(3.0)),
                    "color": hair_specular,
                    "hardness": 0.95,
                    "opacity": 0.9,
                },
            })

    if is_venus:
        base_title = "The Birth of Venus"
    elif is_male:
        base_title = "Classical Male Portrait"
    else:
        base_title = f"{prompt.title()} Portrait"

    title = format_document_title(base_title, style=style, detail_level=detail, model=model)

    return {
        "title": title,
        "width": width,
        "height": height,
        "background": bg_color,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def parse_geometric_shape_prompt(prompt: str) -> tuple[bool, int, str, str | None]:
    """Parse prompt for geometric shapes and return (is_geometric, sides, shape_name, target_color)."""
    lowered = prompt.lower()

    color_map = {
        "red": "#e74c3c",
        "crimson": "#c0392b",
        "scarlet": "#e74c3c",
        "blue": "#3498db",
        "azure": "#2980b9",
        "navy": "#1b4f72",
        "green": "#2ecc71",
        "emerald": "#27ae60",
        "lime": "#2ecc71",
        "yellow": "#f1c40f",
        "gold": "#f39c12",
        "golden": "#f39c12",
        "orange": "#e67e22",
        "amber": "#d35400",
        "purple": "#9b59b6",
        "violet": "#8e44ad",
        "pink": "#ff69b4",
        "magenta": "#e056fd",
        "cyan": "#00ffff",
        "teal": "#1abc9c",
        "turquoise": "#1abc9c",
        "black": "#1c2833",
        "white": "#ffffff",
        "gray": "#7f8c8d",
        "grey": "#7f8c8d",
    }
    target_color = None
    for c_name, c_hex in color_map.items():
        if re.search(rf"\b{c_name}\b", lowered):
            target_color = c_hex
            break

    # 1. Triangle / 3-sided polygon
    if any(k in lowered for k in [
        "triangle", "triangular", "trigon", "delta",
        "3 sided", "3-sided", "3sided", "three sided", "three-sided", "3 sides", "three sides",
    ]):
        return True, 3, "Triangle", target_color

    # 2. Quadrilateral / Square / 4-sided polygon
    if any(k in lowered for k in [
        "square", "rectangle", "rectangular", "quadrilateral", "rhombus", "diamond",
        "4 sided", "4-sided", "4sided", "four sided", "four-sided", "4 sides", "four sides",
    ]):
        return True, 4, "Square", target_color

    # 3. Pentagon / 5-sided polygon
    if any(k in lowered for k in [
        "pentagon", "pentagonal",
        "5 sided", "5-sided", "5sided", "five sided", "five-sided", "5 sides", "five sides",
    ]):
        return True, 5, "Pentagon", target_color

    # 4. Hexagon / 6-sided polygon
    if any(k in lowered for k in [
        "hexagon", "hexagonal",
        "6 sided", "6-sided", "6sided", "six sided", "six-sided", "6 sides", "six sides",
    ]):
        return True, 6, "Hexagon", target_color

    # 5. Octagon / 8-sided polygon
    if any(k in lowered for k in [
        "octagon", "octagonal",
        "8 sided", "8-sided", "8sided", "eight sided", "eight-sided", "8 sides", "eight sides",
    ]):
        return True, 8, "Octagon", target_color

    # 6. General polygon / geometric shape (defaults to 3-sided polygon as user requested)
    if any(k in lowered for k in ["polygon", "polygons", "polygonal", "geometric shape", "geometric figure"]):
        return True, 3, "Polygon", target_color

    return False, 0, "", None


def plan_painterly_geometric_shape(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    model: str = "built-in",
    sides: int = 3,
    shape_name: str = "Triangle",
    target_color: str | None = None,
) -> dict[str, Any]:
    """Generate drawing steps recreating an authentic artist rendering a crisp geometric polygon.

    Guarantees that triangles are true 3-sided polygons with straight edges and sharp corners,
    strictly preventing rounded or bowed 'gum drop' shapes across all styles (especially sketchy & cartoon).
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    sides = max(3, sides)
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    cx = width * 0.5
    cy = height * 0.52
    radius = min(width, height) * 0.36

    # Calculate exact polygon vertices
    vertices = stroke_regular_polygon_vertices(cx, cy, radius, sides=sides, orientation_deg=0.0)

    # Determine harmonious palette
    if style_preset.id == "sketchy":
        bg_color = "#fdfefe"
        ink_color = "#1c2833"
        fill_color = target_color or "#566573"
        shade_color = "#2c3e50"
        guide_color = "#7f8c8d"
        highlight_color = "#f2f4f4"
    elif style_preset.id == "pencil":
        bg_color = "#ffffff"
        ink_color = "#374151"
        fill_color = "#f3f4f6"
        shade_color = "#4b5563"
        guide_color = "#6b7280"
        highlight_color = "#ffffff"
    elif style_preset.id == "cartoon":
        bg_color = "#ffffff"
        ink_color = "#000000"
        fill_color = target_color or "#e74c3c"
        shade_color = style_preset.adjust_color(fill_color, 0.75) or "#922b21"
        guide_color = "#aed6f1"
        highlight_color = "#ffffff"
    elif style_preset.id == "dreamlike":
        bg_color = "#100b20"
        ink_color = "#2e1c4a"
        fill_color = target_color or "#9b59b6"
        shade_color = style_preset.adjust_color(fill_color, 0.8) or "#512e5f"
        guide_color = "#6c3483"
        highlight_color = "#f9e79f"
    elif style_preset.id == "abstract":
        bg_color = "#17202a"
        ink_color = "#00ffff"
        fill_color = target_color or "#e67e22"
        shade_color = style_preset.adjust_color(fill_color, 0.7) or "#1b2631"
        guide_color = "#34495e"
        highlight_color = "#ffffff"
    elif style_preset.id == "cubism":
        bg_color = "#1c1917"
        ink_color = "#181512"
        fill_color = target_color or "#c29b62"
        shade_color = "#3d322a"
        guide_color = "#7d6b55"
        highlight_color = "#fefae0"
    else:
        # Realistic / Painterly
        bg_color = "#161a22"
        ink_color = "#0e1117"
        fill_color = target_color or "#c0392b"
        shade_color = style_preset.adjust_color(fill_color, 0.72) or "#641e16"
        guide_color = "#4a5568"
        highlight_color = "#f8f9fa"

    steps: list[dict[str, Any]] = []

    # 1. Background layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Background"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"Background Wash ({style_preset.name})",
            "points": stroke_line(0, cy, width, cy, steps=10),
            "size": float(max(width, height)),
            "color": bg_color,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })

    # 2. Construction & Drafting layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"2. Drafting & Construction ({shape_name})"}})

    if style_preset.id == "sketchy":
        # Classical architectural/artist drafting guides with corner overshoots
        overshoot_lines = stroke_sketchy_polygon_lines(vertices, overshoot=s(18.0), wobble=0.3)
        for idx, line_pts in enumerate(overshoot_lines, start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Drafting Guide Line {idx}",
                    "points": line_pts,
                    "size": 2.2,
                    "color": guide_color,
                    "hardness": 0.85,
                    "opacity": 0.65,
                },
            })
        # Vertical symmetry axis passing through apex
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Drafting: Central Symmetry Axis",
                "points": stroke_line(cx, vertices[0][1] - s(30), cx, cy + radius + s(25), steps=20, wobble=0.2),
                "size": 1.8,
                "color": "#95a5a6",
                "hardness": 0.8,
                "opacity": 0.5,
            },
        })
    elif style_preset.id == "cartoon":
        # Clean gesture guide polygon with sharp vertices
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Gesture: Guide {shape_name}",
                "points": stroke_polygon(vertices, wobble=0.0, steps_per_side=15, closed=True),
                "size": 2.5,
                "color": guide_color,
                "hardness": 0.95,
                "opacity": 0.6,
                "polygon": True,
            },
        })
    elif style_preset.id == "cubism":
        # Analytical perspective fracture rays through each vertex
        for i in range(len(vertices)):
            p1 = vertices[i]
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Analytical Fracture Ray {i + 1}",
                    "points": stroke_line(cx, cy, p1[0] + (p1[0] - cx) * 0.4, p1[1] + (p1[1] - cy) * 0.4, steps=15),
                    "size": 2.2,
                    "color": guide_color,
                    "hardness": 0.95,
                    "opacity": 0.65,
                    "linear": True,
                },
            })
    else:
        # Subtle structural framing lines
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Structure: Edge Guide {i + 1}",
                    "points": stroke_line(p1[0], p1[1], p2[0], p2[1], steps=15, wobble=style_preset.wobble * 0.3),
                    "size": 2.4,
                    "color": guide_color,
                    "hardness": 0.8,
                    "opacity": 0.55,
                },
            })

    # 3. Base Color Flats & Watertight Boundary
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"3. Base Color & Fill ({shape_name})"}})

    # CRITICAL: Straight linear polygon outline (zero Catmull-Rom curvature!)
    polygon_outline = stroke_polygon(vertices, wobble=0.0 if style_preset.id == "cartoon" else style_preset.wobble * 0.15, steps_per_side=20, closed=True)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"{shape_name} Bounding Outline (Enclosed)",
            "points": polygon_outline,
            "size": 4.8,
            "color": ink_color,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })

    if style_preset.id != "pencil":
        # Flood fill cleanly inside centroid
        steps.append({
            "cmd": "paint.bucket",
            "params": {
                "name": f"{shape_name} Flat Fill",
                "x": int(round(cx)),
                "y": int(round(cy)),
                "color": fill_color,
                "sampleAllLayers": True,
            },
        })

    # 4. Facet Shading & Modeling layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"4. Facet Shading & Form ({shape_name})"}})

    if sides == 3:
        # Midpoint of base edge between vertex 1 and 2
        base_mid = [(vertices[1][0] + vertices[2][0]) * 0.5, (vertices[1][1] + vertices[2][1]) * 0.5]
        apex = vertices[0]

        # Facet divider line from apex to base
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Facet: Center Ridge Line",
                "points": stroke_line(apex[0], apex[1], base_mid[0], base_mid[1], steps=20, wobble=0.0 if style_preset.id == "cartoon" else 0.2),
                "size": 3.2 if style_preset.id != "pencil" else 1.8,
                "color": ink_color if style_preset.id == "cartoon" else shade_color,
                "hardness": 0.95 if style_preset.id != "pencil" else 0.65,
                "opacity": 0.85 if style_preset.id != "pencil" else 0.55,
            },
        })

        if style_preset.id == "cartoon":
            # Right facet cel shadow band
            right_facet_verts = [apex, vertices[1], base_mid]
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Cel Shadow Facet Boundary",
                    "points": stroke_polygon(right_facet_verts, wobble=0.0, steps_per_side=15, closed=True),
                    "size": 3.0,
                    "color": shade_color,
                    "hardness": 1.0,
                    "polygon": True,
                },
            })
            rcx = (apex[0] + vertices[1][0] + base_mid[0]) / 3.0
            rcy = (apex[1] + vertices[1][1] + base_mid[1]) / 3.0
            steps.append({
                "cmd": "paint.bucket",
                "params": {
                    "name": "Cel Shadow Facet Fill",
                    "x": int(round(rcx)),
                    "y": int(round(rcy)),
                    "color": shade_color,
                    "sampleAllLayers": True,
                },
            })
        elif style_preset.id in ("sketchy", "pencil"):
            # Directional cross-hatching inside the right facet
            hatch_count = 6 + detail * 2
            for h_i in range(1, hatch_count + 1):
                t_h = h_i / (hatch_count + 1)
                hx0 = apex[0] + (base_mid[0] - apex[0]) * t_h
                hy0 = apex[1] + (base_mid[1] - apex[1]) * t_h
                hx1 = apex[0] + (vertices[1][0] - apex[0]) * t_h
                hy1 = apex[1] + (vertices[1][1] - apex[1]) * t_h
                steps.append({
                    "cmd": "paint.stroke",
                    "params": {
                        "name": f"Facet Cross-Hatch {h_i}",
                        "points": stroke_line(hx0, hy0, hx1, hy1, steps=10, wobble=0.25 if style_preset.id == "pencil" else 0.3),
                        "size": 1.6 if style_preset.id == "pencil" else 2.2,
                        "color": shade_color,
                        "hardness": 0.65 if style_preset.id == "pencil" else 0.9,
                        "opacity": 0.45 if style_preset.id == "pencil" else 0.75,
                    },
                })
        elif style_preset.id == "cubism":
            # Multi-perspective 3D polyhedral facet planes
            right_facet_verts = [apex, vertices[1], base_mid]
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Cubist Shadow Facet Plane Boundary",
                    "points": stroke_polygon(right_facet_verts, wobble=0.0, steps_per_side=15, closed=True),
                    "size": 3.4,
                    "color": ink_color,
                    "hardness": 1.0,
                    "polygon": True,
                },
            })
            rcx = (apex[0] + vertices[1][0] + base_mid[0]) / 3.0
            rcy = (apex[1] + vertices[1][1] + base_mid[1]) / 3.0
            steps.append({
                "cmd": "paint.bucket",
                "params": {
                    "name": "Cubist Shadow Facet Fill",
                    "x": int(round(rcx)),
                    "y": int(round(rcy)),
                    "color": shade_color,
                    "sampleAllLayers": True,
                },
            })
            centroid = [(vertices[0][0] + vertices[1][0] + vertices[2][0]) / 3.0, (vertices[0][1] + vertices[1][1] + vertices[2][1]) / 3.0]
            diag_facet_verts = [apex, centroid, vertices[2]]
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Cubist Intersecting Planar Facet Ridge",
                    "points": stroke_polygon(diag_facet_verts, wobble=0.0, steps_per_side=12, closed=True),
                    "size": 2.8,
                    "color": ink_color,
                    "hardness": 1.0,
                    "polygon": True,
                },
            })
            steps.append({
                "cmd": "paint.bucket",
                "params": {
                    "name": "Cubist Key-Lit Facet Fill",
                    "x": int(round((apex[0] + centroid[0] + vertices[2][0]) / 3.0)),
                    "y": int(round((apex[1] + centroid[1] + vertices[2][1]) / 3.0)),
                    "color": style_preset.adjust_color(fill_color, 1.15) or "#d4ac0d",
                    "sampleAllLayers": True,
                },
            })
        else:
            # Volumetric chiaroscuro sweeps along right facet
            rcx = (apex[0] + vertices[1][0] + base_mid[0]) / 3.0
            rcy = (apex[1] + vertices[1][1] + base_mid[1]) / 3.0
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Facet Chiaroscuro Wash",
                    "points": stroke_line(rcx - s(40), rcy, rcx + s(40), rcy, steps=12, wobble=0.4),
                    "size": s(35.0),
                    "color": shade_color,
                    "hardness": 0.65,
                    "opacity": 0.85,
                },
            })

    # 5. Ink Contours & Sharp Edge Definition
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"5. Ink Contours ({shape_name})"}})

    contour_pts = stroke_polygon(vertices, wobble=0.0 if style_preset.id == "cartoon" else style_preset.wobble * 0.1, steps_per_side=22, closed=True)
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"{shape_name} Master Ink Outline",
            "points": contour_pts,
            "size": 5.4 if style_preset.id == "cartoon" else 3.8,
            "color": ink_color,
            "hardness": 1.0,
            "opacity": 1.0,
            "polygon": True,
        },
    })

    # 6. Highlights & Accents
    if detail >= 2:
        steps.append({"cmd": "layer.new.layer", "params": {"name": f"6. Highlights & Accents ({shape_name})"}})

        apex = vertices[0]
        p_left = vertices[-1]
        hi_x0 = apex[0] + (p_left[0] - apex[0]) * 0.08
        hi_y0 = apex[1] + (p_left[1] - apex[1]) * 0.08
        hi_x1 = apex[0] + (p_left[0] - apex[0]) * 0.45
        hi_y1 = apex[1] + (p_left[1] - apex[1]) * 0.45

        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Specular: Leading Edge Highlight",
                "points": stroke_line(hi_x0, hi_y0, hi_x1, hi_y1, steps=12, wobble=0.0 if style_preset.id == "cartoon" else 0.2),
                "size": 3.0,
                "color": highlight_color,
                "hardness": 0.95,
                "opacity": 0.9,
            },
        })

        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Specular: Apex Corner Gleam",
                "points": [[apex[0], apex[1] + s(2), 1.0], [apex[0], apex[1] + s(3), 1.0]],
                "size": 5.0,
                "color": highlight_color,
                "hardness": 1.0,
                "opacity": 0.95,
            },
        })

    title = format_document_title(f"{shape_name} Study", style=style, detail_level=detail, model=model)
    return {
        "title": title,
        "width": width,
        "height": height,
        "background": bg_color,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_painterly_rabbit(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "cartoon",
    model: str = "built-in",
) -> dict[str, Any]:
    """Generate a cartoon/painterly illustration of a white rabbit hopping across a lush meadow field.

    Strictly separates Layer 1 (Background Field & Sky) from Layers 2-4 (Rabbit Character solid fills,
    cel shading, facial features, and crisp ink outlines) so animations keep the field stationary while
    the fully colored white rabbit hops cleanly across the screen.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []
    lowered = prompt.lower()

    # Determine rabbit fur color (defaults to pure white #ffffff for white rabbit / cartoon rabbit)
    fur_color = "#ffffff"
    fur_shadow = "#e2e8f0"
    inner_ear_color = "#ffb6c1"
    nose_color = "#ff6b8b"
    ink_color = "#111116"
    if "brown" in lowered:
        fur_color = "#d2996c"
        fur_shadow = "#b0784c"
    elif "gray" in lowered or "grey" in lowered:
        fur_color = "#cbd5e1"
        fur_shadow = "#94a3b8"
    elif "pink" in lowered:
        fur_color = "#ffc2d1"
        fur_shadow = "#ff8fa3"

    bg_color = "#87ceeb"
    if style_preset.id in ("pencil", "sketchy"):
        bg_color = "#ffffff"

    # =========================================================================
    # LAYER 1: STATIONARY BACKGROUND (SKY, SUN, CLOUDS, HILLS, FIELD, FLOWERS)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "1. Background Field & Sky"}})

    if style_preset.id != "pencil":
        # Sky upper atmosphere wash
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Sky Atmosphere Wash",
                "points": stroke_line(s(40), s(90), s(760), s(90), steps=16),
                "size": s(140.0),
                "color": "#7ec8e3",
                "hardness": 0.85,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Sky Mid Horizon Wash",
                "points": stroke_line(s(40), s(260), s(760), s(260), steps=16),
                "size": s(160.0),
                "color": "#a2d9f7",
                "hardness": 0.85,
                "opacity": 1.0,
            },
        })
        # Golden Sun in top right
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Sun Golden Disk",
                "points": [[s(680), s(105), 1.0], [s(682), s(106), 1.0]],
                "size": s(88.0),
                "color": "#ffd54f",
                "hardness": 0.98,
                "opacity": 1.0,
            },
        })
        # Fluffy white clouds
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Fluffy Cloud Left",
                "points": stroke_line(s(150), s(125), s(270), s(125), steps=10),
                "size": s(52.0),
                "color": "#ffffff",
                "hardness": 0.92,
                "opacity": 0.96,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Fluffy Cloud Center",
                "points": stroke_line(s(430), s(145), s(550), s(145), steps=10),
                "size": s(48.0),
                "color": "#ffffff",
                "hardness": 0.92,
                "opacity": 0.96,
            },
        })
        # Distant rolling green meadow hill
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Distant Rolling Meadow Hill",
                "points": stroke_bezier((s(0), s(520)), (s(260), s(465)), (s(540), s(485)), (s(800), s(525)), steps=24),
                "size": s(130.0),
                "color": "#66bb6a",
                "hardness": 0.95,
                "opacity": 1.0,
            },
        })
        # Foreground lush green field fill
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Meadow Field Upper Sweep",
                "points": stroke_line(s(0), s(610), s(800), s(610), steps=20),
                "size": s(160.0),
                "color": "#4caf50",
                "hardness": 0.95,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Background Meadow Field Lower Sweep",
                "points": stroke_line(s(0), s(735), s(800), s(735), steps=20),
                "size": s(160.0),
                "color": "#43a047",
                "hardness": 0.95,
                "opacity": 1.0,
            },
        })

    # Meadow horizon line
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Background Horizon Hill Line",
            "points": stroke_bezier((s(0), s(505)), (s(260), s(455)), (s(540), s(475)), (s(800), s(510)), steps=24),
            "size": s(4.5),
            "color": "#2e7d32" if style_preset.id != "pencil" else "#4b5563",
            "hardness": 0.95,
            "opacity": 1.0,
        },
    })

    # Stationary grass tufts & meadow wildflowers on background
    for g_idx, (gx, gy) in enumerate([
        (s(95), s(635)), (s(265), s(660)), (s(430), s(615)),
        (s(585), s(650)), (s(710), s(625)), (s(350), s(710)),
    ], start=1):
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Background Grass Tuft {g_idx}",
                "points": [[gx - s(10), gy - s(12), 0.9], [gx, gy, 1.0], [gx + s(10), gy - s(14), 0.9]],
                "size": s(3.8),
                "color": "#1b5e20" if style_preset.id != "pencil" else "#4b5563",
                "hardness": 0.95,
                "opacity": 1.0,
            },
        })
        if style_preset.id != "pencil" and g_idx <= 4:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Background Meadow Flower {g_idx}",
                    "points": [[gx + s(18), gy - s(8), 1.0], [gx + s(19), gy - s(7), 1.0]],
                    "size": s(11.0),
                    "color": "#fff176" if g_idx % 2 == 1 else "#f48fb1",
                    "hardness": 0.98,
                    "opacity": 1.0,
                },
            })

    # =========================================================================
    # LAYER 2: RABBIT CHARACTER SOLID OPAQUE FILLS (100% OPAQUE ON EVERY CEL)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Rabbit Character Solid Fills"}})

    # Local cast shadow directly beneath rabbit
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rabbit Cast Shadow Under Feet",
            "points": stroke_line(s(140), s(572), s(245), s(572), steps=10),
            "size": s(22.0),
            "color": "#2e7d32" if style_preset.id != "pencil" else "#9ca3af",
            "hardness": 0.85,
            "opacity": 0.65,
        },
    })

    if style_preset.id != "pencil":
        # 1. Fluffy cotton tail solid white fill (fills r=18 tail outline edge-to-edge)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Tail Solid White Fill",
                "points": stroke_line(s(110), s(502), s(114), s(502), steps=6),
                "size": s(33.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 2. Plump rabbit body/torso multi-pass solid white interior fills (strictly inside back/belly outlines)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Body Outer Solid White Fill",
                "points": stroke_enclosed_oval(s(182), s(492), s(34), s(20)),
                "size": s(30.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Body Core Solid White Fill",
                "points": stroke_line(s(150), s(494), s(216), s(488), steps=12),
                "size": s(44.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Chest & Shoulder Solid White Fill",
                "points": stroke_line(s(195), s(484), s(228), s(472), steps=10),
                "size": s(36.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 3. Hind leg and hopping foot solid white fills (follows exact curve inside hind leg outline)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Hind Thigh Solid White Fill",
                "points": stroke_bezier((s(156), s(514)), (s(144), s(544)), (s(162), s(556)), (s(198), s(553)), steps=14),
                "size": s(22.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Hind Hopping Foot Solid White Fill",
                "points": stroke_line(s(154), s(542), s(194), s(552), steps=10),
                "size": s(18.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 4. Front paws solid white fills (strictly inside front paw outline)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Front Foreleg & Paw Solid White Fill",
                "points": stroke_line(s(232), s(502), s(244), s(534), steps=8),
                "size": s(16.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 5. Round rabbit head & cheeks solid white fills (inside head outline centered at (238, 434) with rx=36, ry=32)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Head Outer Solid White Fill",
                "points": stroke_enclosed_oval(s(238), s(434), s(20), s(17)),
                "size": s(30.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Head Core Solid White Fill",
                "points": stroke_line(s(226), s(434), s(250), s(434), steps=8),
                "size": s(38.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 6. Long upright rabbit ears solid white fills + pink inner ear fills (strictly inside ear outlines)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Left Ear Solid White Fill",
                "points": stroke_bezier((s(218), s(404)), (s(210), s(370)), (s(211), s(350)), (s(212), s(344)), steps=14),
                "size": s(15.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Right Ear Solid White Fill",
                "points": stroke_bezier((s(241), s(404)), (s(239), s(368)), (s(240), s(348)), (s(241), s(340)), steps=14),
                "size": s(15.0),
                "color": fur_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Left Inner Ear Pink Fill",
                "points": stroke_line(s(217), s(396), s(212), s(352), steps=10),
                "size": s(8.0),
                "color": inner_ear_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Right Inner Ear Pink Fill",
                "points": stroke_line(s(241), s(394), s(241), s(348), steps=10),
                "size": s(8.0),
                "color": inner_ear_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

        # 7. Subtle cel shading along lower belly and hind leg
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Belly Underside Cel Shadow",
                "points": stroke_bezier((s(145), s(516)), (s(182), s(530)), (s(210), s(522)), (s(228), s(504)), steps=14),
                "size": s(12.0),
                "color": fur_shadow,
                "hardness": 0.98,
                "opacity": 1.0,
            },
        })

    # =========================================================================
    # LAYER 3: RABBIT CRISP CARTOON INK OUTLINES
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Rabbit Ink Outlines"}})

    rabbit_outlines = [
        ("Rabbit Ink: Fluffy Cotton Tail Outline", stroke_enclosed_oval(s(112), s(502), s(18), s(18)), s(4.8)),
        ("Rabbit Ink: Arched Back & Rump Outline", stroke_bezier((s(128), s(495)), (s(145), s(448)), (s(195), s(445)), (s(222), s(462)), steps=22), s(5.0)),
        ("Rabbit Ink: Belly & Chest Outline", stroke_bezier((s(134), s(518)), (s(178), s(536)), (s(212), s(524)), (s(232), s(498)), steps=22), s(5.0)),
        ("Rabbit Ink: Hind Leg & Hopping Foot Outline", stroke_bezier((s(152), s(510)), (s(132), s(548)), (s(155), s(566)), (s(208), s(558)), steps=22), s(4.8)),
        ("Rabbit Ink: Front Paw Outline", stroke_bezier((s(224), s(500)), (s(236), s(545)), (s(256), s(545)), (s(246), s(496)), steps=18), s(4.6)),
        ("Rabbit Ink: Round Head & Cheek Outline", stroke_enclosed_oval(s(238), s(434), s(36), s(32)), s(5.0)),
        ("Rabbit Ink: Left Long Ear Outline", stroke_bezier((s(210), s(408)), (s(198), s(332)), (s(222), s(328)), (s(226), s(406)), steps=24), s(4.8)),
        ("Rabbit Ink: Right Long Ear Outline", stroke_bezier((s(232), s(406)), (s(228), s(328)), (s(254), s(324)), (s(250), s(408)), steps=24), s(4.8)),
    ]
    for o_name, o_pts, o_sz in rabbit_outlines:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": o_name,
                "points": o_pts,
                "size": o_sz if style_preset.id != "pencil" else 2.2,
                "color": ink_color if style_preset.id != "pencil" else "#374151",
                "hardness": 1.0 if style_preset.id != "pencil" else 0.65,
                "opacity": 1.0 if style_preset.id != "pencil" else 0.6,
            },
        })

    # =========================================================================
    # LAYER 4: RABBIT FACIAL FEATURES (EYE, CATCHLIGHT, PINK NOSE, SMILE, WHISKERS)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Rabbit Facial Features"}})

    if style_preset.id != "pencil":
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Facial Feature: Rosy Cheek Blush",
                "points": [[s(248), s(446), 1.0], [s(252), s(446), 1.0]],
                "size": s(13.0),
                "color": "#ffccd5",
                "hardness": 0.9,
                "opacity": 0.95,
            },
        })
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Facial Feature: Cute Pink Nose",
                "points": [[s(270), s(432), 1.0], [s(272), s(433), 1.0]],
                "size": s(9.5),
                "color": nose_color,
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })

    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rabbit Facial Feature: Expressive Dark Eye Pupil",
            "points": [[s(248), s(422), 1.0], [s(249), s(423), 1.0]],
            "size": s(11.5),
            "color": ink_color,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    if style_preset.id != "pencil":
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Rabbit Facial Feature: Eye White Specular Catchlight",
                "points": [[s(246), s(419), 1.0], [s(247), s(420), 1.0]],
                "size": s(4.2),
                "color": "#ffffff",
                "hardness": 1.0,
                "opacity": 1.0,
            },
        })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rabbit Facial Feature: Happy Smile Mouth Curve",
            "points": stroke_bezier((s(256), s(442)), (s(262), s(448)), (s(268), s(446)), (s(271), s(438)), steps=10),
            "size": s(3.0),
            "color": ink_color,
            "hardness": 1.0,
            "opacity": 1.0,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rabbit Facial Feature: Upper Whisker",
            "points": stroke_line(s(258), s(436), s(286), s(430), steps=6),
            "size": s(2.2),
            "color": ink_color,
            "hardness": 0.95,
            "opacity": 0.9,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Rabbit Facial Feature: Lower Whisker",
            "points": stroke_line(s(258), s(440), s(285), s(442), steps=6),
            "size": s(2.2),
            "color": ink_color,
            "hardness": 0.95,
            "opacity": 0.9,
        },
    })

    title = format_document_title("Cartoon White Rabbit Hopping", style=style, detail_level=detail, model=model)
    return {
        "title": title,
        "width": width,
        "height": height,
        "background": bg_color,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
    }


def plan_fallback(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    images: list[Path] | None = None,
    model: str = "built-in",
) -> dict[str, Any]:
    """Select the best matching painterly plan based on prompt keywords, detail level (1 to 25), and style."""
    lowered = prompt.lower()

    if is_portrait_or_face_prompt(prompt, images):
        return plan_painterly_portrait(prompt, width, height, detail_level, style=style, model=model)

    is_geom, sides, shape_name, target_color = parse_geometric_shape_prompt(prompt)
    if is_geom:
        return plan_painterly_geometric_shape(
            prompt,
            width,
            height,
            detail_level=detail_level,
            style=style,
            model=model,
            sides=sides,
            shape_name=shape_name,
            target_color=target_color,
        )

    if any(k in lowered for k in ["rabbit", "bunny", "hare"]):
        return plan_painterly_rabbit(prompt, width, height, detail_level, style=style, model=model)

    if any(k in lowered for k in ["pikachu", "pika", "pokemon"]):
        return plan_painterly_pikachu(width, height, detail_level, style=style, model=model)

    if any(k in lowered for k in ["car", "racecar", "auto", "vehicle", "speed", "formula", "truck"]):
        return plan_painterly_racecar(width, height, detail_level, style=style, model=model)

    if any(k in lowered for k in ["sunset", "mountain", "dusk", "horizon", "lake", "ocean", "landscape"]):
        return plan_painterly_sunset(width, height, detail_level, style=style, model=model)

    if any(k in lowered for k in ["duck", "rubber duck", "bath", "quack"]):
        return plan_painterly_rubber_duck(width, height, detail_level, style=style, model=model)

    # For any other prompt, create an authentic dynamic composition matching the user's specific prompt
    return plan_dynamic_artwork(prompt, width, height, detail_level, style=style, model=model)


def plan_refinement_fallback(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
    current_image: Path | None = None,
    loop_iteration: int = 1,
    total_iterations: int = 1,
    model: str = "built-in",
) -> dict[str, Any]:
    """Procedurally generate phase-specific targeted additive refinement brushstrokes for feedback loop passes.

    Follows a progressive 4-phase refinement pipeline:
    - Pass 1: Complete occlusion repair, covering intersecting water/background with solid opaque base color, and unifying silhouette.
    - Pass 2: Continuous volumetric form modeling (broad smooth shadow sweeps, strictly banning scattered shadow spots) and waterline contact wake.
    - Pass 3: Crisp focal facial features, anatomy, and dynamic flying water splash particles.
    - Pass 4: Weighted master vector ink contours and brilliant specular catchlights.
    """
    style_preset = get_style(style)
    detail = max(1, min(detail_level, 25))
    scale = min(width, height) / 800.0

    def s(val: float) -> float:
        return round(val * scale, 1)

    steps: list[dict[str, Any]] = []

    lowered = prompt.lower()
    is_duck = any(k in lowered for k in ["duck", "rubber duck", "bath"])
    is_moose = any(k in lowered for k in ["moose", "deer", "stag", "elk", "reindeer", "caribou", "buck"])

    # Base palette
    if is_moose:
        ink_color = "#111111"
        shadow_color = "#3e2723"
        base_color = "#795548"
        highlight_color = "#ffffff"
    elif style_preset.id == "cubism":
        ink_color = "#181512"
        shadow_color = "#2c2118"
        base_color = "#d4ac0d"
        highlight_color = "#fefae0"
    elif style_preset.id == "cartoon":
        ink_color = "#000000"
        shadow_color = "#d35400" if is_duck else "#2c3e50"
        base_color = "#f1c40f" if is_duck else "#ecf0f1"
        highlight_color = "#ffffff"
    elif style_preset.id == "sketchy":
        ink_color = "#1c2833"
        shadow_color = "#2c3e50"
        base_color = "#f2f4f4"
        highlight_color = "#fdfefe"
    elif style_preset.id == "pencil":
        ink_color = "#374151"
        shadow_color = "#4b5563"
        base_color = "#f3f4f6"
        highlight_color = "#ffffff"
    elif style_preset.id == "dreamlike":
        ink_color = "#2e1c4a"
        shadow_color = "#3a256a"
        base_color = "#f9e79f" if is_duck else "#d7bde2"
        highlight_color = "#fff8dc"
    elif style_preset.id == "abstract":
        ink_color = "#0e1724"
        shadow_color = "#1b2631"
        base_color = "#e67e22" if is_duck else "#3498db"
        highlight_color = "#00ffff"
    else:  # realistic & painterly
        ink_color = "#17120e"
        shadow_color = "#935116" if is_duck else "#2a1e17"
        base_color = "#f39c12" if is_duck else "#d5dbdb"
        highlight_color = "#ffffff"

    phase = min(loop_iteration, 4)

    if phase == 1:
        # =========================================================================
        # PHASE 1: COMPLETE OCCLUSION REPAIR & SOLID BASE FLATS
        # =========================================================================
        if is_duck:
            critique = (
                f"Pass 1/{total_iterations} [Structural Repair]: Fully resolving occlusion errors and unpainted gaps. "
                "Applying solid opaque yellow base strokes across the torso to erase the intersecting blue water line, "
                "clearing wireframe scribbles from the head, and establishing a unified watertight silhouette."
            )
        elif is_moose:
            critique = (
                f"Pass 1/{total_iterations} [Flesh Out Forgotten Shapes]: Filling in the unpainted hollow ear wireframes "
                "with matching tan base color, grounding the hooves, and adding nostrils—strictly leaving already solid body areas untouched."
            )
        else:
            critique = (
                f"Pass 1/{total_iterations} [Structural Repair]: Fully repairing occlusion errors and background cuts. "
                "Applying solid opaque base flats to seal all holes and bleed-through, and unifying outer silhouette boundaries."
            )

        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 1. Base Occlusion Repair"}})
        if is_duck:
            # Solid opaque yellow patch over body and wing to erase intersecting waterline
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Opaque Yellow Body Patch (Cover Intersecting Water)",
                    "points": stroke_line(s(270), s(460), s(570), s(460), steps=15),
                    "size": max(25.0, s(50.0)),
                    "color": base_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Opaque patch covering chest gap
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Opaque Chest & Belly Flat Fill",
                    "points": stroke_line(s(310), s(430), s(460), s(430), steps=12),
                    "size": max(20.0, s(40.0)),
                    "color": base_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Clean head patch to erase multiple overlapping sketch wireframes
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Opaque Head Flat (Erase Wireframe Scribbles)",
                    "points": stroke_bezier((s(430), s(280)), (s(490), s(250)), (s(530), s(280)), (s(490), s(340))),
                    "size": max(25.0, s(45.0)),
                    "color": base_color,
                    "hardness": 1.0,
                    "opacity": 0.95,
                },
            })
        elif is_moose:
            # Fill hollow left ear wireframe
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Fill Hollow Left Ear (Tan Base Flat)",
                    "points": stroke_bezier((s(205), s(260)), (s(220), s(235)), (s(235), s(245)), (s(225), s(270))),
                    "size": max(12.0, s(22.0)),
                    "color": "#bcaaa4",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Ear Core Flat",
                    "points": [[s(220), s(255), 1.0], [s(222), s(253), 1.0]],
                    "size": max(14.0, s(24.0)),
                    "color": "#bcaaa4",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Fill hollow right ear wireframe
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Fill Hollow Right Ear (Tan Base Flat)",
                    "points": stroke_bezier((s(325), s(270)), (s(335), s(245)), (s(355), s(235)), (s(360), s(260))),
                    "size": max(12.0, s(22.0)),
                    "color": "#bcaaa4",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Ear Core Flat",
                    "points": [[s(340), s(255), 1.0], [s(342), s(253), 1.0]],
                    "size": max(14.0, s(24.0)),
                    "color": "#bcaaa4",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Snout nostrils
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Snout Nostril",
                    "points": [[s(265), s(395), 1.0], [s(268), s(398), 1.0]],
                    "size": max(4.0, s(7.0)),
                    "color": "#3e2723",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Snout Nostril",
                    "points": [[s(295), s(395), 1.0], [s(298), s(398), 1.0]],
                    "size": max(4.0, s(7.0)),
                    "color": "#3e2723",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Solid hoof base fills
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Front Hoof Solid Base",
                    "points": stroke_line(s(310), s(675), s(345), s(675), steps=4),
                    "size": max(8.0, s(14.0)),
                    "color": "#212121",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Rear Hoof Solid Base",
                    "points": stroke_line(s(535), s(675), s(570), s(675), steps=4),
                    "size": max(8.0, s(14.0)),
                    "color": "#212121",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Outer Silhouette Boundary Accent",
                    "points": stroke_sketch_oval(s(400), s(400), s(170), s(150), passes=1.0),
                    "size": 3.8,
                    "color": ink_color,
                    "hardness": 0.95,
                    "opacity": 0.9,
                },
            })

        # Unified outer silhouette boundary
        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 2. Watertight Outer Boundary"}})
        if is_duck:
            duck_body_contour = stroke_bezier((s(250), s(410)), (s(300), s(550)), (s(550), s(550)), (s(590), s(420)))
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Clean Lower Body Boundary Contour",
                    "points": duck_body_contour,
                    "size": 4.8 if style_preset.id == "cartoon" else 3.8,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Waterline Base Contact Foam",
                    "points": stroke_line(s(240), s(540), s(580), s(540), steps=16, wobble=0.1),
                    "size": max(3.0, s(5.5)),
                    "color": "#ffffff",
                    "hardness": 0.95,
                    "opacity": 0.95,
                },
            })
        elif is_moose:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Ear Outer Ink Boundary",
                    "points": stroke_bezier((s(200), s(260)), (s(215), s(235)), (s(238), s(245)), (s(225), s(272))),
                    "size": 4.0,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Ear Outer Ink Boundary",
                    "points": stroke_bezier((s(325), s(272)), (s(338), s(245)), (s(360), s(235)), (s(365), s(260))),
                    "size": 4.0,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Unified Perimeter Contour",
                    "points": stroke_line(s(300), s(540), s(500), s(540), steps=8),
                    "size": 3.8,
                    "color": ink_color,
                    "hardness": 0.95,
                    "opacity": 1.0,
                },
            })

    elif phase == 2:
        # =========================================================================
        # PHASE 2: VOLUMETRIC FORM MODELING & WATERLINE GROUNDING (NO SHADOW SPOTS!)
        # =========================================================================
        if is_duck:
            critique = (
                f"Pass 2/{total_iterations} [Form Modeling & Waterline Grounding]: Applying one smooth, continuous "
                "cel shadow crescent along the underside belly (strictly avoiding noisy shadow spots or speckles). "
                "Establishing clean wing shading and positioning foam wake ripples along the water contact boundary."
            )
        elif is_moose:
            critique = (
                f"Pass 2/{total_iterations} [Form Modeling & Ground Anchoring]: Adding a smooth continuous form shadow "
                "along the underside belly (no scattered spots), and defining ground cast shadow anchors under the hooves."
            )
        else:
            critique = (
                f"Pass 2/{total_iterations} [Form Modeling]: Adding unified continuous form shadow planes along the "
                "underside volume (no scattered dash marks), and defining clean ground contact anchors."
            )

        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 1. Continuous Form Shadow (No Spots)"}})
        if is_duck:
            # ONE continuous sweeping underside crescent shadow along the belly curve (STRICTLY NO SCATTERED DASH MARKS!)
            belly_shadow = stroke_bezier((s(270), s(490)), (s(380), s(545)), (s(490), s(545)), (s(580), s(470)))
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Underside Continuous Form Shadow Crescent",
                    "points": belly_shadow,
                    "size": max(14.0, s(28.0)),
                    "color": shadow_color,
                    "hardness": 0.85 if style_preset.id == "cartoon" else 0.7,
                    "opacity": 0.85,
                },
            })
            # Wing underside shadow sweep
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Wing Underside Shadow Plane",
                    "points": stroke_line(s(370), s(480), s(490), s(480), steps=10),
                    "size": max(8.0, s(16.0)),
                    "color": shadow_color,
                    "hardness": 0.85 if style_preset.id == "cartoon" else 0.75,
                    "opacity": 0.8,
                },
            })
        elif is_moose:
            # Continuous lower belly form shadow along the natural bottom edge of the moose
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Underside Continuous Form Shadow Crescent",
                    "points": stroke_bezier((s(320), s(540)), (s(420), s(560)), (s(510), s(555)), (s(590), s(525))),
                    "size": max(10.0, s(18.0)),
                    "color": shadow_color,
                    "hardness": 0.85 if style_preset.id == "cartoon" else 0.7,
                    "opacity": 0.75,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Neck Underside Form Shadow",
                    "points": stroke_bezier((s(265), s(430)), (s(280), s(460)), (s(300), s(480)), (s(320), s(460))),
                    "size": max(8.0, s(14.0)),
                    "color": shadow_color,
                    "hardness": 0.85 if style_preset.id == "cartoon" else 0.7,
                    "opacity": 0.7,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Continuous Form Shadow Sweep",
                    "points": stroke_line(s(320), s(540), s(480), s(540), steps=8),
                    "size": max(8.0, s(16.0)),
                    "color": shadow_color,
                    "hardness": 0.85 if style_preset.id == "cartoon" else 0.7,
                    "opacity": 0.65,
                },
            })

        # Ground / Waterline contact
        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 2. Waterline Wake & Ground Contact"}})
        if is_duck:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Contact Water Foam Ribbon",
                    "points": stroke_bezier((s(230), s(550)), (s(340), s(575)), (s(460), s(575)), (s(570), s(550))),
                    "size": max(3.5, s(6.0)),
                    "color": "#ffffff",
                    "hardness": 0.95,
                    "opacity": 0.95,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Water Surface Reflection Tint",
                    "points": stroke_line(s(320), s(580), s(480), s(580), steps=12),
                    "size": max(8.0, s(18.0)),
                    "color": "#f39c12",
                    "hardness": 0.5,
                    "opacity": 0.45,
                },
            })
        elif is_moose:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Front Hoof Ground Cast Shadow",
                    "points": stroke_sketch_oval(s(328), s(686), s(35), s(10), passes=1.0),
                    "size": max(6.0, s(12.0)),
                    "color": "#2e7d32",
                    "hardness": 0.85,
                    "opacity": 0.75,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Rear Hoof Ground Cast Shadow",
                    "points": stroke_sketch_oval(s(552), s(686), s(35), s(10), passes=1.0),
                    "size": max(6.0, s(12.0)),
                    "color": "#2e7d32",
                    "hardness": 0.85,
                    "opacity": 0.75,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Ground Contact Anchor",
                    "points": stroke_line(s(300), s(560), s(500), s(560), steps=8),
                    "size": 3.5,
                    "color": shadow_color,
                    "hardness": 0.75,
                    "opacity": 0.6,
                },
            })

    elif phase == 3:
        # =========================================================================
        # PHASE 3: FACIAL FEATURES, ANATOMY & DYNAMIC SPLASHES
        # =========================================================================
        if is_duck:
            critique = (
                f"Pass 3/{total_iterations} [Anatomy & Dynamic Splashes]: Defining crisp facial features: clean circular eye, "
                "dark pupil with white catchlight, and smiling bill parting line. Painting dynamic water droplets and splash "
                "arcs radiating outward from the contact wake."
            )
        elif is_moose:
            critique = (
                f"Pass 3/{total_iterations} [Facial Features & Fine Anatomy]: Defining crisp facial anatomy: eye pupils with "
                "specular white catchlights, smiling snout division line, inner ear depth creases, and chin bell tuft."
            )
        else:
            critique = (
                f"Pass 3/{total_iterations} [Anatomy & Features]: Defining crisp focal anatomy and environmental particles."
            )

        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 1. Focal Features & Bill Anatomy"}})
        if is_duck:
            # Clean eye circle, pupil, and white shine dot
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Eye Outer Rim Contour",
                    "points": stroke_enclosed_oval(s(505), s(305), s(20), s(22)),
                    "size": 3.6,
                    "color": "#000000",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Eye Dark Pupil",
                    "points": [[s(506), s(305), 1.0], [s(507), s(306), 1.0]],
                    "size": max(10.0, s(16.0)),
                    "color": "#111111",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Eye White Catchlight Dot",
                    "points": [[s(502), s(300), 1.0], [s(503), s(301), 1.0]],
                    "size": max(3.5, s(5.5)),
                    "color": "#ffffff",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Bill smiling parting line
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Bill Center Smile Division",
                    "points": stroke_bezier((s(540), s(335)), (s(565), s(340)), (s(595), s(340)), (s(620), s(330))),
                    "size": 3.5,
                    "color": "#111111",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })

            # Dynamic Flying Splash Droplets
            steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 2. Dynamic Flying Water Splashes"}})
            droplet_coords = [
                (s(180), s(490)), (s(210), s(460)), (s(230), s(520)),
                (s(590), s(510)), (s(620), s(470)), (s(640), s(520)),
            ]
            for idx, (dx, dy) in enumerate(droplet_coords, start=1):
                steps.append({
                    "cmd": "paint.stroke",
                    "params": {
                        "name": f"Refinement: Water Splash Droplet {idx}",
                        "points": [[dx, dy, 1.0], [dx + s(1), dy + s(1), 1.0]],
                        "size": max(3.0, s(5.0 + (idx % 3) * 1.5)),
                        "color": "#e0f7fa" if idx % 2 == 0 else "#ffffff",
                        "hardness": 1.0,
                        "opacity": 0.95,
                    },
                })
        elif is_moose:
            # Left eye pupil & catchlight
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Eye Dark Pupil",
                    "points": [[s(255), s(335), 1.0], [s(256), s(336), 1.0]],
                    "size": max(7.0, s(10.0)),
                    "color": "#111111",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Eye White Catchlight Dot",
                    "points": [[s(253), s(333), 1.0], [s(254), s(334), 1.0]],
                    "size": max(2.5, s(3.5)),
                    "color": "#ffffff",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Right eye pupil & catchlight
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Eye Dark Pupil",
                    "points": [[s(315), s(335), 1.0], [s(316), s(336), 1.0]],
                    "size": max(7.0, s(10.0)),
                    "color": "#111111",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Eye White Catchlight Dot",
                    "points": [[s(313), s(333), 1.0], [s(314), s(334), 1.0]],
                    "size": max(2.5, s(3.5)),
                    "color": "#ffffff",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Snout smile parting line
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Snout Smile Division Line",
                    "points": stroke_bezier((s(255), s(420)), (s(280), s(428)), (s(300), s(428)), (s(325), s(418))),
                    "size": 3.5,
                    "color": "#3e2723",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            # Inner ear crease lines
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Left Inner Ear Crease Line",
                    "points": stroke_line(s(212), s(255), s(230), s(250)),
                    "size": 3.0,
                    "color": "#5d4037",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Right Inner Ear Crease Line",
                    "points": stroke_line(s(335), s(252), s(352), s(250)),
                    "size": 3.0,
                    "color": "#5d4037",
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 2. Secondary Anatomy & Fur Accents"}})
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Chin Dewlap Bell Tuft",
                    "points": stroke_bezier((s(265), s(435)), (s(270), s(460)), (s(275), s(465)), (s(280), s(440))),
                    "size": 3.8,
                    "color": "#3e2723",
                    "hardness": 1.0,
                    "opacity": 0.9,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Antler Underside Ridge Shadow",
                    "points": stroke_line(s(230), s(220), s(160), s(180), steps=6),
                    "size": 4.0,
                    "color": "#8d6e63",
                    "hardness": 0.8,
                    "opacity": 0.7,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Focal Accent Line",
                    "points": stroke_line(s(360), s(320), s(440), s(320)),
                    "size": 3.5,
                    "color": ink_color,
                    "hardness": 0.95,
                    "opacity": 1.0,
                },
            })

    else:
        # =========================================================================
        # PHASE 4: MASTER VECTOR INKING & BRILLIANT SPECULAR LIGHTING
        # =========================================================================
        if is_moose:
            critique = (
                f"Pass {loop_iteration}/{total_iterations} [Master Inking & Specular Lighting]: Tracing weighted master ink contours "
                "along the antlers, head, and hooves, and placing brilliant white specular catchlights on antler tips and snout bridge."
            )
        else:
            critique = (
                f"Pass {loop_iteration}/{total_iterations} [Master Inking & Specular Lighting]: Tracing weighted master vector ink "
                "contours for maximum graphic punch and silhouette clarity, and placing brilliant specular gleams on head and water."
            )

        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 1. Master Vector Contours"}})
        if is_duck:
            # Weighted outer ink outline
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Head & Bill Contour",
                    "points": stroke_bezier((s(430), s(240)), (s(510), s(220)), (s(550), s(270)), (s(610), s(330))),
                    "size": 5.2,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Wing Ink Contour",
                    "points": stroke_bezier((s(350), s(450)), (s(420), s(430)), (s(510), s(460)), (s(450), s(520))),
                    "size": 4.5,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
        elif is_moose:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Left Antler Contour",
                    "points": stroke_bezier((s(140), s(130)), (s(200), s(170)), (s(240), s(230)), (s(250), s(260))),
                    "size": 4.8,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Right Antler Contour",
                    "points": stroke_bezier((s(410), s(120)), (s(360), s(170)), (s(330), s(230)), (s(325), s(260))),
                    "size": 4.8,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Head & Muzzle Contour",
                    "points": stroke_bezier((s(240), s(280)), (s(250), s(420)), (s(330), s(420)), (s(340), s(280))),
                    "size": 4.5,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })
        else:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": "Refinement: Master Outer Contour",
                    "points": stroke_line(s(280), s(450), s(520), s(450)),
                    "size": 5.0,
                    "color": ink_color,
                    "hardness": 1.0,
                    "opacity": 1.0,
                },
            })

        steps.append({"cmd": "layer.new.layer", "params": {"name": f"Refinement {loop_iteration}: 2. Brilliant Specular Gleams"}})
        if is_moose:
            gleams = [
                (s(150), s(130), "Left Antler Tip Specular Glint"),
                (s(420), s(125), "Right Antler Tip Specular Glint"),
                (s(280), s(365), "Snout Bridge Specular Gloss"),
                (s(440), s(410), "Back Spine Specular Accent"),
            ]
        elif is_duck:
            gleams = [
                (s(460), s(240), "Head Crest Specular Gleam"),
                (s(560), s(315), "Bill Bridge Specular Glint"),
                (s(380), s(440), "Wing Highlight Arc"),
            ]
        else:
            gleams = [
                (s(400), s(300), "Focal Specular Gleam"),
                (s(460), s(340), "Secondary Specular Glint"),
            ]
        for gx, gy, gname in gleams:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Refinement: {gname}",
                    "points": stroke_line(gx, gy, gx + s(14), gy + s(4), steps=6),
                    "size": 3.6,
                    "color": highlight_color,
                    "hardness": 1.0,
                    "opacity": 0.95,
                },
            })

    title = format_document_title(
        f"{prompt.title()} Refine {loop_iteration}",
        style=style,
        detail_level=detail,
        model=model,
    )

    return {
        "title": title,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "model": model.strip().replace(":", "-").replace("/", "-"),
        "steps": steps,
        "critique": critique,
        "is_refinement": True,
    }


"""Built-in painterly and vector artwork compositions simulating a human artist with adjustable detail levels (1 to 25)."""

from __future__ import annotations

import math
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
    stroke_sketch_oval,
)
from photocraft_painter.styles import get_style


def plan_painterly_rubber_duck(
    width: int = 800, height: int = 800, detail_level: int = 5, style: str = "realistic"
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
    elif style_preset.id == "dreamlike":
        bg = "#16122c"
    elif style_preset.id == "cartoon":
        bg = "#ffffff"
    elif style_preset.id == "abstract":
        bg = "#111822"

    return {
        "title": f"Painterly Rubber Duck [{style_preset.name}] (Detail {detail}/25)",
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "steps": steps,
    }


def plan_painterly_sunset(
    width: int = 800, height: int = 800, detail_level: int = 5, style: str = "realistic"
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
    elif style_preset.id == "dreamlike":
        bg = "#0d0a21"
    elif style_preset.id == "cartoon":
        bg = "#f0f4f8"
    elif style_preset.id == "abstract":
        bg = "#0f141c"

    return {
        "title": f"Mountain Sunset at Dusk [{style_preset.name}] (Detail {detail}/25)",
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "steps": steps,
    }


def plan_painterly_racecar(
    width: int = 800, height: int = 800, detail_level: int = 5, style: str = "realistic"
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
    elif style_preset.id == "dreamlike":
        bg = "#140e26"
    elif style_preset.id == "cartoon":
        bg = "#ffffff"
    elif style_preset.id == "abstract":
        bg = "#161b22"

    return {
        "title": f"Painterly Racecar [{style_preset.name}] (Detail {detail}/25)",
        "width": width,
        "height": height,
        "background": bg,
        "detail_level": detail,
        "style": style_preset.id,
        "steps": steps,
    }


def plan_painterly_pikachu(
    width: int = 800, height: int = 800, detail_level: int = 5, style: str = "realistic"
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
        "#fdfefe" if style_preset.id == "sketchy" else
        "#111822" if style_preset.id == "abstract" else
        "#16122c" if style_preset.id == "dreamlike" else
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

    title = f"Painterly Pikachu [{style_preset.name}] (Detail {detail}/25)"
    return {
        "title": title,
        "background": bg_color,
        "width": width,
        "height": height,
        "detail_level": detail,
        "style": style_preset.id,
        "steps": steps,
    }


def plan_dynamic_artwork(
    prompt: str, width: int = 800, height: int = 800, detail_level: int = 5, style: str = "realistic"
) -> dict[str, Any]:
    """Generate an authentic custom painterly study dynamically themed around any arbitrary prompt.
    
    A higher detail_level (1 to 25) scales the number and density of brushstrokes across all layers.
    At detail level 5, ~50-60 brush strokes are generated; at detail level 25, ~250 brush strokes are generated.
    """
    style_preset = get_style(style)
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
                "size": 3.8,
                "color": pal["ink"],
                "hardness": 0.95,
                "opacity": 1.0,
            },
        })
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
        "title": f"Painterly Study: {prompt.title()} [{style_preset.name}] (Detail {detail}/25)",
        "width": width,
        "height": height,
        "background": pal["bg"],
        "detail_level": detail,
        "style": style_preset.id,
        "steps": steps,
    }


def plan_fallback(
    prompt: str,
    width: int = 800,
    height: int = 800,
    detail_level: int = 5,
    style: str = "realistic",
) -> dict[str, Any]:
    """Select the best matching painterly plan based on prompt keywords, detail level (1 to 25), and style."""
    lowered = prompt.lower()

    if any(k in lowered for k in ["pikachu", "pika", "pokemon"]):
        return plan_painterly_pikachu(width, height, detail_level, style=style)

    if any(k in lowered for k in ["car", "racecar", "auto", "vehicle", "speed", "formula", "truck"]):
        return plan_painterly_racecar(width, height, detail_level, style=style)

    if any(k in lowered for k in ["sunset", "mountain", "dusk", "horizon", "lake", "ocean", "landscape"]):
        return plan_painterly_sunset(width, height, detail_level, style=style)

    if any(k in lowered for k in ["duck", "rubber duck", "bath", "quack"]):
        return plan_painterly_rubber_duck(width, height, detail_level, style=style)

    # For any other prompt, create an authentic dynamic composition matching the user's specific prompt
    return plan_dynamic_artwork(prompt, width, height, detail_level, style=style)

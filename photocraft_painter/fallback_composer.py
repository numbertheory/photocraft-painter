"""Built-in painterly and vector artwork compositions simulating a human artist with adjustable detail levels."""

from __future__ import annotations

from typing import Any

from photocraft_painter.strokes import (
    stroke_arc,
    stroke_bezier,
    stroke_hatching,
    stroke_line,
    stroke_painterly_fill,
    stroke_sketch_oval,
)


def plan_painterly_rubber_duck(width: int = 800, height: int = 800, detail_level: int = 3) -> dict[str, Any]:
    """Generate drawing steps recreating an artist sketching and painting a rubber duck.
    
    A higher detail_level (1 to 5) scales the number and density of brushstrokes across all layers.
    """
    detail = max(1, min(detail_level, 5))
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
            "points": stroke_sketch_oval(s(320), s(420), s(150), s(105), tilt_deg=-4, passes=1.0 + 0.08 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.85,
            "opacity": 0.7,
        },
    })

    if detail >= 2:
        # Head gesture circle
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Head Gesture",
                "points": stroke_sketch_oval(s(460), s(290), s(85), s(80), passes=1.0 + 0.08 * detail),
                "size": 3.0,
                "color": "#7f8c8d",
                "hardness": 0.85,
                "opacity": 0.7,
            },
        })

    if detail >= 3:
        # Beak wedge guide
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
        # Chest line guide
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

    if detail >= 4:
        # Tail posture guide
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
        # Eye placement guide crosshair
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Eye Placement Crosshair",
                "points": stroke_line(s(435), s(275), s(455), s(275)),
                "size": 2.0,
                "color": "#bdc3c7",
                "hardness": 0.8,
                "opacity": 0.6,
            },
        })

    if detail >= 5:
        # Construction tangents & anatomical posture guides
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
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Sketch: Water Ripple Oval",
                "points": stroke_sketch_oval(s(330), s(535), s(220), s(35), passes=1.1),
                "size": 2.2,
                "color": "#aed6f1",
                "hardness": 0.7,
                "opacity": 0.6,
            },
        })

    # =========================================================================
    # STAGE 2: WATER BASE (Broad painterly brush sweeps)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Water Paint Wash"}})

    water_layers = [
        ("Water Wash: Deep Abyss", (0, s(720)), (s(250), s(700)), (s(550), s(730)), (width, s(710)), 90.0, "#1a5276", 0.95),
        ("Water Wash: Deep", (0, s(640)), (s(300), s(620)), (s(600), s(650)), (width, s(630)), 80.0, "#1f618d", 0.9),
        ("Water Wash: Mid", (0, s(575)), (s(320), s(555)), (s(580), s(585)), (width, s(570)), 68.0, "#2980b9", 0.9),
        ("Water Wash: Surface", (0, s(530)), (s(350), s(515)), (s(600), s(540)), (width, s(525)), 52.0, "#3498db", 0.9),
        ("Water Wash: Horizon Glint", (0, s(515)), (s(380), s(505)), (s(620), s(520)), (width, s(510)), 38.0, "#5dade2", 0.85),
    ]

    # Select water sweep count based on detail level
    count_water = 1 if detail == 1 else (2 if detail == 2 else (3 if detail == 3 else (4 if detail == 4 else 5)))
    for w_name, p0, p1, p2, p3, w_size, w_col, w_op in water_layers[:count_water]:
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": w_name,
                "points": stroke_bezier(p0, p1, p2, p3, steps=25),
                "size": w_size,
                "color": w_col,
                "hardness": 0.5,
                "opacity": w_op,
            },
        })

    # =========================================================================
    # STAGE 3: COLOR WASH (Painterly yellow & orange blocking)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Duck Body Paint"}})

    # Spacing determines stroke density: higher detail = tighter spacing = more brushstrokes!
    # Detail 1: ~4 sweeps, Detail 2: ~6 sweeps, Detail 3: ~9 sweeps, Detail 4: ~14 sweeps, Detail 5: ~22 sweeps!
    body_spacing = {1: 42.0, 2: 30.0, 3: 20.0, 4: 13.0, 5: 8.5}[detail]
    head_spacing = {1: 36.0, 2: 26.0, 3: 18.0, 4: 11.5, 5: 7.5}[detail]
    body_brush_size = {1: 65.0, 2: 54.0, 3: 46.0, 4: 36.0, 5: 28.0}[detail]
    head_brush_size = {1: 52.0, 2: 44.0, 3: 38.0, 4: 30.0, 5: 24.0}[detail]

    # Body yellow fill strokes
    for idx, sweep in enumerate(stroke_painterly_fill(s(320), s(420), s(140), s(95), spacing=s(body_spacing)), start=1):
        # Slightly modulate tone at higher detail levels for painterly richness
        col = "#ffd700" if (idx % 2 == 0 or detail < 4) else "#ffda33"
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Paint Wash: Body Sweep {idx}",
                "points": sweep,
                "size": s(body_brush_size),
                "color": col,
                "hardness": 0.6,
                "opacity": 0.95,
            },
        })

    # Head yellow fill strokes
    for idx, sweep in enumerate(stroke_painterly_fill(s(460), s(290), s(80), s(75), spacing=s(head_spacing)), start=1):
        col = "#ffd700" if (idx % 2 == 0 or detail < 4) else "#ffe04d"
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Paint Wash: Head Sweep {idx}",
                "points": sweep,
                "size": s(head_brush_size),
                "color": col,
                "hardness": 0.6,
                "opacity": 0.95,
            },
        })

    # Tail feather wash
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Paint Wash: Tail",
            "points": stroke_bezier((s(210), s(410)), (s(160), s(380)), (s(170), s(440)), (s(210), s(440))),
            "size": s(32.0),
            "color": "#ffd700",
            "hardness": 0.65,
        },
    })
    if detail >= 4:
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

    # Beak orange wash
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
                "name": "Paint Wash: Beak Top Lip",
                "points": stroke_bezier((s(510), s(318)), (s(545), s(315)), (s(565), s(325)), (s(515), s(330))),
                "size": s(16.0),
                "color": "#ff9100",
                "hardness": 0.75,
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
        # Wing underside shadow
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
        # Beak crease shadow
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
        # Cheek blush
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

    if detail >= 4:
        # Neck occlusion shadow
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
        # Water contact ambient occlusion shadow
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

    if detail >= 5:
        # Cross-hatching brush texture for deeper modeling on belly
        hatch_strokes = stroke_hatching(s(310), s(485), s(160), s(35), count=9, angle_deg=35)
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

    # =========================================================================
    # STAGE 5: INKING & CONTOUR LINES (Confident ink pen & brush lines)
    # =========================================================================
    steps.append({"cmd": "layer.new.layer", "params": {"name": "5. Ink Outlines"}})

    # Tail tip curve
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Tail Feather",
            "points": stroke_bezier((s(210), s(385)), (s(165), s(370)), (s(175), s(435)), (s(230), s(455))),
            "size": s(6.5),
            "color": "#2c3e50",
            "hardness": 0.95,
        },
    })

    # Back to neck contour
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Back to Neck",
            "points": stroke_bezier((s(230), s(385)), (s(300), s(375)), (s(380), s(355)), (s(405), s(340))),
            "size": s(7.0),
            "color": "#2c3e50",
            "hardness": 0.95,
        },
    })

    # Breast and belly contour
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Breast & Belly",
            "points": stroke_bezier((s(225), s(455)), (s(320), s(515)), (s(420), s(505)), (s(470), s(410))),
            "size": s(7.5),
            "color": "#2c3e50",
            "hardness": 0.95,
        },
    })

    # Head crown arc
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Head Crown",
            "points": stroke_arc(s(460), s(290), s(82), s(78), 150, 360, steps=35),
            "size": s(6.5),
            "color": "#2c3e50",
            "hardness": 0.95,
        },
    })

    # Beak contour
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Beak Outline",
            "points": stroke_bezier((s(495), s(315)), (s(555), s(310)), (s(585), s(332)), (s(515), s(350))),
            "size": s(6.0),
            "color": "#873600",
            "hardness": 0.9,
        },
    })

    # Wing contour
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Wing Contour",
            "points": stroke_bezier((s(250), s(415)), (s(315), s(375)), (s(395), s(420)), (s(330), s(470))),
            "size": s(7.0),
            "color": "#34495e",
            "hardness": 0.95,
        },
    })

    # Eye circle & pupil
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Eye Contour",
            "points": stroke_arc(s(445), s(275), s(15), s(18), 0, 360, steps=25),
            "size": s(5.0),
            "color": "#1a1a1a",
            "hardness": 0.95,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Ink: Eye Pupil",
            "points": stroke_arc(s(447), s(277), s(9), s(12), 0, 360, steps=20),
            "size": s(11.0),
            "color": "#1a1a1a",
            "hardness": 0.95,
        },
    })

    if detail >= 4:
        # Wing internal feather separation curves
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
        # Beak smile / nostril line
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
        # Calligraphy feather texturing & fine plumage accents
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
        # Head top glint
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
        # Primary water ripple
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

    if detail >= 3:
        # Secondary ripple
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
        # Soap bubbles
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

    if detail >= 4:
        # Beak specular highlight
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
        # Extra bubbles & foam crescents
        for b_name, bx, by, br in [
            ("Detail: Bubble 3", s(510), s(525), s(11)),
            ("Detail: Bubble 4", s(540), s(505), s(8)),
            ("Detail: Bubble 5", s(110), s(510), s(14)),
        ]:
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": b_name,
                    "points": stroke_arc(bx, by, br, br, 0, 360, steps=18),
                    "size": s(2.5),
                    "color": "#ffffff",
                    "hardness": 0.9,
                },
            })

    if detail >= 5:
        # Rim lighting along duck's back and head crown
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
        # Secondary eye sparkle glint (double catchlight)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": "Highlight: Secondary Eye Glint",
                "points": stroke_line(s(443), s(281), s(443), s(282), steps=3),
                "size": s(3.5),
                "color": "#ffffff",
                "hardness": 1.0,
            },
        })
        # Water surface shimmer lines
        for sh_idx, (sx, sy, sw) in enumerate([
            (s(280), s(585), s(120)),
            (s(360), s(615), s(160)),
            (s(230), s(645), s(100)),
        ], start=1):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Detail: Deep Shimmer {sh_idx}",
                    "points": stroke_line(sx, sy, sx + sw, sy, steps=12),
                    "size": s(3.0),
                    "color": "#85c1e9",
                    "hardness": 0.7,
                    "opacity": 0.65,
                },
            })

    return {
        "title": f"Painterly Rubber Duck (Detail {detail}/5)",
        "width": width,
        "height": height,
        "background": "#eef7fa",
        "detail_level": detail,
        "steps": steps,
    }


def plan_painterly_sunset(width: int = 800, height: int = 800, detail_level: int = 3) -> dict[str, Any]:
    """Generate drawing steps recreating an artist painting a mountain sunset."""
    detail = max(1, min(detail_level, 5))
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

    # 2. Sky gradient paint wash (more bands with higher detail)
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Sunset Sky Wash"}})
    all_colors = ["#78281f", "#922b21", "#b03a2e", "#c0392b", "#d35400", "#e67e22", "#eb984e", "#f39c12", "#f7dc6f", "#fef9e7"]
    band_count = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}[detail]
    selected_colors = all_colors[:band_count]
    spacing = 480.0 / band_count

    for i, col in enumerate(selected_colors):
        y = s(40 + i * spacing)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Sky Wash: Band {i+1}",
                "points": stroke_bezier((0, y), (s(250), y - 10), (s(550), y + 10), (width, y)),
                "size": s(spacing * 1.3),
                "color": col,
                "hardness": 0.45,
                "opacity": 0.9,
            },
        })

    # Sun disk
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sun: Glowing Disk",
            "points": stroke_arc(s(400), s(360), s(60), s(60), 0, 360),
            "size": s(55.0),
            "color": "#fff9c4",
            "hardness": 0.6,
        },
    })

    # 3. Mountain brushwork
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Mountain Silhouettes"}})
    mountains = [
        [(s(40), s(520)), (s(220), s(340)), (s(380), s(520)), "#4a235a"],
        [(s(320), s(520)), (s(520), s(360)), (s(700), s(520)), "#341f47"],
        [(s(600), s(520)), (s(720), s(420)), (s(800), s(520)), "#2c193e"],
        [(0, s(520)), (s(100), s(430)), (s(240), s(520)), "#211330"],
    ]
    m_count = 2 if detail <= 2 else (3 if detail <= 4 else 4)
    for idx, (p0, p1, p2, col) in enumerate(mountains[:m_count], start=1):
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

    # 4. Lake wash & reflections (more ripples at higher detail)
    steps.append({"cmd": "layer.new.layer", "params": {"name": "4. Lake & Shimmer"}})
    steps.append({
        "cmd": "shape.create",
        "params": {"kind": "rect", "rect": [0, s(520), width, s(280)], "fill": "#1b2631", "name": "Lake Deep Water"},
    })

    ripple_count = {1: 3, 2: 5, 3: 8, 4: 12, 5: 18}[detail]
    for i in range(ripple_count):
        y = s(535 + i * (240.0 / ripple_count))
        w = s(140 + i * 25)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Lake Shimmer: Ripple {i+1}",
                "points": stroke_line(s(400) - w * 0.5, y, s(400) + w * 0.5, y, steps=12),
                "size": max(2.5, s(8.0 - i * 0.3)),
                "color": "#f39c12" if i % 2 == 0 else "#f5b041",
                "hardness": 0.6,
                "opacity": max(0.4, 0.85 - i * 0.03),
            },
        })

    return {
        "title": f"Mountain Sunset at Dusk (Detail {detail}/5)",
        "width": width,
        "height": height,
        "background": "#110e1b",
        "detail_level": detail,
        "steps": steps,
    }


def plan_painterly_racecar(width: int = 800, height: int = 800, detail_level: int = 3) -> dict[str, Any]:
    """Generate drawing steps recreating an artist sketching and painting an aerodynamic racecar."""
    detail = max(1, min(detail_level, 5))
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
            "points": stroke_sketch_oval(s(220), s(530), s(55), s(55), passes=1.0 + 0.08 * detail),
            "size": 3.0,
            "color": "#7f8c8d",
            "hardness": 0.8,
        },
    })
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": "Sketch: Rear Wheel Guide",
            "points": stroke_sketch_oval(s(580), s(530), s(60), s(60), passes=1.0 + 0.08 * detail),
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

    # 2. CAR BODY WASH
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Car Body Paint"}})
    passes = {1: 4, 2: 7, 3: 11, 4: 16, 5: 24}[detail]
    for i in range(passes):
        t = i / max(1, passes - 1)
        y = s(460 + t * 60)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Body Paint: Red Sweep {i+1}",
                "points": stroke_line(s(130 + t * 40), y, s(680 - t * 30), y, steps=15, wobble=0.8),
                "size": max(12.0, s(35.0 - t * 10)),
                "color": "#e74c3c" if i % 2 == 0 else "#c0392b",
                "hardness": 0.65,
                "opacity": 0.85,
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
    if detail >= 4:
        hatch = stroke_hatching(s(180), s(480), s(60), s(40), count=6, angle_deg=45)
        for hi, line in enumerate(hatch):
            steps.append({
                "cmd": "paint.stroke",
                "params": {
                    "name": f"Hatching: Fender Tone {hi+1}",
                    "points": line,
                    "size": 2.0,
                    "color": "#641e16",
                    "hardness": 0.85,
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
    streak_count = {1: 2, 2: 3, 3: 5, 4: 8, 5: 12}[detail]
    for si in range(streak_count):
        sy = s(420 + si * 14)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Speed Accent: Trail {si+1}",
                "points": stroke_line(s(700 + si * 8), sy, s(760 + si * 10), sy),
                "size": max(1.5, s(3.5 - si * 0.2)),
                "color": "#e74c3c" if si % 2 == 0 else "#f39c12",
                "hardness": 0.75,
                "opacity": 0.8,
            },
        })

    return {
        "title": f"Painterly Racecar (Detail {detail}/5)",
        "width": width,
        "height": height,
        "background": "#141419",
        "detail_level": detail,
        "steps": steps,
    }


def plan_dynamic_artwork(prompt: str, width: int = 800, height: int = 800, detail_level: int = 3) -> dict[str, Any]:
    """Generate an authentic custom painterly study dynamically themed around any arbitrary prompt."""
    detail = max(1, min(detail_level, 5))
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
    pal = palettes[h % len(palettes)]

    # 1. Sketch layer
    steps.append({"cmd": "layer.new.layer", "params": {"name": f"1. Sketch: {prompt.title()}"}})
    steps.append({
        "cmd": "paint.stroke",
        "params": {
            "name": f"Sketch: Gesture Oval ({prompt})",
            "points": stroke_sketch_oval(s(400), s(400), s(160), s(140), passes=1.0 + 0.1 * detail),
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

    # 2. Painterly Wash
    steps.append({"cmd": "layer.new.layer", "params": {"name": "2. Painterly Color Wash"}})
    passes = {1: 5, 2: 9, 3: 15, 4: 22, 5: 32}[detail]
    for i in range(passes):
        t = i / max(1, passes - 1)
        y = s(300 + t * 200)
        w = s(160 + (1.0 - abs(t - 0.5) * 2) * 120)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Color Wash: Sweep {i+1}",
                "points": stroke_line(s(400) - w, y, s(400) + w, y, steps=14, wobble=0.7),
                "size": max(10.0, s(32.0 - t * 8)),
                "color": pal["wash"] if i % 2 == 0 else pal["mid"],
                "hardness": 0.65,
                "opacity": 0.8,
            },
        })

    # 3. Form Shading
    steps.append({"cmd": "layer.new.layer", "params": {"name": "3. Form & Volume Shading"}})
    shading_passes = {1: 2, 2: 4, 3: 7, 4: 12, 5: 18}[detail]
    for si in range(shading_passes):
        st = si / max(1, shading_passes - 1)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Shading: Form Tone {si+1}",
                "points": stroke_bezier((s(280 + st * 40), s(460 + st * 30)), (s(380), s(510)), (s(460), s(510)), (s(520 - st * 30), s(470 + st * 20))),
                "size": max(8.0, s(22.0 - si * 0.8)),
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
    accent_count = {1: 1, 2: 2, 3: 4, 4: 7, 5: 10}[detail]
    for ai in range(accent_count):
        ay = s(340 + ai * 25)
        steps.append({
            "cmd": "paint.stroke",
            "params": {
                "name": f"Accent: Tint {ai+1}",
                "points": stroke_line(s(330 + ai * 15), ay, s(360 + ai * 15), ay),
                "size": max(2.5, s(6.0 - ai * 0.3)),
                "color": pal["accent"],
                "hardness": 0.75,
                "opacity": 0.85,
            },
        })

    return {
        "title": f"Painterly Study: {prompt.title()} (Detail {detail}/5)",
        "width": width,
        "height": height,
        "background": pal["bg"],
        "detail_level": detail,
        "steps": steps,
    }


def plan_fallback(prompt: str, width: int = 800, height: int = 800, detail_level: int = 3) -> dict[str, Any]:
    """Select the best matching painterly plan based on prompt keywords and detail level."""
    lowered = prompt.lower()

    if any(k in lowered for k in ["car", "racecar", "auto", "vehicle", "speed", "formula", "truck"]):
        return plan_painterly_racecar(width, height, detail_level)

    if any(k in lowered for k in ["sunset", "mountain", "dusk", "horizon", "lake", "ocean", "landscape"]):
        return plan_painterly_sunset(width, height, detail_level)

    if any(k in lowered for k in ["duck", "rubber duck", "bath", "quack"]):
        return plan_painterly_rubber_duck(width, height, detail_level)

    # For any other prompt, create an authentic dynamic composition matching the user's specific prompt
    return plan_dynamic_artwork(prompt, width, height, detail_level)

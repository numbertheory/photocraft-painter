"""Unit tests for PhotoCraft Painter composer, stroke generation, step normalization, and configuration."""

from photocraft_painter.config import PainterConfig
from photocraft_painter.composer import (
    densify_artwork_plan,
    extract_json_from_response,
    normalize_color,
    normalize_step,
    plan_artwork,
)
from photocraft_painter.fallback_composer import (
    plan_fallback,
    plan_painterly_rubber_duck,
    plan_painterly_sunset,
)
from photocraft_painter.strokes import (
    stroke_bezier,
    stroke_line,
    stroke_sketch_oval,
    stroke_painterly_fill,
)
from photocraft_painter.styles import STYLE_PRESETS, get_style


def test_config_defaults():
    config = PainterConfig()
    assert config.control_port == 7878
    assert config.control_host == "127.0.0.1"
    assert config.provider == "ollama"
    assert config.ollama_model == "ornith-1.5:35b"
    assert config.ollama_host == "http://127.0.0.1:11434"


def test_normalize_color():
    assert normalize_color("#ff0000") == "#ff0000"
    assert normalize_color("00ff00") == "#00ff00"
    assert normalize_color("#fff") == "#ffffff"
    assert normalize_color("none") is None
    assert normalize_color("null") is None
    assert normalize_color("transparent") is None


def test_normalize_stroke_step():
    # Coarse stroke should be smoothed into more points
    step = {
        "cmd": "paint.stroke",
        "params": {
            "name": "Quick Sketch Line",
            "points": [[100, 100], [200, 150], [300, 200]],
            "size": 5.0,
            "color": "#333333",
            "hardness": 0.8,
        },
    }
    normalized = normalize_step(step)
    assert normalized["cmd"] == "paint.stroke"
    assert len(normalized["params"]["points"]) > 3
    assert normalized["params"]["size"] == 5.0
    assert normalized["params"]["color"] == "#333333"


def test_normalize_layer_step():
    step = {"cmd": "layer.new.layer", "params": {"name": "Pencil Sketch"}}
    normalized = normalize_step(step)
    assert normalized["cmd"] == "layer.new.layer"
    assert normalized["params"]["name"] == "Pencil Sketch"


def test_stroke_generators():
    line = stroke_line(0, 0, 100, 100)
    assert len(line) >= 20
    assert abs(line[0][0] - 0.0) < 1.0

    bezier = stroke_bezier((0, 0), (50, 100), (100, 100), (150, 0))
    assert len(bezier) >= 30

    oval = stroke_sketch_oval(200, 200, 50, 40)
    assert len(oval) >= 40

    fills = stroke_painterly_fill(200, 200, 50, 40, spacing=15)
    assert len(fills) >= 3


def test_extract_json():
    wrapped = "Here is your drawing:\n```json\n{\"title\": \"Cat\", \"steps\": []}\n```\nHope you like it!"
    data = extract_json_from_response(wrapped)
    assert data["title"] == "Cat"
    assert data["steps"] == []


def test_extract_json_salvage_truncated():
    # Incomplete/truncated output where token limit cut off the 2nd step
    truncated = (
        '{\n'
        '  "title": "A Racecar",\n'
        '  "steps": [\n'
        '    {"cmd": "layer.new.layer", "params": {"name": "Sketch"}},\n'
        '    {"cmd": "paint.stroke", "params": {"name": "Body", "points": [[100, 100], [200, 200]]}},\n'
        '    {"cmd": "paint.stroke", "params": {"name": "Wheel", "points": [[300, 30'  # truncated mid-token
    )
    salvaged = extract_json_from_response(truncated)
    assert salvaged["title"] == "A Racecar"
    assert len(salvaged["steps"]) == 2
    assert salvaged["steps"][0]["params"]["name"] == "Sketch"
    assert salvaged["steps"][1]["params"]["name"] == "Body"



def test_painterly_rubber_duck_plan():
    duck = plan_painterly_rubber_duck(800, 800)
    assert "Painterly Rubber Duck" in duck["title"]
    assert duck["width"] == 800
    assert duck["height"] == 800
    # Checks that drawing contains multiple layers and brush strokes
    has_layers = any(s["cmd"] == "layer.new.layer" for s in duck["steps"])
    has_strokes = any(s["cmd"] == "paint.stroke" for s in duck["steps"])
    assert has_layers
    assert has_strokes
    assert len(duck["steps"]) >= 20


def test_painterly_sunset_plan():
    sunset = plan_painterly_sunset(800, 800)
    assert "Mountain Sunset at Dusk" in sunset["title"]
    assert len(sunset["steps"]) >= 15


def test_detail_level_scaling():
    # Rubber duck stroke and step counts scale strictly with detail level
    duck_l1 = plan_painterly_rubber_duck(800, 800, detail_level=1)
    duck_l5 = plan_painterly_rubber_duck(800, 800, detail_level=5)
    duck_l15 = plan_painterly_rubber_duck(800, 800, detail_level=15)
    duck_l25 = plan_painterly_rubber_duck(800, 800, detail_level=25)

    def stroke_count(plan: dict) -> int:
        return sum(1 for s in plan["steps"] if s["cmd"] == "paint.stroke")

    assert duck_l1["detail_level"] == 1
    assert duck_l5["detail_level"] == 5
    assert duck_l25["detail_level"] == 25

    # Total steps and stroke counts must strictly increase as detail level increases
    assert len(duck_l1["steps"]) < len(duck_l5["steps"]) < len(duck_l15["steps"]) < len(duck_l25["steps"])
    assert stroke_count(duck_l1) < stroke_count(duck_l5) < stroke_count(duck_l15) < stroke_count(duck_l25)

    # At detail level 5: ~50 brush strokes (~50-60); at detail level 25: ~250 brush strokes (~240-260)
    assert 45 <= stroke_count(duck_l5) <= 65
    assert 235 <= stroke_count(duck_l25) <= 265

    # Sunset lake shimmer ripples and strokes scale with detail level up to 25
    sunset_l1 = plan_painterly_sunset(800, 800, detail_level=1)
    sunset_l5 = plan_painterly_sunset(800, 800, detail_level=5)
    sunset_l25 = plan_painterly_sunset(800, 800, detail_level=25)
    assert stroke_count(sunset_l1) < stroke_count(sunset_l5) < stroke_count(sunset_l25)
    assert 45 <= stroke_count(sunset_l5) <= 65
    assert 235 <= stroke_count(sunset_l25) <= 265


def test_plan_artwork_detail_forwarding():
    # When using built-in procedural composer via plan_artwork
    cfg_low = PainterConfig(provider="none", detail_level=1)
    cfg_mid = PainterConfig(provider="none", detail_level=5)
    cfg_high = PainterConfig(provider="none", detail_level=25)

    plan_low, src_low = plan_artwork("rubber duck", cfg_low)
    plan_mid, src_mid = plan_artwork("rubber duck", cfg_mid)
    plan_high, src_high = plan_artwork("rubber duck", cfg_high)

    assert "Detail 1/25" in src_low
    assert "Detail 5/25" in src_mid
    assert "Detail 25/25" in src_high
    assert len(plan_low["steps"]) < len(plan_mid["steps"]) < len(plan_high["steps"])


def test_plan_fallback_routes_independently():
    # Prompt for racecar generates racecar, NOT rubber duck
    plan_car = plan_artwork("a red racecar", PainterConfig(provider="none"))[0]
    assert "Racecar" in plan_car["title"]

    # Prompt for duck generates rubber duck
    plan_duck = plan_artwork("a rubber duck", PainterConfig(provider="none"))[0]
    assert "Rubber Duck" in plan_duck["title"]

    # Prompt for sunset generates mountain sunset
    plan_sunset = plan_artwork("mountain sunset", PainterConfig(provider="none"))[0]
    assert "Mountain Sunset" in plan_sunset["title"]

    # Arbitrary prompt generates custom themed study with prompt title, NOT rubber duck
    plan_coffee = plan_artwork("a cozy cup of coffee", PainterConfig(provider="none"))[0]
    assert "A Cozy Cup Of Coffee" in plan_coffee["title"]
    assert "Rubber Duck" not in plan_coffee["title"]


def test_densify_artwork_plan_scales_ai_models():
    # Simulate a raw foundation plan returned by Ollama with ~48 strokes
    raw_ollama_plan = {
        "title": "A Racecar",
        "steps": (
            [{"cmd": "layer.new.layer", "params": {"name": "1. Sketch"}}]
            + [{"cmd": "paint.stroke", "params": {"name": f"Sketch Line {i}", "points": [[100 + i * 5, 100], [200 + i * 5, 200]], "size": 3.0, "color": "#777777"}} for i in range(8)]
            + [{"cmd": "layer.new.layer", "params": {"name": "2. Body Paint"}}]
            + [{"cmd": "paint.stroke", "params": {"name": f"Paint Wash {i}", "points": [[120 + i * 10, 300], [400 + i * 10, 300]], "size": 35.0, "color": "#e74c3c"}} for i in range(15)]
            + [{"cmd": "layer.new.layer", "params": {"name": "3. Shading"}}]
            + [{"cmd": "paint.stroke", "params": {"name": f"Shading {i}", "points": [[150 + i * 10, 350], [350 + i * 10, 350]], "size": 18.0, "color": "#78281f"}} for i in range(12)]
            + [{"cmd": "layer.new.layer", "params": {"name": "4. Ink Contours"}}]
            + [{"cmd": "paint.stroke", "params": {"name": f"Ink Outline {i}", "points": [[100 + i * 10, 320], [300 + i * 10, 320]], "size": 4.0, "color": "#111116"}} for i in range(10)]
            + [{"cmd": "layer.new.layer", "params": {"name": "5. Highlights"}}]
            + [{"cmd": "paint.stroke", "params": {"name": f"Highlight {i}", "points": [[200 + i * 20, 280], [250 + i * 20, 280]], "size": 5.0, "color": "#ffffff"}} for i in range(3)]
        ),
    }

    def count_strokes(p: dict) -> int:
        return sum(1 for s in p["steps"] if s["cmd"] == "paint.stroke")

    assert count_strokes(raw_ollama_plan) == 48

    # Detail 5: should preserve or meet ~50 strokes
    plan_d5 = densify_artwork_plan(raw_ollama_plan, detail_level=5)
    assert count_strokes(plan_d5) == 50

    # Detail 15: scales to 150 strokes
    plan_d15 = densify_artwork_plan(raw_ollama_plan, detail_level=15)
    assert count_strokes(plan_d15) == 150

    # Detail 25: scales to ~250 strokes
    plan_d25 = densify_artwork_plan(raw_ollama_plan, detail_level=25)
    assert count_strokes(plan_d25) == 250

    # Child strokes must be in valid layers and have non-empty coordinates
    for st in plan_d25["steps"]:
        if st["cmd"] == "paint.stroke":
            assert len(st["params"]["points"]) >= 2
            assert st["params"]["size"] > 0
            assert st["params"]["color"].startswith("#")


def test_style_presets_and_lookup():
    expected_styles = ["realistic", "dreamlike", "abstract", "sketchy", "cartoon", "painterly"]
    for s_name in expected_styles:
        assert s_name in STYLE_PRESETS
        preset = get_style(s_name)
        assert preset.id == s_name
        assert len(preset.name) > 0
        assert len(preset.description) > 0
        assert len(preset.ai_guidance) > 0

    # Case-insensitive resolution
    assert get_style("DREAMLIKE").id == "dreamlike"
    assert get_style("Cartoon").id == "cartoon"
    assert get_style("   sKeTchY  ").id == "sketchy"

    # Default fallback to realistic for missing/invalid
    assert get_style(None).id == "realistic"
    assert get_style("").id == "realistic"
    assert get_style("nonexistent_style_xyz").id == "realistic"


def test_style_color_adjustment():
    sketchy = get_style("sketchy")
    cartoon = get_style("cartoon")
    dreamlike = get_style("dreamlike")
    abstract = get_style("abstract")
    realistic = get_style("realistic")

    orig_color = "#3498db"
    # Sketchy should desaturate towards graphite
    adj_sketchy = sketchy.adjust_color(orig_color)
    assert adj_sketchy.startswith("#")
    assert adj_sketchy != orig_color

    # Cartoon should enhance contrast
    adj_cartoon = cartoon.adjust_color(orig_color)
    assert adj_cartoon.startswith("#")

    # Dreamlike shifts towards luminous pastel
    adj_dream = dreamlike.adjust_color(orig_color)
    assert adj_dream.startswith("#")

    # Abstract pops vibrant tones
    adj_abs = abstract.adjust_color(orig_color)
    assert adj_abs.startswith("#")

    # None or non-hex returns as-is safely
    assert realistic.adjust_color(None) is None
    assert realistic.adjust_color("transparent") == "transparent"


def test_densify_artwork_plan_with_styles():
    raw_plan = {
        "title": "A Bird",
        "steps": [
            {"cmd": "layer.new.layer", "params": {"name": "1. Sketch"}},
            {"cmd": "paint.stroke", "params": {"name": "Guide Oval", "points": [[100, 100], [200, 200]], "size": 3.0, "color": "#555555"}},
            {"cmd": "layer.new.layer", "params": {"name": "2. Body Paint"}},
            {"cmd": "paint.stroke", "params": {"name": "Body Wash", "points": [[120, 300], [400, 300]], "size": 30.0, "color": "#3498db"}},
            {"cmd": "layer.new.layer", "params": {"name": "3. Shading"}},
            {"cmd": "paint.stroke", "params": {"name": "Belly Shade", "points": [[150, 350], [350, 350]], "size": 18.0, "color": "#1b4f72"}},
            {"cmd": "layer.new.layer", "params": {"name": "4. Ink Contours"}},
            {"cmd": "paint.stroke", "params": {"name": "Wing Ink", "points": [[100, 320], [300, 320]], "size": 4.0, "color": "#111116"}},
            {"cmd": "layer.new.layer", "params": {"name": "5. Highlights"}},
            {"cmd": "paint.stroke", "params": {"name": "Eye Highlight", "points": [[200, 280], [220, 280]], "size": 5.0, "color": "#ffffff"}},
        ],
    }

    # Cartoon style densification produces solid crisp outlines
    plan_cartoon = densify_artwork_plan(raw_plan, detail_level=10, style="cartoon")
    assert plan_cartoon["style"] == "cartoon"
    cartoon_contours = [
        s for s in plan_cartoon["steps"]
        if s.get("cmd") == "paint.stroke" and "Ink Contour" in s["params"].get("name", "")
    ]
    assert len(cartoon_contours) > 0
    for c in cartoon_contours:
        assert c["params"]["hardness"] == 1.0
        assert c["params"]["opacity"] == 1.0

    # Sketchy style densification produces pencil guides & hatching
    plan_sketchy = densify_artwork_plan(raw_plan, detail_level=10, style="sketchy")
    assert plan_sketchy["style"] == "sketchy"
    sketchy_hatches = [
        s for s in plan_sketchy["steps"]
        if s.get("cmd") == "paint.stroke" and "Pencil Hatch" in s["params"].get("name", "")
    ]
    assert len(sketchy_hatches) > 0
    for h in sketchy_hatches:
        assert h["params"]["hardness"] == 0.9

    # Dreamlike style densification produces soft luminous aura flares
    plan_dream = densify_artwork_plan(raw_plan, detail_level=10, style="dreamlike")
    assert plan_dream["style"] == "dreamlike"
    dream_flares = [
        s for s in plan_dream["steps"]
        if s.get("cmd") == "paint.stroke" and "Aura Flare" in s["params"].get("name", "")
    ]
    assert len(dream_flares) > 0
    for f in dream_flares:
        assert f["params"]["hardness"] == 0.5


def test_plan_fallback_with_styles():
    duck_dream = plan_fallback("rubber duck", style="dreamlike")
    assert "Dreamlike" in duck_dream["title"]
    assert duck_dream["style"] == "dreamlike"
    assert duck_dream["background"] == "#16122c"

    car_sketch = plan_fallback("a red racecar", style="sketchy")
    assert "Sketchy" in car_sketch["title"]
    assert car_sketch["style"] == "sketchy"
    assert car_sketch["background"] == "#fdfefe"

    sunset_cartoon = plan_fallback("mountain sunset", style="cartoon")
    assert "Cartoon" in sunset_cartoon["title"]
    assert sunset_cartoon["style"] == "cartoon"
    assert sunset_cartoon["background"] == "#f0f4f8"

    dynamic_abstract = plan_fallback("cup of coffee", style="abstract")
    assert "Abstract" in dynamic_abstract["title"]
    assert dynamic_abstract["style"] == "abstract"
    assert dynamic_abstract["background"] == "#17202a"


def test_plan_artwork_style_forwarding():
    cfg_cartoon = PainterConfig(provider="none", style="cartoon", detail_level=5)
    plan_c, src_c = plan_artwork("rubber duck", cfg_cartoon)
    assert "[Cartoon]" in src_c
    assert "[Cartoon]" in plan_c["title"]
    assert plan_c["style"] == "cartoon"

    cfg_dream = PainterConfig(provider="none", style="dreamlike", detail_level=8)
    plan_d, src_d = plan_artwork("mountain sunset", cfg_dream)
    assert "[Dreamlike]" in src_d
    assert "[Dreamlike]" in plan_d["title"]
    assert plan_d["style"] == "dreamlike"




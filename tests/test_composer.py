"""Unit tests for PhotoCraft Painter composer, stroke generation, step normalization, and configuration."""

from photocraft_painter.config import PainterConfig
from photocraft_painter.composer import (
    extract_json_from_response,
    normalize_color,
    normalize_step,
    plan_artwork,
)
from photocraft_painter.fallback_composer import plan_painterly_rubber_duck, plan_painterly_sunset
from photocraft_painter.strokes import (
    stroke_bezier,
    stroke_line,
    stroke_sketch_oval,
    stroke_painterly_fill,
)


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



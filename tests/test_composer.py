import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from photocraft_painter.config import PainterConfig
from photocraft_painter.composer import (
    compose_with_ollama,
    densify_artwork_plan,
    expand_step,
    extract_json_from_response,
    get_face_feature_bounds,
    is_facial_feature_stroke,
    is_hair_stroke,
    normalize_color,
    normalize_step,
    parse_prompt_and_images,
    plan_artwork,
    plan_refinement_artwork,
    REFINEMENT_SYSTEM_PROMPT,
    sanitize_hair_strokes_against_face,
    validate_image_files,
)
from photocraft_painter.fallback_composer import (
    format_document_title,
    is_portrait_or_face_prompt,
    parse_geometric_shape_prompt,
    plan_dynamic_artwork,
    plan_fallback,
    plan_painterly_geometric_shape,
    plan_painterly_pikachu,
    plan_painterly_portrait,
    plan_painterly_racecar,
    plan_painterly_rubber_duck,
    plan_painterly_sunset,
    plan_refinement_fallback,
)
from photocraft_painter.strokes import (
    smooth_path,
    stroke_bezier,
    stroke_enclosed_loop,
    stroke_enclosed_oval,
    stroke_enclosed_rect,
    stroke_line,
    stroke_painterly_fill,
    stroke_polygon,
    stroke_regular_polygon_vertices,
    stroke_sketch_oval,
    stroke_sketchy_polygon_lines,
    stroke_triangle,
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
    expected_styles = ["realistic", "dreamlike", "abstract", "sketchy", "cartoon", "painterly", "cubism"]
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
    assert get_style("CUBISM").id == "cubism"
    assert get_style("  Cubism  ").id == "cubism"

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
    cubism = get_style("cubism")

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

    # Cubism shifts towards analytical ochre, sienna, and slate chiaroscuro
    adj_cubism = cubism.adjust_color(orig_color)
    assert adj_cubism.startswith("#")
    assert adj_cubism != orig_color

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

    # Cubism style densification produces sharp facet planes, edge fractures, and facet highlights
    plan_cubism = densify_artwork_plan(raw_plan, detail_level=10, style="cubism")
    assert plan_cubism["style"] == "cubism"
    cubist_facets = [
        s for s in plan_cubism["steps"]
        if s.get("cmd") == "paint.stroke" and "Cubist Facet Plane" in s["params"].get("name", "")
    ]
    assert len(cubist_facets) > 0
    for cf in cubist_facets:
        assert cf["params"]["hardness"] == 0.98
        assert cf["params"]["opacity"] == 0.95

    cubist_fractures = [
        s for s in plan_cubism["steps"]
        if s.get("cmd") == "paint.stroke" and "Cubist Edge Fracture" in s["params"].get("name", "")
    ]
    assert len(cubist_fractures) > 0
    for fr in cubist_fractures:
        assert fr["params"]["hardness"] == 0.98
        assert fr["params"]["color"] == "#181512"


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

    portrait_cubism = plan_fallback("portrait of a woman", style="cubism")
    assert "Cubism" in portrait_cubism["title"]
    assert portrait_cubism["style"] == "cubism"
    assert portrait_cubism["background"] == "#1c1917"


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


def test_plan_artwork_provider_routing():
    cfg = PainterConfig(provider="none", ollama_host="http://127.0.0.1:59999")
    plan, src = plan_artwork("rubber duck", cfg)
    assert "Built-in" in src
    assert "Rubber Duck" in plan["title"]


def test_parse_prompt_and_images_no_images():
    prompt, images = parse_prompt_and_images("a rubber duck in water")
    assert prompt == "a rubber duck in water"
    assert images == []


def test_parse_prompt_and_images_single_image():
    prompt, images = parse_prompt_and_images("file:/home/jp/apple.png make a green apple")
    assert prompt == "make a green apple"
    assert images == [Path("/home/jp/apple.png")]

    # Position at end of prompt
    prompt2, images2 = parse_prompt_and_images("make a green apple file:/home/jp/apple.png")
    assert prompt2 == "make a green apple"
    assert images2 == [Path("/home/jp/apple.png")]


def test_parse_prompt_and_images_quoted_paths():
    prompt1, images1 = parse_prompt_and_images('file:"/home/jp/My Images/apple photo.png" draw this in sketchy style')
    assert prompt1 == "draw this in sketchy style"
    assert images1 == [Path("/home/jp/My Images/apple photo.png")]

    prompt2, images2 = parse_prompt_and_images("file:'/home/jp/path with spaces/pic.jpg' paint this")
    assert prompt2 == "paint this"
    assert images2 == [Path("/home/jp/path with spaces/pic.jpg")]


def test_parse_prompt_and_images_multiple_images():
    prompt, images = parse_prompt_and_images("file:/tmp/a.png file:/tmp/b.jpg combine these into a landscape")
    assert prompt == "combine these into a landscape"
    assert images == [Path("/tmp/a.png"), Path("/tmp/b.jpg")]


def test_parse_prompt_and_images_tilde_expansion():
    prompt, images = parse_prompt_and_images("file:~/photo.png")
    assert prompt == ""
    assert images == [Path.home() / "photo.png"]


def test_parse_prompt_and_images_empty_text():
    prompt, images = parse_prompt_and_images("file:/tmp/apple.png")
    assert prompt == ""
    assert images == [Path("/tmp/apple.png")]


def test_validate_image_files(tmp_path):
    # Valid existing file
    valid_file = tmp_path / "test.png"
    valid_file.write_bytes(b"fake png data")
    validate_image_files([valid_file])  # Should not raise

    # Missing file
    missing_file = tmp_path / "does_not_exist.png"
    with pytest.raises(FileNotFoundError, match="Reference image not found"):
        validate_image_files([missing_file])

    # Directory instead of file
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    with pytest.raises(ValueError, match="Path is not a regular file"):
        validate_image_files([sub_dir])


def test_plan_artwork_with_image_forwarding(tmp_path):
    # Tests that plan_artwork extracts image from prompt, forwards it, and gracefully falls back to procedural composer
    img = tmp_path / "ref.png"
    img.write_bytes(b"dummy")

    cfg = PainterConfig(provider="none")
    raw_prompt = f"file:{img} a rubber duck"
    plan, src = plan_artwork(raw_prompt, cfg)

    assert "Rubber Duck" in plan["title"]
    assert "Built-in" in src


def test_compose_with_ollama_non_multimodal_error(tmp_path):
    img = tmp_path / "duck.png"
    img.write_bytes(b"dummy")

    cfg = PainterConfig(provider="ollama", ollama_model="text-only-model:7b")

    # Mock ollama.Client chat raising ResponseError indicating non-multimodal model
    mock_resp_error = Exception("status_code: 400 - Multimodal data provided, but model does not support multimodal requests.")

    with patch("ollama.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.chat.side_effect = mock_resp_error
        mock_client_cls.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            compose_with_ollama("draw this duck", cfg, 800, 800, images=[img])

        assert "does not support vision/image input" in str(exc_info.value)
        assert "llama3.2-vision:11b" in str(exc_info.value)


def test_normalize_paint_bucket_step():
    # Direct x, y and color
    step1 = {
        "cmd": "paint.bucket",
        "params": {
            "name": "Cheek Fill",
            "x": 275.4,
            "y": 465.8,
            "color": "#e74c3c",
            "tolerance": 45,
            "sampleAllLayers": True,
        },
    }
    norm1 = normalize_step(step1)
    assert norm1["cmd"] == "paint.bucket"
    assert norm1["params"]["name"] == "Cheek Fill"
    assert norm1["params"]["x"] == 275
    assert norm1["params"]["y"] == 466
    assert norm1["params"]["color"] == "#e74c3c"
    assert norm1["params"]["tolerance"] == 45
    assert norm1["params"]["sampleAllLayers"] is True

    # Seed point extraction from point/seed
    step2 = {
        "cmd": "bucket",
        "params": {
            "name": "Body Fill",
            "seed": [400, 420],
            "color": "fedb00",
        },
    }
    norm2 = normalize_step(step2)
    assert norm2["cmd"] == "paint.bucket"
    assert norm2["params"]["x"] == 400
    assert norm2["params"]["y"] == 420
    assert norm2["params"]["color"] == "#fedb00"
    assert norm2["params"]["sampleAllLayers"] is True


def test_expand_bounding_box_step():
    # A high-level bounding box step expands into an enclosed outline stroke and a paint bucket fill
    box_step = {
        "cmd": "paint.bounding_box",
        "params": {
            "name": "Badge Flat",
            "rect": [200, 300, 100, 80],
            "stroke": "#111111",
            "fill": "#fedb00",
            "stroke_size": 4.0,
        },
    }
    expanded = expand_step(box_step)
    assert len(expanded) == 2

    # Step 1: paint.stroke with completely closed bounding outline
    stroke_step = expanded[0]
    assert stroke_step["cmd"] == "paint.stroke"
    assert "Bounding Outline" in stroke_step["params"]["name"]
    pts = stroke_step["params"]["points"]
    assert len(pts) >= 4
    # End point meets start point without gaps
    assert math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.1 or len(pts) > 4
    assert stroke_step["params"]["hardness"] == 1.0

    # Step 2: paint.bucket with center coordinates (250, 340)
    bucket_step = expanded[1]
    assert bucket_step["cmd"] == "paint.bucket"
    assert bucket_step["params"]["x"] == 250
    assert bucket_step["params"]["y"] == 340
    assert bucket_step["params"]["color"] == "#fedb00"
    assert bucket_step["params"]["sampleAllLayers"] is True


def test_stroke_enclosed_shapes():
    # Enclosed rect
    rect_pts = stroke_enclosed_rect(100, 100, 200, 150)
    assert len(rect_pts) >= 40
    # Closed loop: points touch or overlap start
    assert rect_pts[0][0] == 100.0 and rect_pts[0][1] == 100.0
    for p in rect_pts:
        assert p[2] >= 0.8  # Solid pressure throughout to prevent pinholes

    # Enclosed oval
    oval_pts = stroke_enclosed_oval(400, 400, 100, 80)
    assert len(oval_pts) >= 50
    for p in oval_pts:
        assert p[2] >= 0.8


def test_smooth_path_closed_loop_watertight():
    # Coarse closed polygon: 4 corners of a box + return to start
    closed_box = [[100, 100], [200, 100], [200, 200], [100, 200], [100, 100]]
    smoothed = smooth_path(closed_box)
    assert len(smoothed) >= 20
    # The seam must not taper pressure to zero (which would cause a flood fill leak)
    assert smoothed[-1][2] >= 0.85
    assert smoothed[0][2] >= 0.85


def test_plan_painterly_pikachu():
    pikachu = plan_painterly_pikachu(800, 800, detail_level=5)
    assert "Painterly Pikachu" in pikachu["title"]
    assert pikachu["width"] == 800
    assert pikachu["height"] == 800

    # Must contain both enclosed bounding outlines and paint bucket fills
    bucket_steps = [s for s in pikachu["steps"] if s["cmd"] == "paint.bucket"]
    stroke_steps = [s for s in pikachu["steps"] if s["cmd"] == "paint.stroke"]
    layer_steps = [s for s in pikachu["steps"] if s["cmd"] == "layer.new.layer"]

    assert len(bucket_steps) >= 5  # Body, ears, ear tips, cheeks, eyes, mouth
    assert len(stroke_steps) >= 15
    assert len(layer_steps) >= 4

    # Verify Pikachu yellow body fill is present
    has_body_fill = any(
        s["params"].get("color") == "#fedb00" and "Body" in s["params"].get("name", "")
        for s in bucket_steps
    )
    assert has_body_fill

    # Verify red cheek fills are present
    cheek_fills = [
        s for s in bucket_steps
        if s["params"].get("color") == "#e74c3c" and "Cheek" in s["params"].get("name", "")
    ]
    assert len(cheek_fills) == 2

    # Verify fallback router routes "pikachu" to plan_painterly_pikachu
    routed_plan, routed_src = plan_artwork("pikachu", PainterConfig(provider="none"))
    assert "Pikachu" in routed_plan["title"]


def test_is_portrait_or_face_prompt_keywords():
    assert is_portrait_or_face_prompt("draw a man or woman") is True
    assert is_portrait_or_face_prompt("portrait of a warrior") is True
    assert is_portrait_or_face_prompt("bov") is True
    assert is_portrait_or_face_prompt("birth of venus") is True
    assert is_portrait_or_face_prompt("venus") is True
    assert is_portrait_or_face_prompt("young girl with ribbon") is True
    assert is_portrait_or_face_prompt("mona lisa study") is True
    assert is_portrait_or_face_prompt("classical gentleman") is True

    # Non-portraits
    assert is_portrait_or_face_prompt("a red sports car") is False
    assert is_portrait_or_face_prompt("rubber duck in bath") is False
    assert is_portrait_or_face_prompt("sunset over mountains") is False
    assert is_portrait_or_face_prompt("pikachu") is False


def test_is_portrait_or_face_prompt_with_images():
    assert is_portrait_or_face_prompt("", [Path("/home/jp/Pictures/bov.jpg")]) is True
    assert is_portrait_or_face_prompt("", [Path("/home/jp/Pictures/venus.png")]) is True
    assert is_portrait_or_face_prompt("", [Path("/home/jp/Pictures/portrait_study.webp")]) is True
    assert is_portrait_or_face_prompt("duck", [Path("/home/jp/Pictures/duck.png")]) is False


def test_plan_painterly_portrait_strict_z_order_depth():
    plan = plan_painterly_portrait("birth of venus", detail_level=5)
    layer_names = [s["params"]["name"] for s in plan["steps"] if s["cmd"] == "layer.new.layer"]

    # Verify key depth layers exist in strict Back-to-Front Z-order
    assert any("Background" in l or "Atmosphere" in l for l in layer_names)
    assert any("Rear" in l and "Hair" in l for l in layer_names)
    assert any("Shoulders" in l or "Torso" in l for l in layer_names)
    assert any("Head & Face Base" in l for l in layer_names)
    assert any("Facial Features" in l for l in layer_names)
    assert any("Foreground Framing Hair" in l for l in layer_names)
    assert any("Specular Highlights" in l for l in layer_names)

    # Verify index ordering of layers
    bg_idx = next(i for i, l in enumerate(layer_names) if "Background" in l or "Atmosphere" in l)
    rear_hair_idx = next(i for i, l in enumerate(layer_names) if "Rear" in l and "Hair" in l)
    torso_idx = next(i for i, l in enumerate(layer_names) if "Shoulders" in l or "Torso" in l)
    face_base_idx = next(i for i, l in enumerate(layer_names) if "Head & Face Base" in l)
    features_idx = next(i for i, l in enumerate(layer_names) if "Facial Features" in l)
    front_hair_idx = next(i for i, l in enumerate(layer_names) if "Foreground Framing Hair" in l)
    highlights_idx = next(i for i, l in enumerate(layer_names) if "Specular Highlights" in l)

    # Strict Z-order: Rear Hair must come BEFORE Face Base, and Face Base BEFORE Features
    assert bg_idx < rear_hair_idx
    assert rear_hair_idx < torso_idx
    assert torso_idx < face_base_idx
    assert face_base_idx < features_idx
    assert features_idx < front_hair_idx
    assert front_hair_idx < highlights_idx


def test_plan_painterly_portrait_facial_features_fidelity():
    plan = plan_painterly_portrait("venus", detail_level=5)
    stroke_names = [s["params"].get("name", "") for s in plan["steps"] if s["cmd"] == "paint.stroke"]
    bucket_steps = [s for s in plan["steps"] if s["cmd"] == "paint.bucket"]

    # Face base must have paint.bucket in skin tone
    assert any("Alabaster Skin Flat" in s["params"].get("name", "") for s in bucket_steps)

    # Eyes: Upper lashline, lower lid, iris, pupil, and white specular catchlight
    assert any("Left Eye Upper Lid" in name for name in stroke_names)
    assert any("Left Eye Lower Lid" in name for name in stroke_names)
    assert any("Left Eye Iris" in name for name in stroke_names)
    assert any("Left Eye Pupil" in name for name in stroke_names)
    assert any("Left Eye Specular Catchlight" in name for name in stroke_names)

    # Eyebrows
    assert any("Eyebrow Arch" in name for name in stroke_names)

    # Nose: Bridge, tip bulb, nostrils
    assert any("Nose Bridge" in name for name in stroke_names)
    assert any("Nose Tip" in name for name in stroke_names)
    assert any("Nostril" in name for name in stroke_names)

    # Lips: Cupid's bow, mouth parting line, lower lip, gloss highlight
    assert any("Cupid's Bow" in name for name in stroke_names)
    assert any("Mouth Parting Line" in name for name in stroke_names)
    assert any("Lower Lip Curve" in name for name in stroke_names)
    assert any("Lower Lip Gloss" in name for name in stroke_names)


def test_plan_painterly_portrait_unobstructed_face():
    plan = plan_painterly_portrait("venus", detail_level=5)
    steps = plan["steps"]

    # Identify steps in Foreground Framing Hair layer
    in_framing = False
    framing_strokes = []
    for s in steps:
        if s.get("cmd") == "layer.new.layer":
            name = s["params"]["name"]
            if "Foreground Framing Hair" in name:
                in_framing = True
            elif in_framing:
                break
        elif in_framing and s.get("cmd") == "paint.stroke":
            framing_strokes.append(s)

    # Facial feature box: x in [400, 495], y in [290, 415]
    # No framing hair stroke should cross horizontally through the eyes, nose, and mouth
    for s in framing_strokes:
        pts = s["params"]["points"]
        pts_in_face = [
            pt for pt in pts
            if 410 <= pt[0] <= 485 and 300 <= pt[1] <= 410
        ]
        assert len(pts_in_face) == 0, f"Framing stroke '{s['params']['name']}' crossed into facial feature zone: {pts_in_face}"


def test_plan_painterly_portrait_detail_scaling():
    p1 = plan_painterly_portrait("portrait", detail_level=1)
    p5 = plan_painterly_portrait("portrait", detail_level=5)
    p25 = plan_painterly_portrait("portrait", detail_level=25)

    s1 = [s for s in p1["steps"] if s["cmd"] == "paint.stroke"]
    s5 = [s for s in p5["steps"] if s["cmd"] == "paint.stroke"]
    s25 = [s for s in p25["steps"] if s["cmd"] == "paint.stroke"]

    assert len(s1) >= 15
    assert len(s5) >= 30
    assert len(s25) > len(s5) + 30


def test_plan_fallback_routes_portraits():
    config = PainterConfig(provider="none")

    # Venus / BOV
    p_bov, _ = plan_artwork("bov", config)
    assert "Venus" in p_bov["title"] or "Portrait" in p_bov["title"]

    # Man or woman
    p_mow, _ = plan_artwork("draw a man or woman", config)
    assert "Portrait" in p_mow["title"]

    # Image reference to bov.jpg
    p_img, _ = plan_artwork("file:/home/jp/Pictures/bov.jpg", config)
    assert "Venus" in p_img["title"] or "Portrait" in p_img["title"]


def test_densify_artwork_plan_protects_facial_features():
    plan = {
        "title": "Portrait Test",
        "steps": [
            {
                "cmd": "paint.stroke",
                "params": {"name": "Facial Feature: Left Eye Pupil", "points": [[420, 315], [421, 315]], "size": 3.0, "color": "#000000"},
            },
            {
                "cmd": "paint.stroke",
                "params": {"name": "Facial Feature: Upper Lip Cupid's Bow", "points": [[433, 396], [454, 398]], "size": 2.5, "color": "#b85955"},
            },
            {
                "cmd": "paint.stroke",
                "params": {"name": "Background Atmosphere Wash", "points": [[100, 100], [700, 100]], "size": 40.0, "color": "#96b5c6"},
            },
        ],
    }
    densified = densify_artwork_plan(plan, detail_level=10)
    for s in densified["steps"]:
        if s.get("cmd") == "paint.stroke":
            name = s["params"].get("name", "")
            # Broad washes should never be generated for pupil or cupid's bow
            if "Wash" in name:
                assert "Pupil" not in name
                assert "Cupid's Bow" not in name


def test_sanitize_hair_strokes_against_face():
    # Face feature box centered around (450, 350)
    face_box = (400.0, 300.0, 500.0, 400.0)

    # A bad stroke that crosses horizontally straight through the face: x=300 to x=600 at y=350
    bad_hair_stroke = {
        "cmd": "paint.stroke",
        "params": {
            "name": "Hair Texture Across Face",
            "points": [[320, 350], [360, 350], [420, 350], [480, 350], [540, 350], [580, 350]],
            "size": 8.0,
            "color": "#d4a34b",
        },
    }

    sanitized = sanitize_hair_strokes_against_face([bad_hair_stroke], face_box, allow_face_obstruction=False)
    # The bad stroke must be split into Left Lock and Right Lock, leaving the center clear
    assert len(sanitized) == 2
    assert "Left Lock" in sanitized[0]["params"]["name"]
    assert "Right Lock" in sanitized[1]["params"]["name"]

    for pt in sanitized[0]["params"]["points"]:
        assert pt[0] < face_box[0]
    for pt in sanitized[1]["params"]["points"]:
        assert pt[0] > face_box[2]

    # If explicit deviation is allowed (e.g. hair over face), it is preserved intact
    sanitized_deviated = sanitize_hair_strokes_against_face([bad_hair_stroke], face_box, allow_face_obstruction=True)
    assert len(sanitized_deviated) == 1
    assert sanitized_deviated[0]["params"]["name"] == "Hair Texture Across Face"


def test_format_document_title_user_example():
    # User's exact requested example
    result = format_document_title(
        base_title="Woman on Staircase",
        style="painterly",
        detail_level=5,
        model="kimi-k3-cloud",
    )
    assert result == "Woman on Staircase [Painterly][Detail 5][kimi-k3-cloud]"
    assert "/" not in result
    assert "\\" not in result
    assert ":" not in result


def test_format_document_title_model_sanitization():
    # Model names with colons or slashes must use dashes instead
    res_colon = format_document_title("A Fast Racecar", model="ornith-1.5:35b")
    assert "[ornith-1.5-35b]" in res_colon
    assert ":" not in res_colon

    res_slash = format_document_title("Landscape", model="meta-llama/Llama-3.2-Vision:11B")
    assert "[meta-llama-Llama-3.2-Vision-11B]" in res_slash
    assert "/" not in res_slash
    assert ":" not in res_slash


def test_format_document_title_strictly_no_slashes_and_length_limit():
    # Short title must be no more than 25 characters
    long_prompt = "A Magnificent Oil Painting Of An Astronaut Exploring A Distant Neon Galaxy"
    result = format_document_title(long_prompt, style="dreamlike", detail_level=25, model="test-model")

    # Extract short title before the first bracket
    short_title = result.split("[")[0].strip()
    assert len(short_title) <= 25
    assert short_title == "A Magnificent Oil Paintin"
    assert "[Dreamlike]" in result
    assert "[Detail 25]" in result
    assert "[test-model]" in result
    assert "/" not in result

    # Slashes in prompt must be removed/cleaned
    slash_prompt = "Before/After/Split"
    slash_res = format_document_title(slash_prompt, detail_level=12)
    assert "/" not in slash_res
    assert "[Detail 12]" in slash_res


def test_format_document_title_idempotence_and_metadata_preservation():
    # Re-formatting an already formatted title preserves existing metadata
    formatted = "Woman on Staircase [Painterly][Detail 5][kimi-k3-cloud]"
    assert format_document_title(formatted) == formatted

    # Overriding a specific attribute while preserving the rest
    updated_detail = format_document_title(formatted, detail_level=20)
    assert updated_detail == "Woman on Staircase [Painterly][Detail 20][kimi-k3-cloud]"

    # Legacy (Detail 5/25) with slash is sanitized to [Detail 5]
    legacy = "Painterly Rubber Duck [Painterly] (Detail 5/25)"
    cleaned_legacy = format_document_title(legacy, model="built-in")
    assert cleaned_legacy == "Painterly Rubber Duck [Painterly][Detail 5][built-in]"
    assert "/" not in cleaned_legacy


def test_procedural_plans_document_titles_have_no_slashes():
    # All procedural plans must generate titles without slashes, <= 25 char base, and bracketed metadata
    plans = [
        plan_painterly_rubber_duck(detail_level=5, style="painterly"),
        plan_painterly_sunset(detail_level=15, style="dreamlike"),
        plan_painterly_racecar(detail_level=25, style="realistic"),
        plan_painterly_pikachu(detail_level=8, style="cartoon"),
        plan_dynamic_artwork("cyberpunk cityscape in rain", detail_level=10, style="abstract"),
        plan_painterly_portrait("mona lisa portrait study", detail_level=18, style="painterly"),
    ]

    for p in plans:
        title = p["title"]
        assert "/" not in title, f"Title '{title}' contains illegal slash"
        assert "\\" not in title
        assert ":" not in title
        # Check base title <= 25 chars
        base_title = title.split("[")[0].strip()
        assert len(base_title) <= 25, f"Base title '{base_title}' exceeds 25 chars"
        assert "[" in title and "]" in title
        assert "[Detail " in title


@pytest.mark.anyio
async def test_execute_live_drawing_sanitizes_title(monkeypatch):
    from photocraft_painter.artist import execute_live_drawing

    captured_name = None

    class MockClient:
        async def doc_new(self, width, height, background, name, **kwargs):
            nonlocal captured_name
            captured_name = name
            return {"document_id": "doc_1"}

        async def new_layer(self, name):
            pass

        async def command_run(self, cmd_id, params=None, wait=True):
            return {"status": "ok"}

    mock_client = MockClient()
    plan_with_slashes = {
        "title": "A Long Elaborate Painting Title Exceeding Twenty Five Characters / Subtitle (Detail 5/25)",
        "style": "painterly",
        "detail_level": 5,
        "model": "ornith-1.5:35b",
        "width": 800,
        "height": 800,
        "steps": [],
    }

    config = PainterConfig(step_delay=0)
    await execute_live_drawing(mock_client, plan_with_slashes, config)

    assert captured_name is not None
    assert "/" not in captured_name
    assert ":" not in captured_name
    assert "[Detail 5]" in captured_name
    assert "[ornith-1.5-35b]" in captured_name
    assert "[Painterly]" in captured_name
    base_name = captured_name.split("[")[0].strip()
    assert len(base_name) <= 25


def test_stroke_polygon_is_linear_and_sharp():
    # 3-sided triangle with vertices: (400, 100), (600, 600), (200, 600)
    verts = [[400.0, 100.0], [600.0, 600.0], [200.0, 600.0]]
    pts = stroke_polygon(verts, wobble=0.0, steps_per_side=15, closed=True)

    assert len(pts) >= 45
    # Bottom edge: between (600, 600) and (200, 600), every point must have y == 600.0 (no sagging/gum drop curve!)
    idx_v1 = next(i for i, p in enumerate(pts) if p[0] == 600.0 and p[1] == 600.0)
    idx_v2 = next(i for i, p in enumerate(pts) if p[0] == 200.0 and p[1] == 600.0)
    bottom_pts = pts[idx_v1:idx_v2 + 1]
    assert len(bottom_pts) >= 15
    for bp in bottom_pts:
        assert bp[1] == 600.0

    # Apex vertex at (400, 100) is reached exactly
    apex_pts = [p for p in pts if p[0] == 400.0 and p[1] == 100.0]
    assert len(apex_pts) >= 1

    # End overlaps start point for watertight fill
    assert pts[0][:2] == [400.0, 100.0]
    assert pts[-1][:2] == pts[2][:2] or pts[-1][:2] == pts[0][:2]


def test_normalize_step_preserves_sharp_polygon_no_gum_drops():
    # A coarse triangle passed with points
    triangle_step = {
        "cmd": "paint.stroke",
        "params": {
            "name": "Triangle Outline",
            "points": [[400.0, 100.0], [600.0, 600.0], [200.0, 600.0], [400.0, 100.0]],
            "size": 5.0,
            "color": "#111111",
        },
    }
    normalized = normalize_step(triangle_step)
    assert normalized["cmd"] == "paint.stroke"
    norm_pts = normalized["params"]["points"]
    assert len(norm_pts) > 10

    # Bottom edge must remain flat (y == 600.0), NOT bowed or curved into a gum drop
    idx_v1 = next(i for i, p in enumerate(norm_pts) if p[0] == 600.0 and p[1] == 600.0)
    idx_v2 = next(i for i, p in enumerate(norm_pts) if p[0] == 200.0 and p[1] == 600.0)
    bottom_pts = norm_pts[idx_v1:idx_v2 + 1]
    assert len(bottom_pts) >= 15
    for p in bottom_pts:
        assert p[1] == 600.0


def test_expand_step_geometric_triangle():
    # Expand composite paint.triangle command
    tri_step = {
        "cmd": "paint.triangle",
        "params": {
            "name": "Emerald Triangle",
            "fill": "#2ecc71",
            "stroke": "#111111",
            "cx": 400,
            "cy": 400,
            "radius": 180,
        },
    }
    expanded = expand_step(tri_step)
    assert len(expanded) == 2

    # Step 1: paint.stroke with enclosed outline
    stroke_step = expanded[0]
    assert stroke_step["cmd"] == "paint.stroke"
    assert "Enclosed Outline" in stroke_step["params"]["name"]
    assert stroke_step["params"]["polygon"] is True
    assert len(stroke_step["params"]["points"]) >= 40

    # Step 2: paint.bucket at centroid
    bucket_step = expanded[1]
    assert bucket_step["cmd"] == "paint.bucket"
    assert bucket_step["params"]["color"] == "#2ecc71"
    assert bucket_step["params"]["x"] == 400
    assert bucket_step["params"]["y"] == 400
    assert bucket_step["params"]["sampleAllLayers"] is True


def test_parse_geometric_shape_prompt():
    assert parse_geometric_shape_prompt("make a triangle") == (True, 3, "Triangle", None)
    assert parse_geometric_shape_prompt("draw a 3 sided polygon") == (True, 3, "Triangle", None)
    assert parse_geometric_shape_prompt("a green triangle in sketchy style") == (True, 3, "Triangle", "#2ecc71")
    assert parse_geometric_shape_prompt("a red 3-sided polygon") == (True, 3, "Triangle", "#e74c3c")
    assert parse_geometric_shape_prompt("a golden square") == (True, 4, "Square", "#f39c12")
    assert parse_geometric_shape_prompt("blue hexagon") == (True, 6, "Hexagon", "#3498db")
    assert parse_geometric_shape_prompt("draw a polygon") == (True, 3, "Polygon", None)
    assert parse_geometric_shape_prompt("mountain sunset")[0] is False


def test_plan_fallback_routes_triangles_all_styles():
    # 1. Sketchy style
    sketchy_plan = plan_fallback("make a triangle", style="sketchy")
    assert "Triangle" in sketchy_plan["title"]
    assert "[Sketchy]" in sketchy_plan["title"]
    assert sketchy_plan["background"] == "#fdfefe"
    # Must have drafting guide lines with corner overshoots
    has_drafting_lines = any(
        "Drafting Guide Line" in s.get("params", {}).get("name", "")
        for s in sketchy_plan["steps"]
    )
    assert has_drafting_lines
    # Must have facet cross-hatching
    has_hatching = any(
        "Facet Cross-Hatch" in s.get("params", {}).get("name", "")
        for s in sketchy_plan["steps"]
    )
    assert has_hatching
    # Must have paint bucket fill
    has_fill = any(s["cmd"] == "paint.bucket" for s in sketchy_plan["steps"])
    assert has_fill

    # 2. Cartoon style
    cartoon_plan = plan_fallback("draw a red triangle", style="cartoon")
    assert "Triangle" in cartoon_plan["title"]
    assert "[Cartoon]" in cartoon_plan["title"]
    # Black ink contour outline with hardness 1.0
    ink_steps = [
        s for s in cartoon_plan["steps"]
        if "Master Ink Outline" in s.get("params", {}).get("name", "")
    ]
    assert len(ink_steps) == 1
    assert ink_steps[0]["params"]["color"] == "#000000"
    assert ink_steps[0]["params"]["hardness"] == 1.0
    # Must contain red fill (#e74c3c)
    red_fills = [
        s for s in cartoon_plan["steps"]
        if s["cmd"] == "paint.bucket" and s.get("params", {}).get("color") == "#e74c3c"
    ]
    assert len(red_fills) >= 1
    # Cel shadow facet
    has_cel_shadow = any(
        "Cel Shadow" in s.get("params", {}).get("name", "")
        for s in cartoon_plan["steps"]
    )
    assert has_cel_shadow

    # 3. Realistic style
    realistic_plan = plan_fallback("a green triangle", style="realistic")
    assert "Triangle" in realistic_plan["title"]
    assert "[Realistic]" in realistic_plan["title"]
    has_green = any(
        s.get("params", {}).get("color") == "#2ecc71"
        for s in realistic_plan["steps"]
    )
    assert has_green

    # 4. 3-sided polygon routing
    poly_plan = plan_fallback("draw a 3-sided polygon", style="abstract")
    assert "Triangle" in poly_plan["title"] or "Polygon" in poly_plan["title"]
    assert "[Abstract]" in poly_plan["title"]


def test_cubism_portrait_plan_multi_perspective_and_3d_relief():
    portrait = plan_fallback("portrait of a woman", style="cubism", detail_level=5)
    assert "[Cubism]" in portrait["title"]
    assert "[Detail 5]" in portrait["title"]
    assert portrait["style"] == "cubism"
    assert portrait["background"] == "#1c1917"

    step_names = [s.get("params", {}).get("name", "") for s in portrait["steps"]]

    # 1. Multi-Perspective Analytical Axes
    assert any("Central Bisecting Facial Ridge" in n for n in step_names)
    assert any("Profile Viewpoint Eye-Axis" in n for n in step_names)
    assert any("Frontal Viewpoint Eye-Axis" in n for n in step_names)

    # 2. Deconstructed Head Facets (Profile + Frontal)
    assert any("Profile Nose & Brow Projection" in n for n in step_names)
    assert any("Frontal Right Cheek & Zygomatic Plane" in n for n in step_names)
    assert any("Central Chiaroscuro Shadow Ridge" in n for n in step_names)

    # 3. Multi-Perspective Features
    assert any("Profile Eye Contour" in n for n in step_names)
    assert any("Frontal Eye Contour" in n for n in step_names)
    assert any("Upper Lip Profile Facet" in n for n in step_names)
    assert any("Upper Lip Frontal Facet" in n for n in step_names)

    # 4. 3D Facet High-Relief Highlights (Leaping off canvas)
    assert any("Profile Nose Tip Vertex" in n for n in step_names)
    assert any("Nose Bridge Leading Edge" in n for n in step_names)
    assert any("Frontal Cheek Crest Apex" in n for n in step_names)

    # 5. Watertight polygon boundaries with paint bucket fills
    bucket_fills = [s for s in portrait["steps"] if s.get("cmd") == "paint.bucket"]
    assert len(bucket_fills) >= 15
    for bf in bucket_fills:
        assert bf["params"]["sampleAllLayers"] is True
        assert bf["params"]["color"].startswith("#")

    # 6. Straight linear polygon vertices (no Catmull-Rom gum drops)
    polygon_strokes = [
        s for s in portrait["steps"]
        if s.get("cmd") == "paint.stroke" and s.get("params", {}).get("polygon") is True
    ]
    assert len(polygon_strokes) >= 15
    for ps in polygon_strokes:
        assert ps["params"]["hardness"] >= 0.95


def test_cubism_geometric_shape_multi_perspective():
    geom = plan_fallback("draw a triangle", style="cubism", detail_level=5)
    assert "[Cubism]" in geom["title"]
    assert geom["style"] == "cubism"
    assert geom["background"] == "#1c1917"

    step_names = [s.get("params", {}).get("name", "") for s in geom["steps"]]

    # Analytical fracture rays
    assert any("Analytical Fracture Ray" in n for n in step_names)

    # Multi-perspective 3D polyhedral facet planes
    assert any("Cubist Shadow Facet Plane Boundary" in n for n in step_names)
    assert any("Cubist Shadow Facet Fill" in n for n in step_names)
    assert any("Cubist Intersecting Planar Facet Ridge" in n for n in step_names)
    assert any("Cubist Key-Lit Facet Fill" in n for n in step_names)

    # Paint bucket fills for the facets
    buckets = [s for s in geom["steps"] if s.get("cmd") == "paint.bucket"]
    assert len(buckets) >= 3  # Base fill, shadow facet fill, key-lit facet fill


def test_cubism_dynamic_artwork():
    artwork = plan_fallback("a cubist guitar", style="cubism", detail_level=5)
    assert "[Cubism]" in artwork["title"]
    assert artwork["style"] == "cubism"
    assert artwork["background"] == "#1c1917"

    step_names = [s.get("params", {}).get("name", "") for s in artwork["steps"]]

    # Analytical perspective grid
    assert any("Analytical Axis: Diagonal Perspective Grid" in n for n in step_names)
    assert any("Analytical Axis: Counter-Diagonal Perspective Grid" in n for n in step_names)

    # Multi-perspective facets
    assert any("Facet: Frontal Key-Lit Plane" in n for n in step_names)
    assert any("Facet: Isometric Top Perspective" in n for n in step_names)
    assert any("Facet: Profile Angled Projection" in n for n in step_names)
    assert any("Facet: Deep Volumetric Shadow Plane" in n for n in step_names)

    # 3D relief highlights
    assert any("Relief Highlight: Frontal Planar Apex" in n for n in step_names)
    assert any("Relief Highlight: Profile Projection Leading Edge" in n for n in step_names)


def test_config_loop_setting_and_clamping():
    cfg = PainterConfig()
    assert cfg.loop == 1
    assert cfg.loop_count == 1

    cfg.loop = 3
    assert cfg.loop == 3
    assert cfg.loop_count == 3

    # Clamping range [1, 5]
    cfg.loop_count = 0
    assert cfg.loop == 1

    cfg.loop_count = 10
    assert cfg.loop == 5

    cfg.loop = -5
    assert cfg.loop == 1

    cfg.loop = 99
    assert cfg.loop == 5


def test_plan_refinement_fallback_all_styles():
    for style in ["realistic", "cubism", "cartoon", "sketchy", "dreamlike", "abstract"]:
        refine = plan_refinement_fallback("a majestic portrait", width=800, height=800, detail_level=5, style=style, loop_iteration=1)
        assert refine["is_refinement"] is True
        assert refine["style"] == style
        assert "critique" in refine and len(refine["critique"]) > 0
        assert len(refine["steps"]) > 0
        # No background wash step or doc creation in refinement steps
        assert not any(s.get("cmd") == "doc.new" for s in refine["steps"])
        assert any("Refinement" in s.get("params", {}).get("name", "") for s in refine["steps"])


def test_plan_refinement_artwork_routing():
    cfg_none = PainterConfig(provider="none", loop=2)
    dummy_img = Path("/tmp/dummy_refinement_canvas.png")
    plan, src = plan_refinement_artwork("a noble knight", cfg_none, current_image=dummy_img, loop_iteration=1)
    assert plan["is_refinement"] is True
    assert "Built-in Refiner" in src
    assert "critique" in plan and len(plan["critique"]) > 0


@pytest.mark.anyio
async def test_capture_png_and_execute_live_drawing_refinement(tmp_path):
    from photocraft_painter.artist import execute_live_drawing
    from photocraft_painter.mcp_client import PhotocraftMcpClient

    client = PhotocraftMcpClient(MagicMock())
    client.call_tool = MagicMock()
    async def mock_call(name, args=None):
        if name == "doc_render_preview":
            return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        return {"status": "ok"}
    client.call_tool.side_effect = mock_call

    out_file = tmp_path / "canvas_snapshot.png"
    captured = await client.capture_png(out_file)
    assert captured.exists()
    assert captured.stat().st_size > 0

    cfg = PainterConfig(step_delay=0.0)
    refine_plan = plan_refinement_fallback("portrait", loop_iteration=1)

    await execute_live_drawing(client, refine_plan, cfg, create_canvas=False)
    tool_calls = [c.args[0] for c in client.call_tool.call_args_list]
    assert "doc_new" not in tool_calls


@pytest.mark.anyio
async def test_multi_loop_simulation(tmp_path):
    from photocraft_painter.artist import execute_live_drawing
    from photocraft_painter.mcp_client import PhotocraftMcpClient

    client = PhotocraftMcpClient(MagicMock())
    calls = []
    async def mock_call(name, args=None):
        calls.append(name)
        if name == "doc_render_preview":
            return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        return {"status": "ok"}
    client.call_tool = MagicMock(side_effect=mock_call)

    cfg = PainterConfig(provider="none", loop=3, step_delay=0.0)
    prompt = "a majestic cat"

    # 1. Initial Pass
    initial_plan, _ = plan_artwork(prompt, cfg)
    await execute_live_drawing(client, initial_plan, cfg, create_canvas=True)
    assert "doc_new" in calls
    doc_new_count = calls.count("doc_new")
    assert doc_new_count == 1

    # 2. Refinement loop iterations = loop - 1 = 2
    loop_passes = cfg.loop - 1
    assert loop_passes == 2

    for i in range(1, loop_passes + 1):
        snapshot = await client.capture_png(tmp_path / f"snap_{i}.png")
        assert snapshot.exists()
        refine_plan, _ = plan_refinement_artwork(prompt, cfg, current_image=snapshot, loop_iteration=i)
        assert refine_plan["is_refinement"] is True
        assert len(refine_plan["critique"]) > 0
        await execute_live_drawing(client, refine_plan, cfg, create_canvas=False)

    # doc_new must NEVER be called again during refinement passes
    assert calls.count("doc_new") == 1


def test_refinement_instructions_emphasize_logical_errors_and_intersections():
    # Verify REFINEMENT_SYSTEM_PROMPT directs model to find logical errors, background intersections, and style violations
    prompt_upper = REFINEMENT_SYSTEM_PROMPT.upper()
    assert "LOGICAL ERRORS" in prompt_upper
    assert "INTERSECT" in prompt_upper
    assert "WATER" in prompt_upper
    assert "DUCK" in prompt_upper
    assert "OPAQUE" in prompt_upper
    assert "STYLE VIOLATIONS" in prompt_upper
    assert "COVER" in prompt_upper or "REPAIR" in prompt_upper


def test_plan_refinement_fallback_duck_resolves_water_intersection():
    plan = plan_refinement_fallback("a rubber duck splashing in water", style="cartoon", loop_iteration=1)
    assert plan["is_refinement"] is True
    assert "layering error" in plan["critique"].lower() or "intersect" in plan["critique"].lower()

    step_names = [s.get("params", {}).get("name", "") for s in plan["steps"]]
    # Must have base occlusion repair layer and stroke covering intersecting water
    assert any("Base Occlusion" in n or "Cover Intersecting Water" in n for n in step_names)
    assert any("Waterline Base Contact Foam" in n for n in step_names)

    # Check that opaque yellow base stroke is present with opacity 1.0
    cover_strokes = [
        s for s in plan["steps"]
        if s.get("cmd") == "paint.stroke" and "Cover Intersecting Water" in s.get("params", {}).get("name", "")
    ]
    assert len(cover_strokes) > 0
    assert cover_strokes[0]["params"]["opacity"] == 1.0
    assert cover_strokes[0]["params"]["size"] >= 20.0


def test_refinement_progressive_phase_guidance():
    from photocraft_painter.composer import get_refinement_phase_guidance

    # Pass 1 of 4: Phase 1 (Occlusion & Base Flats)
    g1 = get_refinement_phase_guidance(1, 4, "cartoon")
    assert "PASS 1" in g1
    assert "SHADOW SPOTS" in g1.upper() and ("DO NOT" in g1.upper() or "NO" in g1.upper())
    assert "BASE" in g1.upper()

    # Pass 2 of 4: Phase 2 (Form Modeling & Continuous Shadow)
    g2 = get_refinement_phase_guidance(2, 4, "cartoon")
    assert "PASS 2" in g2
    assert "CONTINUOUS" in g2.upper()

    # Pass 3 of 4: Phase 3 (Facial Features & Splashes)
    g3 = get_refinement_phase_guidance(3, 4, "cartoon")
    assert "PASS 3" in g3
    assert "FACIAL" in g3.upper() or "FOCAL" in g3.upper()

    # Pass 4 of 4: Phase 4 (Master Inking & Specular Highlights)
    g4 = get_refinement_phase_guidance(4, 4, "cartoon")
    assert "PASS 4" in g4
    assert "INK" in g4.upper() or "SPECULAR" in g4.upper()


def test_refinement_strict_ban_on_shadow_spots_in_prompt():
    prompt_upper = REFINEMENT_SYSTEM_PROMPT.upper()
    assert 'STRICT BAN ON "SHADOW SPOTS"' in prompt_upper or "STRICT BAN ON 'SHADOW SPOTS'" in prompt_upper
    assert "DASH CLUSTERS" in prompt_upper
    assert "MEASLES" in prompt_upper or "SCATTER" in prompt_upper
    assert "CONTINUOUS" in prompt_upper


def test_plan_refinement_fallback_progressive_phases_and_no_dash_clusters():
    # Pass 1: Occlusion & base flats
    p1 = plan_refinement_fallback("a rubber duck in water", style="cartoon", loop_iteration=1, total_iterations=4)
    step_names_1 = [s.get("params", {}).get("name", "") for s in p1["steps"]]
    assert any("Base Occlusion" in n for n in step_names_1)
    # Must NOT have any shadow spots or dash clusters
    assert not any("Shadow Spot" in n or "Dash" in n for n in step_names_1)

    # Pass 2: Volumetric continuous shadow (NO dash clusters)
    p2 = plan_refinement_fallback("a rubber duck in water", style="cartoon", loop_iteration=2, total_iterations=4)
    step_names_2 = [s.get("params", {}).get("name", "") for s in p2["steps"]]
    assert any("Continuous Form Shadow" in n for n in step_names_2)
    assert not any("Shadow Spot" in n or "Dash" in n for n in step_names_2)

    # Pass 3: Facial features & splashes
    p3 = plan_refinement_fallback("a rubber duck in water", style="cartoon", loop_iteration=3, total_iterations=4)
    step_names_3 = [s.get("params", {}).get("name", "") for s in p3["steps"]]
    assert any("Eye" in n or "Beak" in n or "Splash" in n for n in step_names_3)

    # Pass 4: Inking & highlights
    p4 = plan_refinement_fallback("a rubber duck in water", style="cartoon", loop_iteration=4, total_iterations=4)
    step_names_4 = [s.get("params", {}).get("name", "") for s in p4["steps"]]
    assert any("Ink" in n or "Highlight" in n for n in step_names_4)


@pytest.mark.anyio
async def test_execute_live_drawing_isolates_background_layers_and_restores_all():
    from photocraft_painter.artist import execute_live_drawing

    commands_log: list[tuple[str, dict[str, Any]]] = []
    layer_visibility: dict[int, bool] = {1: True}
    next_layer_id = 2

    class LayerMockClient:
        async def doc_new(self, width, height, background, name, **kwargs):
            commands_log.append(("doc_new", {"name": name}))
            return {"document_id": "doc_1"}

        async def doc_inspect(self):
            return {
                "layers": [{"id": lid, "visible": layer_visibility[lid]} for lid in layer_visibility]
            }

        async def command_run(self, cmd_id, params=None, wait=True):
            nonlocal next_layer_id
            params = params or {}
            commands_log.append((cmd_id, params))

            if cmd_id == "layer.new.layer":
                lid = next_layer_id
                next_layer_id += 1
                layer_visibility[lid] = True
                return {"layer": lid}
            elif cmd_id == "layer.setProps":
                lid = params.get("layer")
                if lid is not None and "visible" in params:
                    layer_visibility[lid] = params["visible"]
                return {"status": "ok"}
            return {"status": "ok"}

        async def new_layer(self, name):
            return await self.command_run("layer.new.layer", {"name": name})

    client = LayerMockClient()
    plan = {
        "title": "Jigglypuff Cel",
        "style": "cartoon",
        "detail_level": 5,
        "model": "kimi-k3-cloud",
        "width": 800,
        "height": 800,
        "steps": [
            # Layer 2: Background Starburst Shapes
            {"cmd": "layer.new.layer", "params": {"name": "1. Background Starburst"}},
            {"cmd": "paint.stroke", "params": {"name": "Starburst Ray 1", "points": [[400, 400], [800, 200]]}},
            # Layer 3: Character Body (Enclosed contour + Paint Bucket)
            {"cmd": "layer.new.layer", "params": {"name": "2. Jigglypuff Body"}},
            {"cmd": "paint.stroke", "params": {"name": "Body Contour", "points": [[300, 300], [500, 300], [500, 500], [300, 500], [300, 300]]}},
            {"cmd": "paint.bucket", "params": {"name": "Body Pink Fill", "x": 400, "y": 400, "color": "#ffc0cb", "sampleAllLayers": True}},
            # Layer 4: Face Details
            {"cmd": "layer.new.layer", "params": {"name": "3. Face Details"}},
            {"cmd": "paint.stroke", "params": {"name": "Eye Outline", "points": [[350, 380], [370, 380]]}},
        ],
    }

    config = PainterConfig(step_delay=0)
    summary = await execute_live_drawing(client, plan, config, create_canvas=True)
    assert summary["steps_drawn"] == len(plan["steps"])

    # 1. Verify that while Layer 2 was being drawn, Layer 1 was set invisible:
    # 2. Verify that while Layer 3 was being drawn, Layers 1 and 2 were set invisible:
    hide_calls = [
        p for (cmd, p) in commands_log
        if cmd == "layer.setProps" and p.get("visible") is False
    ]
    # Layer 1 must have been hidden
    assert any(p.get("layer") == 1 for p in hide_calls)
    # Layer 2 must have been hidden when Layer 3 started
    assert any(p.get("layer") == 2 for p in hide_calls)

    # 3. Verify that in the end, ALL layers (1, 2, 3, 4) are restored to visible=True
    assert layer_visibility[1] is True
    assert layer_visibility[2] is True
    assert layer_visibility[3] is True
    assert layer_visibility[4] is True

    # Check that layer.setProps with visible=True was called for all layers
    restore_calls = [
        p for (cmd, p) in commands_log
        if cmd == "layer.setProps" and p.get("visible") is True
    ]
    restored_layers = {p.get("layer") for p in restore_calls}
    assert {1, 2, 3, 4}.issubset(restored_layers)


@pytest.mark.anyio
async def test_execute_live_drawing_restores_layers_on_error():
    from photocraft_painter.artist import execute_live_drawing

    layer_visibility: dict[int, bool] = {1: True}
    next_layer_id = 2

    class FailingClient:
        async def doc_new(self, width, height, background, name, **kwargs):
            return {"document_id": "doc_1"}

        async def doc_inspect(self):
            return {
                "layers": [{"id": lid, "visible": layer_visibility[lid]} for lid in layer_visibility]
            }

        async def command_run(self, cmd_id, params=None, wait=True):
            nonlocal next_layer_id
            params = params or {}
            if cmd_id == "layer.new.layer":
                lid = next_layer_id
                next_layer_id += 1
                layer_visibility[lid] = True
                return {"layer": lid}
            elif cmd_id == "layer.setProps":
                lid = params.get("layer")
                if lid is not None and "visible" in params:
                    layer_visibility[lid] = params["visible"]
                return {"status": "ok"}
            elif cmd_id == "paint.bucket":
                raise RuntimeError("Simulated mid-drawing error")
            return {"status": "ok"}

        async def new_layer(self, name):
            return await self.command_run("layer.new.layer", {"name": name})

    client = FailingClient()
    plan = {
        "title": "Error Recovery",
        "style": "cartoon",
        "detail_level": 3,
        "model": "kimi-k3-cloud",
        "width": 800,
        "height": 800,
        "steps": [
            {"cmd": "layer.new.layer", "params": {"name": "Layer 2"}},
            {"cmd": "paint.bucket", "params": {"name": "Failing Bucket", "x": 100, "y": 100}},
        ],
    }

    config = PainterConfig(step_delay=0)
    await execute_live_drawing(client, plan, config, create_canvas=True)

    # Even with an error during paint.bucket, both layers must be restored to visible
    assert layer_visibility[1] is True
    assert layer_visibility[2] is True


@pytest.mark.anyio
async def test_mcp_client_layer_visibility_and_inspection():
    from unittest.mock import MagicMock
    from photocraft_painter.mcp_client import PhotocraftMcpClient

    mock_raw = MagicMock()
    client = PhotocraftMcpClient(mock_raw)

    async def mock_call(name, args=None):
        if name == "doc_inspect":
            return {"layers": [{"id": 1, "visible": True}, {"id": 2, "visible": False}]}
        elif name == "command_run":
            return {"status": "ok", "params": args}
        return {"status": "ok"}

    client.call_tool = MagicMock(side_effect=mock_call)

    # Test doc_inspect
    insp = await client.doc_inspect()
    assert len(insp["layers"]) == 2

    # Test set_layer_visible
    await client.set_layer_visible(layer_id=2, visible=True)
    assert any(c.args[0] == "command_run" and c.args[1]["id"] == "layer.setProps" for c in client.call_tool.call_args_list)


def test_plan_refinement_fallback_moose_fills_hollow_ears_and_avoids_yellow_body_blob():
    """Verify that cartoon moose refinement fills hollow ears in tan, adds nostrils, and never generates yellow body blobs."""
    from photocraft_painter.fallback_composer import plan_refinement_fallback

    # Pass 1: Fills hollow ears and secondary anatomy, NO yellow body bar
    p1 = plan_refinement_fallback("Cartoon Moose Full Body", style="cartoon", loop_iteration=1, total_iterations=4)
    step_names = [s.get("params", {}).get("name", "") for s in p1["steps"]]
    step_colors = [s.get("params", {}).get("color", "") for s in p1["steps"]]

    # Hollow ears must be filled
    assert any("Fill Hollow Left Ear" in n for n in step_names)
    assert any("Fill Hollow Right Ear" in n for n in step_names)
    # Ear fill color must be tan #bcaaa4
    assert "#bcaaa4" in step_colors
    # Nostrils and hoof bases must be present
    assert any("Nostril" in n for n in step_names)
    assert any("Hoof" in n for n in step_names)

    # Strictly NO yellow body blobs or bars across the body
    for step in p1["steps"]:
        params = step.get("params", {})
        color = params.get("color", "")
        name = params.get("name", "")
        # No yellow strokes on the moose
        assert color not in ("#f4d03f", "#f1c40f", "#ffff00"), f"Unexpected yellow color {color} in step {name}"
        # No wide stroke across y=400 on the body
        points = params.get("points", [])
        if len(points) > 2 and params.get("size", 0) >= 30:
            ys = [pt[1] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2]
            assert not (min(ys) <= 410 and max(ys) >= 390 and min([pt[0] for pt in points]) <= 320 and max([pt[0] for pt in points]) >= 480)

    # Pass 2: Eye pupils, catchlights, smile division, and ground cast shadows under hooves
    p2 = plan_refinement_fallback("Cartoon Moose Full Body", style="cartoon", loop_iteration=2, total_iterations=4)
    p2_names = [s.get("params", {}).get("name", "") for s in p2["steps"]]
    p2_colors = [s.get("params", {}).get("color", "") for s in p2["steps"]]
    assert any("Underside Continuous Form Shadow" in n for n in p2_names)
    assert any("Cast Shadow" in n for n in p2_names)
    # Cast shadow on grass is green
    assert "#2e7d32" in p2_colors

    # Pass 3: Eye pupils & catchlights, snout smile line, inner ear crease lines
    p3 = plan_refinement_fallback("Cartoon Moose Full Body", style="cartoon", loop_iteration=3, total_iterations=4)
    p3_names = [s.get("params", {}).get("name", "") for s in p3["steps"]]
    assert any("Pupil" in n for n in p3_names)
    assert any("Catchlight" in n for n in p3_names)
    assert any("Snout Smile" in n or "Division Line" in n for n in p3_names)
    assert any("Inner Ear" in n for n in p3_names)

    # Pass 4: Antler contours and specular gleams on tips
    p4 = plan_refinement_fallback("Cartoon Moose Full Body", style="cartoon", loop_iteration=4, total_iterations=4)
    p4_names = [s.get("params", {}).get("name", "") for s in p4["steps"]]
    assert any("Antler" in n for n in p4_names)
    assert any("Specular" in n or "Glint" in n for n in p4_names)


def test_refinement_system_prompt_directs_fleshing_out_hollow_shapes():
    """Verify that REFINEMENT_SYSTEM_PROMPT instructs the model to fill hollow outlines and maintain color harmony."""
    from photocraft_painter.composer import REFINEMENT_SYSTEM_PROMPT

    prompt_upper = REFINEMENT_SYSTEM_PROMPT.upper()
    assert "HOLLOW" in prompt_upper
    assert "EARS" in prompt_upper
    assert "FORGOTTEN" in prompt_upper or "UNPAINTED" in prompt_upper
    assert "COLOR HARMONY" in prompt_upper or "MATCHING" in prompt_upper
    assert "SOLID" in prompt_upper









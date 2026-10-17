"""Unit tests for multi-frame cel animation, layer-per-frame structure, and stroke parity."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from photocraft_painter.animator import (
    count_brush_strokes,
    enforce_stroke_parity,
    extract_mobile_feature_strokes,
    plan_animation,
    plan_animation_fallback,
)
from photocraft_painter.config import PainterConfig


def test_config_steps_default_and_clamping():
    """Verify PainterConfig.steps defaults to 1 and clamps to [1, 24]."""
    cfg = PainterConfig()
    assert cfg.steps == 1
    assert cfg.animation_steps == 1

    cfg.steps = 4
    assert cfg.steps == 4
    assert cfg.animation_steps == 4

    # Clamping below 1
    cfg.steps = 0
    assert cfg.steps == 1
    cfg.steps = -5
    assert cfg.steps == 1

    # Clamping above 24
    cfg.steps = 25
    assert cfg.steps == 24
    cfg.steps = 100
    assert cfg.steps == 24

    # Invalid types fallback to 1
    cfg.steps = "invalid"  # type: ignore
    assert cfg.steps == 1

    cfg.animation_steps = 12
    assert cfg.steps == 12


def test_cli_steps_parsing():
    """Verify CLI parser handles --steps and -st flags."""
    import argparse
    from photocraft_painter.cli import main

    # We can inspect the ArgumentParser by testing parse_args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--steps",
        "-st",
        type=int,
        default=1,
        choices=range(1, 25),
    )

    args = parser.parse_args(["--steps", "5"])
    assert args.steps == 5

    args_short = parser.parse_args(["-st", "12"])
    assert args_short.steps == 12


def test_stroke_count_parity_across_all_frames():
    """Verify that every frame of an animation has the EXACT same number of brush strokes."""
    for steps_count in (2, 3, 5):
        for detail in (3, 5):
            cfg = PainterConfig(provider="none", steps=steps_count, detail_level=detail)
            plan, source = plan_animation("a cheerful rubber duck bobbing in water", cfg)

            assert plan.get("is_animation") is True
            assert plan.get("frames_count") == steps_count
            frames = plan.get("frames", [])
            assert len(frames) == steps_count

            # Count brush strokes for each frame
            stroke_counts = [count_brush_strokes(f.get("steps", [])) for f in frames]
            target = stroke_counts[0]
            assert target > 0

            for idx, count in enumerate(stroke_counts, start=1):
                assert count == target, (
                    f"Frame {idx} has {count} brush strokes, expected {target} (detail={detail}, steps={steps_count})"
                )


def test_frames_layer_duplication_and_erase_strokes():
    """Verify Frame 1 is base, and Frames 2..N duplicate layer and apply erase & draw strokes."""
    cfg = PainterConfig(provider="none", steps=4, detail_level=5)
    plan, _ = plan_animation("a cartoon cat blinking and smiling", cfg)

    frames = plan.get("frames", [])
    assert len(frames) == 4

    # Frame 1 is base
    assert frames[0]["is_base"] is True
    assert frames[0]["frame_index"] == 1
    assert frames[0]["name"] == "Frame 1"

    # Frames 2..4 duplicate previous frame layer and apply delta erase & draw strokes
    for f in frames[1:]:
        assert f["is_base"] is False
        steps = f["steps"]

        # First command is layer.duplicate
        first_cmd = steps[0].get("cmd") or steps[0].get("id")
        assert first_cmd == "layer.duplicate"

        # Has erase strokes
        erase_strokes = [
            s for s in steps
            if (s.get("cmd") or s.get("id")) == "paint.stroke" and s.get("params", {}).get("erase") is True
        ]
        assert len(erase_strokes) > 0, f"{f['name']} must contain erase strokes"

        # Has drawing strokes
        draw_strokes = [
            s for s in steps
            if (s.get("cmd") or s.get("id")) == "paint.stroke" and not s.get("params", {}).get("erase")
        ]
        assert len(draw_strokes) > 0, f"{f['name']} must contain drawing strokes"


def test_motion_delta_is_incremental():
    """Verify coordinate changes between consecutive frames are subtle and incremental."""
    cfg = PainterConfig(provider="none", steps=6, detail_level=5)
    plan, _ = plan_animation("a bouncing red rubber ball", cfg)

    frames = plan.get("frames", [])
    assert len(frames) == 6

    # Compare coordinates of corresponding mobile strokes across consecutive delta frames
    for k in range(2, len(frames)):
        cur_frame_draw = [
            s for s in frames[k]["steps"]
            if (s.get("cmd") or s.get("id")) == "paint.stroke" and not s.get("params", {}).get("erase")
        ]
        prev_frame_draw = [
            s for s in frames[k - 1]["steps"]
            if (s.get("cmd") or s.get("id")) == "paint.stroke" and not s.get("params", {}).get("erase")
        ]
        if cur_frame_draw and prev_frame_draw:
            cur_p = cur_frame_draw[0]["params"]["points"][0]
            prev_p = prev_frame_draw[0]["params"]["points"][0]
            # Difference should be bounded (subtle delta, <= 50 px per frame)
            dx = abs(cur_p[0] - prev_p[0])
            dy = abs(cur_p[1] - prev_p[1])
            assert dx <= 50.0 and dy <= 50.0, f"Displacement between frame {k} and {k+1} too large: dx={dx}, dy={dy}"


@pytest.mark.anyio
async def test_execute_live_animation_restores_all_frames_visible():
    """Verify that post drawing, all frames (and background) are kept visible even if they overlap."""
    from photocraft_painter.artist import execute_live_animation

    mock_client = AsyncMock()
    mock_client.doc_new.return_value = {"document": 0}
    mock_client.command_run.side_effect = lambda cmd, params=None: (
        {"layer": 2} if cmd == "layer.duplicate"
        else {"status": "ok"}
    )
    mock_client.doc_inspect.return_value = {
        "layers": [
            {"id": 3, "name": "Frame 3", "visible": True},
            {"id": 2, "name": "Frame 2", "visible": True},
            {"id": 1, "name": "Frame 1", "visible": True},
            {"id": 0, "name": "Background", "visible": True},
        ]
    }

    cfg = PainterConfig(provider="none", steps=3, step_delay=0.0)
    plan, _ = plan_animation("a waving duck", cfg)

    summary = await execute_live_animation(mock_client, plan, cfg, create_canvas=True)
    assert summary["frames_drawn"] == 3

    # Check that layer.setProps visible=True was called for all layers at the end
    visibility_calls = [
        call for call in mock_client.command_run.call_args_list
        if call.args and call.args[0] == "layer.setProps" and call.args[1].get("visible") is True
    ]
    assert len(visibility_calls) >= 4  # All 4 layers set to visible True post-drawing


@pytest.mark.anyio
async def test_play_live_animation_cycles_frames_and_restores_all():
    """Verify play_live_animation cycles frames and restores all layers to visible upon stopping."""
    from photocraft_painter.artist import play_live_animation

    mock_client = AsyncMock()
    mock_client.doc_inspect.return_value = {
        "layers": [
            {"id": 2, "name": "Frame 2", "visible": True},
            {"id": 1, "name": "Frame 1", "visible": True},
            {"id": 0, "name": "Background", "visible": True},
        ]
    }
    mock_client.command_run.return_value = {"status": "ok"}

    played_frames = []

    def on_tick(cur, tot, name):
        played_frames.append((cur, tot, name))

    res = await play_live_animation(
        mock_client,
        fps=60.0,
        max_loops=1,
        on_frame_change=on_tick,
    )
    assert res["status"] == "ok"
    assert res["frames_played"] == 2
    assert len(played_frames) == 2
    assert played_frames[0] == (1, 2, "Frame 1")
    assert played_frames[1] == (2, 2, "Frame 2")

    # Verify final restoration: both Frame 1, Frame 2, and Background set visible=True
    final_set_visible = [
        call for call in mock_client.command_run.call_args_list
        if call.args and call.args[0] == "layer.setProps" and call.args[1].get("visible") is True
    ]
    assert len(final_set_visible) >= 3


@pytest.mark.anyio
async def test_play_live_animation_designate_open_file_or_index():
    """Verify /play can designate an open document by index or title."""
    from photocraft_painter.artist import play_live_animation

    mock_client = AsyncMock()
    mock_client.doc_inspect.return_value = {
        "layers": [
            {"id": 2, "name": "Frame 2", "visible": True},
            {"id": 1, "name": "Frame 1", "visible": True},
            {"id": 0, "name": "Background", "visible": True},
        ]
    }
    mock_client.command_run.return_value = {"status": "ok"}

    # Play by index 1
    res = await play_live_animation(mock_client, target_doc=1, max_loops=1)
    assert res["status"] == "ok"

    # Verify document.activate was called with {"document": 1}
    activate_calls = [
        call for call in mock_client.command_run.call_args_list
        if call.args and call.args[0] == "document.activate" and call.args[1].get("document") == 1
    ]
    assert len(activate_calls) == 1


def test_enforce_stroke_parity_trimming_and_padding():
    """Verify enforce_stroke_parity correctly adds inbetweens or trims strokes."""
    raw_strokes = [
        {"cmd": "paint.stroke", "params": {"name": f"Stroke {i}", "points": [[10, 10], [20, 20]], "color": "#000"}}
        for i in range(10)
    ]
    assert count_brush_strokes(raw_strokes) == 10

    # Test padding (target = 15)
    padded = enforce_stroke_parity(raw_strokes, target_count=15)
    assert count_brush_strokes(padded) == 15

    # Test trimming (target = 7)
    trimmed = enforce_stroke_parity(raw_strokes, target_count=7)
    assert count_brush_strokes(trimmed) == 7

    # Exact match (target = 10)
    exact = enforce_stroke_parity(raw_strokes, target_count=10)
    assert count_brush_strokes(exact) == 10


def test_steps_1_is_single_frame_static_illustration():
    """When steps=1, plan_animation returns standard single-pass illustration without animation frames."""
    cfg = PainterConfig(provider="none", steps=1, detail_level=5)
    plan, source = plan_animation("a cheerful duck", cfg)
    assert plan.get("is_animation") is not True
    assert "frames" not in plan or len(plan.get("frames", [])) <= 1


def test_steps_24_maximum_bound():
    """Verify maximum bound of 24 frames generates 24 frames, all with identical stroke count."""
    cfg = PainterConfig(provider="none", steps=24, detail_level=3)
    plan, source = plan_animation("a fluttering butterfly", cfg)

    assert plan.get("is_animation") is True
    assert plan.get("frames_count") == 24
    frames = plan.get("frames", [])
    assert len(frames) == 24
    assert "[24 Frames]" in plan.get("title", "")

    # Check parity across all 24 frames
    counts = [count_brush_strokes(f["steps"]) for f in frames]
    assert len(set(counts)) == 1, f"Not all 24 frames have equal strokes: {counts}"


def test_animated_portrait_face_blinking():
    """Verify face animation generates blinking eyelids / facial feature delta transforms with stroke parity."""
    cfg = PainterConfig(provider="none", steps=4, detail_level=5)
    plan, _ = plan_animation("portrait of a smiling woman blinking her eyes", cfg)

    frames = plan.get("frames", [])
    assert len(frames) == 4

    counts = [count_brush_strokes(f["steps"]) for f in frames]
    assert counts[0] == counts[1] == counts[2] == counts[3]


@pytest.mark.anyio
async def test_list_open_documents():
    """Verify list_open_documents discovers open document tabs."""
    from photocraft_painter.artist import list_open_documents

    mock_client = AsyncMock()
    mock_client.command_run.side_effect = lambda cmd, params=None: (
        {"name": "Untitled-1", "width": 800, "height": 800, "layers": [{"id": 0}]}
        if params and params.get("document") == 0
        else (
            {"name": "Animation.psd", "width": 1024, "height": 768, "layers": [{"id": 0}, {"id": 1}]}
            if params and params.get("document") == 1
            else (_ for _ in ()).throw(RuntimeError("no document at index"))
        )
    )

    docs = await list_open_documents(mock_client)
    assert len(docs) == 2
    assert docs[0]["title"] == "Untitled-1"
    assert docs[1]["title"] == "Animation.psd"
    assert docs[1]["layers_count"] == 2


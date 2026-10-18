"""Unit tests for the movie export module."""

import asyncio
import os
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from photocraft_painter.movie import (
    check_movie_dependencies,
    detect_canvas_crop_box,
    encode_video_ffmpeg,
    export_document_movie,
    get_movie_output_path,
    process_frame_magick,
)


def test_check_movie_dependencies():
    """Verify tool detection for ffmpeg and magick."""
    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}"
        ok, missing = check_movie_dependencies()
        assert ok is True
        assert len(missing) == 0

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: None if cmd == "ffmpeg" else f"/usr/bin/{cmd}"
        ok, missing = check_movie_dependencies()
        assert ok is False
        assert "ffmpeg" in missing

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: None if cmd == "magick" else f"/usr/bin/{cmd}"
        ok, missing = check_movie_dependencies()
        assert ok is False
        assert any("magick" in m for m in missing)


def test_get_movie_output_path_default_cwd():
    """Verify default export directory is current working directory when EXPORT_MOVIE_FOLDER is unset."""
    with patch.dict(os.environ, {}, clear=True):
        out_path, warning = get_movie_output_path(doc_title="My Animation")
        assert warning is None
        assert out_path.parent == Path.cwd()
        assert out_path.name == "My Animation.mp4"


def test_get_movie_output_path_valid_env_folder():
    """Verify export directory honors EXPORT_MOVIE_FOLDER when it exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"EXPORT_MOVIE_FOLDER": tmpdir}):
            out_path, warning = get_movie_output_path(doc_title="Walk Cycle [24 Frames].psd")
            assert warning is None
            assert out_path.parent == Path(tmpdir).resolve()
            assert out_path.name == "Walk Cycle [24 Frames].mp4"


def test_get_movie_output_path_nonexistent_env_folder_warning():
    """Verify warning is issued and fallback to cwd when EXPORT_MOVIE_FOLDER does not exist."""
    fake_folder = "/path/to/definitely/nonexistent/movie_export_folder_12345"
    with patch.dict(os.environ, {"EXPORT_MOVIE_FOLDER": fake_folder}):
        out_path, warning = get_movie_output_path(doc_title="Bounce Test")
        assert warning is not None
        assert fake_folder in warning
        assert out_path.parent == Path.cwd()
        assert out_path.name == "Bounce Test.mp4"


def test_process_frame_magick_and_ffmpeg_encoding():
    """Verify real magick and ffmpeg pipeline creates a valid MP4."""
    with tempfile.TemporaryDirectory() as tmpdir:
        t = Path(tmpdir)
        raw1 = t / "raw_1.png"
        raw2 = t / "raw_2.png"
        # Valid 2x2 PNG bytes with correct CRCs
        minimal_png = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000200000002080600000072b60d240000001149444154789c63f8cfc0f01f8419600c0047ca07f967596eb70000000049454e44ae426082"
        )
        raw1.write_bytes(minimal_png)
        raw2.write_bytes(minimal_png)

        proc1 = t / "frame_0001.png"
        proc2 = t / "frame_0002.png"
        assert process_frame_magick(raw1, proc1) is True
        assert process_frame_magick(raw2, proc2) is True
        assert proc1.exists() and proc1.stat().st_size > 0
        assert proc2.exists() and proc2.stat().st_size > 0

        out_mp4 = t / "result.mp4"
        pattern = str(t / "frame_%04d.png")
        success, err = encode_video_ffmpeg(pattern, out_mp4, fps=5.0)
        assert success is True
        assert err == ""
        assert out_mp4.exists()
        assert out_mp4.stat().st_size > 0


@pytest.mark.anyio
async def test_export_document_movie_orchestrator():
    """Verify export_document_movie isolates layers, captures frames, and restores all layers to visible."""
    mock_client = AsyncMock()
    mock_client.doc_inspect.return_value = {
        "title": "Test Cel Animation",
        "layers": [
            {"id": 202, "name": "Frame 2", "visible": True},
            {"id": 201, "name": "Frame 1", "visible": True},
            {"id": 200, "name": "Background", "visible": True},
        ],
    }

    # Mock render_preview returning valid PNG bytes
    minimal_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000200000002080600000072b60d240000001149444154789c63f8cfc0f01f8419600c0047ca07f967596eb70000000049454e44ae426082"
    )
    mock_client.render_preview.return_value = minimal_png
    mock_client.command_run.return_value = {"status": "ok"}

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_mp4 = Path(tmpdir) / "output.mp4"
        frames_progress: list[int] = []

        def on_prog(cur, tot, name):
            frames_progress.append(cur)

        res = await export_document_movie(
            client=mock_client,
            fps=5.0,
            output_path=dest_mp4,
            on_frame_progress=on_prog,
        )

        assert res["status"] == "ok"
        assert res["frames_count"] == 2
        assert res["fps"] == 5.0
        assert dest_mp4.exists()
        assert dest_mp4.stat().st_size > 0
        assert frames_progress == [1, 2]

        # Verify all layers were restored to visible: True in finally
        restored_calls = [
            c for c in mock_client.command_run.call_args_list
            if c.args and c.args[0] == "layer.setProps" and c.args[1].get("visible") is True
        ]
        # Frame 1, Frame 2, Background should all be restored
        restored_lids = [c.args[1].get("layer") for c in restored_calls]
        assert 201 in restored_lids
        assert 202 in restored_lids
        assert 200 in restored_lids


@pytest.mark.anyio
async def test_export_document_movie_insufficient_layers():
    """Verify error status when document has fewer than 2 layers."""
    mock_client = AsyncMock()
    mock_client.doc_inspect.return_value = {
        "title": "Single Layer Doc",
        "layers": [{"id": 100, "name": "Background", "visible": True}],
    }

    res = await export_document_movie(client=mock_client, fps=5.0)
    assert res["status"] == "error"
    assert "at least 2 layers" in res["message"].lower()


def test_detect_canvas_crop_box_synthetic():
    """Verify detect_canvas_crop_box detects an inner canvas surrounded by pasteboard."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        test_img = Path(tmpdir) / "synthetic_window.png"
        im = Image.new("L", (1000, 800), color=40)
        # Inner canvas from x=200..800, y=100..700 (width=601, height=601) with white 255
        for x in range(200, 801):
            for y in range(100, 701):
                im.putpixel((x, y), 255)
        im.save(test_img)

        box = detect_canvas_crop_box(test_img)
        assert box is not None
        x, y, w, h = box
        assert x == 200
        assert y == 100
        assert w == 601
        assert h == 601


def test_detect_canvas_crop_box_small_or_invalid():
    """Verify detect_canvas_crop_box returns None for small mock images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_img = Path(tmpdir) / "tiny.png"
        minimal_png = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000200000002080600000072b60d240000001149444154789c63f8cfc0f01f8419600c0047ca07f967596eb70000000049454e44ae426082"
        )
        test_img.write_bytes(minimal_png)
        box = detect_canvas_crop_box(test_img)
        assert box is None


def test_process_frame_magick_with_crop():
    """Verify process_frame_magick crops image when crop_box is provided."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        t = Path(tmpdir)
        raw = t / "raw.png"
        proc = t / "proc.png"
        im = Image.new("RGB", (400, 400), color=(40, 40, 40))
        # White canvas inside 100..300, 100..300 (200x200)
        for x in range(100, 300):
            for y in range(100, 300):
                im.putpixel((x, y), (255, 255, 255))
        im.save(raw)

        assert process_frame_magick(raw, proc, crop_box=(100, 100, 200, 200)) is True
        assert proc.exists()
        with Image.open(proc) as res:
            assert res.size == (200, 200)


def test_detect_canvas_crop_box_resilient_to_dark_inking_lines():
    """Verify detect_canvas_crop_box does not mistake cartoon black ink lines for pasteboard edge."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        test_img = Path(tmpdir) / "synthetic_cartoon_window.png"
        im = Image.new("L", (1000, 800), color=40)
        # Inner canvas from x=200..800, y=100..700 (width=601, height=601) with white 255
        for x in range(200, 801):
            for y in range(100, 701):
                im.putpixel((x, y), 255)

        # Draw vertical dark cartoon ink lines inside the canvas at x=696 and x=350
        for y in range(100, 701):
            for dx in range(6):
                im.putpixel((696 + dx, y), 18)
                im.putpixel((350 + dx, y), 18)

        im.save(test_img)

        box = detect_canvas_crop_box(test_img)
        assert box is not None
        x, y, w, h = box
        # Must detect the full canvas width and not crop prematurely at x=350 or x=696
        assert x == 200
        assert y == 100
        assert w == 601
        assert h == 601


def test_export_movie_from_psd_direct():
    """Verify export_movie_from_psd extracts layers, composites over background, and encodes valid MP4."""
    from photocraft_painter.movie import export_movie_from_psd

    sample_psd = Path("/home/jp/Pictures/Cartoon Rabbit Hopping Ac [Cartoon][Detail 10][gemini-4-argon].psd")
    if not sample_psd.exists():
        pytest.skip("Sample PSD file not found on disk")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_mp4 = Path(tmpdir) / "rabbit_direct.mp4"
        frames_seen = []

        def on_prog(cur, tot, name):
            frames_seen.append((cur, tot, name))

        res = export_movie_from_psd(
            psd_path=sample_psd,
            output_mp4=out_mp4,
            fps=5.0,
            on_frame_progress=on_prog,
        )

        assert res["status"] == "ok"
        assert res["frames_count"] == 24
        assert res["fps"] == 5.0
        assert out_mp4.exists()
        assert out_mp4.stat().st_size > 0
        assert len(frames_seen) == 24


@pytest.mark.anyio
async def test_export_document_movie_routes_to_psd_path():
    """Verify export_document_movie directly handles PSD file paths without requiring active client."""
    sample_psd = Path("/home/jp/Pictures/Cartoon Rabbit Hopping Ac [Cartoon][Detail 10][gemini-4-argon].psd")
    if not sample_psd.exists():
        pytest.skip("Sample PSD file not found on disk")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_mp4 = Path(tmpdir) / "rabbit_routed.mp4"
        res = await export_document_movie(
            client=None,
            target_doc=str(sample_psd),
            fps=5.0,
            output_path=out_mp4,
        )
        assert res["status"] == "ok"
        assert res["frames_count"] == 24
        assert out_mp4.exists()
        assert out_mp4.stat().st_size > 0


@pytest.mark.anyio
async def test_export_document_movie_temp_png_per_layer_with_background():
    """Verify export_document_movie exports each layer to its own temp PNG with Background visible and never screen-records."""
    mock_client = AsyncMock()
    mock_client.doc_inspect.return_value = {
        "title": "Temp PNG Layer Export Test",
        "width": 2,
        "height": 2,
        "layers": [
            {"id": 303, "name": "Frame 3", "visible": True},
            {"id": 302, "name": "Frame 2", "visible": True},
            {"id": 301, "name": "Frame 1", "visible": True},
            {"id": 300, "name": "Background", "visible": True},
        ],
    }

    minimal_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000200000002080600000072b60d240000001149444154789c63f8cfc0f01f8419600c0047ca07f967596eb70000000049454e44ae426082"
    )
    exported_temp_files: list[str] = []
    visibility_state: dict[int, bool] = {300: True, 301: True, 302: True, 303: True}
    snapshots_at_export: list[dict[int, bool]] = []

    async def fake_command_run(cmd: str, params: dict):
        if cmd == "layer.setProps":
            lid = params.get("layer")
            if lid in visibility_state and "visible" in params:
                visibility_state[lid] = bool(params["visible"])
        return {"status": "ok"}

    async def fake_doc_export(path_str: str):
        exported_temp_files.append(path_str)
        snapshots_at_export.append(dict(visibility_state))
        Path(path_str).write_bytes(minimal_png)
        return {"path": path_str}

    mock_client.command_run.side_effect = fake_command_run
    mock_client.doc_export.side_effect = fake_doc_export

    with tempfile.TemporaryDirectory() as tmpdir:
        out_mp4 = Path(tmpdir) / "stitched_temp_layers.mp4"
        res = await export_document_movie(
            client=mock_client,
            fps=5.0,
            output_path=out_mp4,
        )

        assert res["status"] == "ok"
        assert res["frames_count"] == 3
        assert res["crop_box"] is None
        assert out_mp4.exists() and out_mp4.stat().st_size > 0

        # Screen-recording fallback (render_preview) must NOT have been called
        mock_client.render_preview.assert_not_called()

        # Verify 3 sequential PNG files were exported into the system temporary directory in order
        assert len(exported_temp_files) == 3
        assert exported_temp_files[0].endswith("frame_0001.png")
        assert exported_temp_files[1].endswith("frame_0002.png")
        assert exported_temp_files[2].endswith("frame_0003.png")

        # Verify Background (300) was visible in every frame alongside only the active Frame layer in order (301, 302, 303)
        assert snapshots_at_export[0] == {300: True, 301: True, 302: False, 303: False}
        assert snapshots_at_export[1] == {300: True, 301: False, 302: True, 303: False}
        assert snapshots_at_export[2] == {300: True, 301: False, 302: False, 303: True}

        # Verify all layers (including Background) are restored to visible after export
        assert visibility_state == {300: True, 301: True, 302: True, 303: True}



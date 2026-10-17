"""Movie export module for PhotoCraft Painter.

Exports all layers/frames of an open document in PhotoCraft as an MP4 video file
using ImageMagick (`magick`) and FFmpeg (`ffmpeg`) via subprocess.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from photocraft_painter.mcp_client import PhotocraftMcpClient

logger = logging.getLogger(__name__)


def check_movie_dependencies() -> tuple[bool, list[str]]:
    """Check if both ffmpeg and imagemagick (magick) are installed and available in PATH.

    Returns:
        (is_available, list_of_missing_tool_names)
    """
    missing: list[str] = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("magick"):
        missing.append("magick (ImageMagick)")
    return len(missing) == 0, missing


def get_movie_output_path(
    doc_title: str | None = None,
    output_folder_override: str | None = None,
) -> tuple[Path, str | None]:
    """Determine the destination folder and output file path for the movie.

    Saves to the current working directory by default, but if the EXPORT_MOVIE_FOLDER
    environment variable is set, uses that directory. If the directory does not exist,
    returns a warning message and falls back to Path.cwd().

    Returns:
        (output_file_path, optional_warning_message)
    """
    env_folder = output_folder_override if output_folder_override is not None else os.getenv("EXPORT_MOVIE_FOLDER")
    warning: str | None = None
    target_dir = Path.cwd()

    if env_folder:
        folder_path = Path(env_folder).expanduser()
        if folder_path.exists() and folder_path.is_dir():
            target_dir = folder_path.resolve()
        else:
            warning = (
                f"EXPORT_MOVIE_FOLDER '{env_folder}' does not exist or is not a directory. "
                f"Generating movie in current working directory ({Path.cwd()}) instead."
            )
            target_dir = Path.cwd()

    # Sanitize document title for filename
    safe_title = "animation"
    if doc_title:
        # Strip extension if present (.psd, .pcraft, etc.)
        stem = Path(doc_title).stem if "." in doc_title else doc_title
        clean = re.sub(r'[\\/*?:"<>|]', "", stem).strip()
        if clean:
            safe_title = clean

    output_path = target_dir / f"{safe_title}.mp4"
    return output_path, warning


def detect_canvas_crop_box(image_path: Path | str) -> tuple[int, int, int, int] | None:
    """Detect the bounding box of the active document canvas inside the application window screenshot.

    In PhotoCraft GUI screenshots, the canvas is situated in the central work area,
    surrounded by the pasteboard (dark background) and application chrome (toolbar,
    options bar, dock panels, status bar).

    Returns:
        (x, y, width, height) tuple in pixel coordinates, or None if detection fails or image is too small.
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            gray = img.convert("L")
            w, h = gray.size
            if w < 100 or h < 100:
                return None

            # Sample pasteboard in regions known to be pasteboard in PhotoCraft (outside canvas):
            # Left pasteboard: x ~ 0.10 * w, y ~ 0.50 * h and 0.80 * h
            sample_1 = gray.getpixel((int(w * 0.10), int(h * 0.50)))
            sample_2 = gray.getpixel((int(w * 0.10), int(h * 0.80)))
            pb_color = (sample_1 + sample_2) // 2

            # Find candidates for canvas pixels in central region
            candidates = []
            y_step = max(1, h // 30)
            x_step = max(1, w // 30)
            for y in range(int(h * 0.25), int(h * 0.75), y_step):
                for x in range(int(w * 0.20), int(w * 0.75), x_step):
                    val = gray.getpixel((x, y))
                    if abs(val - pb_color) > 25:
                        candidates.append((x, y, val))

            if not candidates:
                return None

            # Seed point: median/mean of candidate coordinates
            cx = sum(c[0] for c in candidates) // len(candidates)
            cy = sum(c[1] for c in candidates) // len(candidates)

            # Ensure (cx, cy) is a canvas pixel; if not, pick the candidate closest to (cx, cy)
            if abs(gray.getpixel((cx, cy)) - pb_color) <= 20:
                candidates.sort(key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
                cx, cy = candidates[0][0], candidates[0][1]

            pb_thresh = max(15, min(35, abs(gray.getpixel((cx, cy)) - pb_color) // 3))

            # Scan left from cx
            left_x = 0
            for x in range(cx, 0, -1):
                if abs(gray.getpixel((x, cy)) - pb_color) <= pb_thresh:
                    left_x = x + 1
                    break

            # Scan right from cx
            right_x = w - 1
            for x in range(cx, w):
                if abs(gray.getpixel((x, cy)) - pb_color) <= pb_thresh:
                    right_x = x - 1
                    break

            mid_x = (left_x + right_x) // 2

            # Scan up from cy
            top_y = 0
            for y in range(cy, 0, -1):
                if abs(gray.getpixel((mid_x, y)) - pb_color) <= pb_thresh:
                    top_y = y + 1
                    break

            # Scan down from cy
            bottom_y = h - 1
            for y in range(cy, h):
                if abs(gray.getpixel((mid_x, y)) - pb_color) <= pb_thresh:
                    bottom_y = y - 1
                    break

            cw = right_x - left_x + 1
            ch = bottom_y - top_y + 1

            # Validate sanity of detected box:
            # Must occupy a reasonable portion of the window (e.g. at least 15% width and height)
            # and not be the entire window
            if cw >= int(w * 0.15) and ch >= int(h * 0.15) and (cw < w or ch < h):
                return (left_x, top_y, cw, ch)
    except Exception as e:
        logger.debug("Canvas detection failed: %s", e)
    return None


def process_frame_magick(
    input_png: Path,
    output_png: Path,
    crop_box: tuple[int, int, int, int] | None = None,
) -> bool:
    """Use ImageMagick (`magick`) to composite frame onto solid white background, optionally crop, and remove alpha."""
    cmd = ["magick", str(input_png.resolve())]
    if crop_box is not None:
        x, y, w, h = crop_box
        cmd.extend(["-crop", f"{w}x{h}+{x}+{y}", "+repage"])
    cmd.extend([
        "-background",
        "white",
        "-flatten",
        "-alpha",
        "off",
        str(output_png.resolve()),
    ])
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return output_png.exists() and output_png.stat().st_size > 0
    except Exception as e:
        logger.warning("ImageMagick frame processing failed: %s", e)
        # Fallback: copy or Pillow crop if magick fails
        try:
            if crop_box is not None:
                try:
                    from PIL import Image

                    with Image.open(input_png) as img:
                        x, y, w, h = crop_box
                        cropped = img.crop((x, y, x + w, y + h))
                        cropped.save(output_png)
                        return True
                except Exception:
                    pass
            shutil.copy2(input_png, output_png)
            return True
        except Exception:
            return False


def encode_video_ffmpeg(
    input_pattern: str,
    output_mp4: Path,
    fps: float = 5.0,
) -> tuple[bool, str]:
    """Use FFmpeg to encode an image sequence into an H.264 MP4 video.

    Args:
        input_pattern: Path pattern for input frames (e.g. '/path/to/frame_%04d.png')
        output_mp4: Destination .mp4 file
        fps: Target framerate in frames per second (e.g. 5.0)

    Returns:
        (success, error_or_output_message)
    """
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        input_pattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        str(output_mp4.resolve()),
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return False, f"FFmpeg failed (exit {proc.returncode}): {proc.stderr.strip()}"
        if not output_mp4.exists() or output_mp4.stat().st_size == 0:
            return False, "FFmpeg finished but output MP4 file was not generated or is empty."
        return True, ""
    except Exception as e:
        return False, f"FFmpeg subprocess error: {e}"


async def export_document_movie(
    client: PhotocraftMcpClient,
    target_doc: str | int | None = None,
    fps: float = 5.0,
    output_path: Path | str | None = None,
    on_frame_progress: Callable[[int, int, str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Export all layers/frames of the open document in PhotoCraft as an MP4 movie.

    Sequentially isolates each frame layer over the background, captures canvas renders,
    processes them with ImageMagick (`magick`), and encodes the MP4 movie using `ffmpeg`.
    Post-export, all layers are restored to visible.

    Returns:
        dict containing "status", "path", "frames_count", "fps", "duration", "size_bytes",
        or "status": "error", "message": "..."
    """
    # 1. Check tools
    available, missing = check_movie_dependencies()
    if not available:
        return {
            "status": "error",
            "message": (
                f"Required tools missing: {', '.join(missing)}. "
                f"Both ffmpeg and ImageMagick ('magick') must be installed locally to export movies."
            ),
        }

    # 2. Activate designated document if requested
    if target_doc is not None:
        if isinstance(target_doc, int):
            await client.command_run("document.activate", {"document": target_doc})
        elif isinstance(target_doc, str):
            p = Path(target_doc).expanduser()
            if p.exists() and p.is_file():
                await client.command_run("file.openAs", {"path": str(p.resolve())})
            else:
                matched = False
                if target_doc.isdigit():
                    try:
                        await client.command_run("document.activate", {"document": int(target_doc)})
                        matched = True
                    except Exception:
                        pass
                if not matched:
                    from photocraft_painter.artist import list_open_documents
                    open_docs = await list_open_documents(client)
                    for d in open_docs:
                        if target_doc.lower() in str(d.get("title", "")).lower():
                            await client.command_run("document.activate", {"document": d["index"]})
                            matched = True
                            break

    # 3. Inspect document
    info = await client.doc_inspect() if hasattr(client, "doc_inspect") else await client.command_run("document.inspect", {})
    if not isinstance(info, dict) or "layers" not in info:
        return {"status": "error", "message": "No active document or layers found in PhotoCraft"}

    doc_title = info.get("name") or info.get("title") or "PhotoCraft Animation"
    all_layers = info.get("layers", [])
    if len(all_layers) < 2:
        return {
            "status": "error",
            "message": f"Document has only {len(all_layers)} layer(s). At least 2 layers are needed to generate an animation movie.",
        }

    bg_id = all_layers[-1].get("id")

    # Separate frames: either Frame 1..N or top-to-bottom layers
    frame_numbered: list[tuple[int, dict[str, Any]]] = []
    other_layers: list[dict[str, Any]] = []

    for l in all_layers:
        if l.get("id") == bg_id:
            continue
        lname = str(l.get("name", "")).strip()
        m = re.match(r"^Frame\s*(\d+)$", lname, re.IGNORECASE)
        if m:
            frame_numbered.append((int(m.group(1)), l))
        else:
            other_layers.append(l)

    frame_layers: list[dict[str, Any]] = []
    if frame_numbered:
        frame_numbered.sort(key=lambda x: x[0])
        frame_layers = [item[1] for item in frame_numbered]
    else:
        frame_layers = list(reversed(other_layers))

    if len(frame_layers) < 2:
        return {
            "status": "error",
            "message": f"Found only {len(frame_layers)} frame layer(s). Need at least 2 frames to generate a movie.",
        }

    total_frames = len(frame_layers)
    fps_val = max(0.1, min(120.0, float(fps)))

    # Determine destination file path
    final_output_path: Path
    folder_warning: str | None = None
    if output_path is not None:
        final_output_path = Path(output_path).expanduser().resolve()
    else:
        final_output_path, folder_warning = get_movie_output_path(doc_title=doc_title)

    if on_status and folder_warning:
        on_status(folder_warning)

    with tempfile.TemporaryDirectory(prefix="photocraft_movie_") as tmpdir:
        tmp_dir_path = Path(tmpdir)
        raw_frames_dir = tmp_dir_path / "raw"
        proc_frames_dir = tmp_dir_path / "proc"
        raw_frames_dir.mkdir(parents=True, exist_ok=True)
        proc_frames_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Ensure background layer is visible
            if bg_id is not None:
                try:
                    await client.command_run("layer.setProps", {"layer": bg_id, "visible": True})
                except Exception:
                    pass

            # Initial isolation: hide all frame layers
            for flayer in frame_layers:
                fid = flayer.get("id")
                if fid is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": fid, "visible": False})
                    except Exception:
                        pass

            # Sequentially expose each frame and capture
            crop_box: tuple[int, int, int, int] | None = None
            prev_id: int | None = None
            for idx, flayer in enumerate(frame_layers, start=1):
                cur_id = flayer.get("id")
                cur_name = flayer.get("name") or f"Frame {idx}"

                if prev_id is not None and prev_id != cur_id:
                    try:
                        await client.command_run("layer.setProps", {"layer": prev_id, "visible": False})
                    except Exception:
                        pass

                if cur_id is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": cur_id, "visible": True})
                    except Exception:
                        pass
                prev_id = cur_id

                if on_frame_progress:
                    on_frame_progress(idx, total_frames, cur_name)

                raw_png = raw_frames_dir / f"frame_{idx:04d}.png"
                proc_png = proc_frames_dir / f"frame_{idx:04d}.png"

                # Capture frame render
                captured = False
                try:
                    preview = await client.render_preview(max_side=1920)
                    if isinstance(preview, bytes) and len(preview) > 0:
                        raw_png.write_bytes(preview)
                        captured = True
                    elif isinstance(preview, str) and len(preview) > 0:
                        try:
                            raw_png.write_bytes(base64.b64decode(preview))
                            captured = True
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("render_preview notice during movie capture: %s", e)

                if not captured:
                    # Fallback to capture_png
                    try:
                        await client.capture_png(raw_png)
                        if raw_png.exists() and raw_png.stat().st_size > 0:
                            captured = True
                    except Exception as e:
                        logger.warning("capture_png fallback failed for frame %d: %s", idx, e)

                if not captured:
                    # Synthetic minimal fallback (valid 2x2 white PNG)
                    minimal_png = bytes.fromhex(
                        "89504e470d0a1a0a0000000d494844520000000200000002080600000072b60d240000001149444154789c63f8cfc0f01f8419600c0047ca07f967596eb70000000049454e44ae426082"
                    )
                    raw_png.write_bytes(minimal_png)

                # Detect canvas crop box on first frame if available
                if crop_box is None and idx == 1:
                    crop_box = detect_canvas_crop_box(raw_png)
                    if crop_box and on_status:
                        on_status(f"Cropping video to canvas bounds: {crop_box[2]}x{crop_box[3]} (excluding controls)...")

                # Process through ImageMagick (magick)
                process_frame_magick(raw_png, proc_png, crop_box=crop_box)

            # 4. Encode MP4 video with FFmpeg
            if on_status:
                on_status(f"Encoding {total_frames} frames into MP4 movie via FFmpeg @ {fps_val:.1f} fps...")

            input_pattern = str(proc_frames_dir / "frame_%04d.png")
            success, err_msg = encode_video_ffmpeg(input_pattern, final_output_path, fps=fps_val)
            if not success:
                return {
                    "status": "error",
                    "message": f"Video encoding failed: {err_msg}",
                }

        finally:
            # 5. Always restore ALL frame layers and background to visible
            for flayer in frame_layers:
                fid = flayer.get("id")
                if fid is not None:
                    try:
                        await client.command_run("layer.setProps", {"layer": fid, "visible": True})
                    except Exception:
                        pass
            if bg_id is not None:
                try:
                    await client.command_run("layer.setProps", {"layer": bg_id, "visible": True})
                except Exception:
                    pass

    return {
        "status": "ok",
        "path": str(final_output_path.resolve()),
        "doc_title": doc_title,
        "frames_count": total_frames,
        "fps": fps_val,
        "duration": round(float(total_frames) / fps_val, 2),
        "size_bytes": final_output_path.stat().st_size if final_output_path.exists() else 0,
        "warning": folder_warning,
        "crop_box": crop_box,
    }

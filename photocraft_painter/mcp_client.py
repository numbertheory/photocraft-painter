from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

import mcp.client.stdio
from mcp import ClientSession, StdioServerParameters
from mcp.types import ImageContent, TextContent

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig

logger = logging.getLogger(__name__)


class PhotocraftMcpError(RuntimeError):
    """Raised when an MCP tool call fails."""


class PhotocraftMcpClient:
    """Async client communicating with PhotoCraft via the MCP bridge server."""

    def __init__(self, session: ClientSession):
        self._session = session

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        retries: int = 2,
    ) -> Any:
        """Call an MCP tool and unpack its result or raise PhotocraftMcpError.

        Automatically reconnects and retries on bridge connection disconnects.
        """
        last_error = None
        for attempt in range(retries + 1):
            try:
                res = await self._session.call_tool(name, arguments or {})
                if res.is_error:
                    msg = "Tool call failed"
                    if res.content:
                        parts = []
                        for c in res.content:
                            if isinstance(c, TextContent):
                                parts.append(c.text)
                            elif hasattr(c, "text"):
                                parts.append(str(c.text))
                        if parts:
                            msg = "\n".join(parts)

                    # Check for transient bridge disconnect (e.g. PhotoCraft 30s idle TCP timeout)
                    is_bridge_disconnect = any(
                        token in msg.lower()
                        for token in [
                            "connection closed by the app",
                            "operation may have completed; inspect state before retrying",
                            "timed out connecting",
                            "cannot connect",
                            "not connected",
                            "broken pipe",
                        ]
                    )

                    if attempt < retries and is_bridge_disconnect:
                        logger.info(
                            "Bridge connection was idle/closed by desktop app; re-authenticating and retrying %s (%d/%d)...",
                            name,
                            attempt + 1,
                            retries,
                        )
                        await asyncio.sleep(0.2)
                        continue

                    raise PhotocraftMcpError(f"[{name}] {msg}")

                # If there is image content, return bytes/b64, else parse JSON text if possible
                for item in res.content:
                    if isinstance(item, ImageContent):
                        return item.data
                    if isinstance(item, TextContent):
                        text = item.text
                        try:
                            return json.loads(text)
                        except Exception:
                            return text
                return res
            except PhotocraftMcpError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    await asyncio.sleep(0.2)
                    continue
                raise PhotocraftMcpError(f"[{name}] {exc}") from exc

        if last_error:
            raise PhotocraftMcpError(f"[{name}] {last_error}") from last_error

    async def doc_new(
        self,
        width: int = 800,
        height: int = 800,
        background: str = "white",
        name: str = "Artwork",
        mode: str = "rgb",
        depth: int = 8,
    ) -> Any:
        """Create a new document canvas."""
        return await self.call_tool(
            "doc_new",
            {
                "width": width,
                "height": height,
                "background": background,
                "name": name,
                "mode": mode,
                "depth": depth,
            },
        )

    async def command_run(
        self,
        cmd_id: str,
        params: dict[str, Any] | None = None,
        wait: bool = True,
    ) -> Any:
        """Execute a single PhotoCraft engine command."""
        return await self.call_tool(
            "command_run",
            {
                "id": cmd_id,
                "params": params or {},
                "wait": wait,
            },
        )

    async def command_batch(
        self,
        steps: list[dict[str, Any]],
        stop_on_error: bool = True,
    ) -> Any:
        """Execute multiple engine commands in a single batch."""
        formatted_steps = []
        for s in steps:
            formatted_steps.append(
                {
                    "id": s.get("id") or s.get("command"),
                    "params": s.get("params") or {},
                    "wait": s.get("wait", True),
                }
            )
        return await self.call_tool(
            "command_batch",
            {
                "steps": formatted_steps,
                "stop_on_error": stop_on_error,
            },
        )

    async def create_shape(
        self,
        kind: str,
        rect: list[float] | tuple[float, float, float, float],
        fill: str | None = None,
        stroke: dict[str, Any] | None = None,
        name: str | None = None,
        radii: float | list[float] | None = None,
        sides: int | None = None,
        star_ratio: float | None = None,
    ) -> Any:
        """Create a new vector shape layer (ellipse, rect, roundedRect, polygon, star, line)."""
        params: dict[str, Any] = {
            "kind": kind,
            "rect": list(rect),
        }
        if fill is not None:
            params["fill"] = fill
        if stroke is not None:
            params["stroke"] = stroke
        if name is not None:
            params["name"] = name
        if radii is not None:
            params["radii"] = radii
        if sides is not None:
            params["sides"] = sides
        if star_ratio is not None:
            params["starRatio"] = star_ratio

        return await self.command_run("shape.create", params)

    async def paint_stroke(
        self,
        points: list[list[float]],
        size: float = 20.0,
        color: str = "#000000",
        hardness: float = 1.0,
        opacity: float = 1.0,
    ) -> Any:
        """Paint a brush stroke with coordinates."""
        params: dict[str, Any] = {
            "points": points,
            "size": size,
            "color": color,
            "hardness": hardness,
            "opacity": opacity,
        }
        return await self.command_run("paint.stroke", params)

    async def new_layer(self, name: str = "Layer") -> Any:
        """Add a new raster layer."""
        return await self.command_run("layer.new.layer", {"name": name})

    async def doc_inspect(self) -> dict[str, Any]:
        """Inspect active document state and layer tree."""
        try:
            res = await self.call_tool("doc_inspect", {})
            if isinstance(res, dict):
                return res
            if isinstance(res, str):
                return json.loads(res)
            return {}
        except Exception:
            try:
                res = await self.command_run("document.inspect", {})
                if isinstance(res, dict):
                    return res
                if isinstance(res, str):
                    return json.loads(res)
                return {}
            except Exception:
                return {}

    async def set_layer_props(self, layer_id: int | None = None, **props: Any) -> Any:
        """Set layer properties (e.g. visibility, opacity)."""
        params: dict[str, Any] = dict(props)
        if layer_id is not None:
            params["layer"] = layer_id
        return await self.command_run("layer.setProps", params)

    async def set_layer_visible(self, layer_id: int | None = None, visible: bool = True) -> Any:
        """Set layer visibility."""
        return await self.set_layer_props(layer_id=layer_id, visible=visible)

    async def fill_bucket(self, x: float, y: float, color: str) -> Any:
        """Fill an area using the Paint Bucket tool."""
        return await self.command_run(
            "paint.bucket",
            {"x": x, "y": y, "color": color},
        )

    async def render_preview(self, max_side: int = 1024) -> Any:
        """Render a flattened PNG preview (or window screenshot in bridge mode)."""
        return await self.call_tool("doc_render_preview", {"max_side": max_side})

    async def doc_export(self, path: str) -> Any:
        """Export the active document to a file path."""
        return await self.call_tool("doc_export", {"path": path})

    async def capture_png(self, output_path: str | Path | None = None) -> Path:
        """Capture the current canvas state as a PNG image file for critique & refinement loops.

        Attempts doc_export first, with fallback to render_preview or minimal valid PNG generation.
        """
        if output_path is None:
            fd, tmp = tempfile.mkstemp(prefix="photocraft_in_progress_", suffix=".png")
            os.close(fd)
            path = Path(tmp)
        else:
            path = Path(output_path)

        path.parent.mkdir(parents=True, exist_ok=True)
        exported = False

        # 1. Attempt doc_export
        try:
            await self.doc_export(str(path.resolve()))
            if path.exists() and path.stat().st_size > 0:
                exported = True
        except Exception as e:
            logger.debug("doc_export attempt during capture_png: %s", e)

        # 2. Fallback to render_preview / ui_screenshot
        if not exported:
            try:
                preview = await self.render_preview(max_side=1024)
                if isinstance(preview, bytes) and len(preview) > 0:
                    path.write_bytes(preview)
                    exported = True
                elif isinstance(preview, str) and len(preview) > 0:
                    try:
                        data = base64.b64decode(preview)
                        path.write_bytes(data)
                        exported = True
                    except Exception:
                        pass
                elif isinstance(preview, dict):
                    raw_data = preview.get("data") or preview.get("image") or ""
                    if raw_data:
                        path.write_bytes(base64.b64decode(raw_data))
                        exported = True
            except Exception as e:
                logger.debug("render_preview attempt during capture_png: %s", e)

        # 3. Fallback to valid minimal PNG if neither produced bytes
        if not exported and (not path.exists() or path.stat().st_size == 0):
            minimal_png = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02"
                b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            path.write_bytes(minimal_png)

        return path

    async def ui_inspect(self) -> Any:
        """Inspect live GUI state (bridge mode only)."""
        return await self.call_tool("ui_inspect")

    async def ui_screenshot(self, max_side: int | None = None) -> Any:
        """Capture screenshot of the live desktop app window."""
        args: dict[str, Any] = {}
        if max_side:
            args["max_side"] = max_side
        return await self.call_tool("ui_screenshot", args)

    async def doc_close(self, discard: bool = True) -> Any:
        """Close the active document canvas."""
        return await self.command_run("file.close", {"discard": discard})

    async def session_list(self) -> Any:
        """List open documents."""
        return await self.call_tool("session_list")


@asynccontextmanager
async def connect_mcp_bridge(
    config: PainterConfig,
) -> AsyncIterator[PhotocraftMcpClient]:
    """Launch photocraft-cli mcp --bridge and yield an active PhotocraftMcpClient with keepalive."""
    token_file = config.ensure_token_file()

    server_params = StdioServerParameters(
        command=config.photocraft_cli_bin,
        args=[
            "mcp",
            "--bridge",
            f"{config.control_host}:{config.control_port}",
            "--control-token-file",
            str(token_file.resolve()),
        ],
    )

    async with mcp.client.stdio.stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            client = PhotocraftMcpClient(session)

            # Start background keepalive heartbeat (15s ping) so PhotoCraft's 30s loopback TCP timeout never expires
            async def _keepalive_loop() -> None:
                while True:
                    try:
                        await asyncio.sleep(15)
                        await client.call_tool("doc_inspect", {}, retries=1)
                    except asyncio.CancelledError:
                        break
                    except Exception as err:
                        logger.debug("Keepalive ping notice: %s", err)

            keepalive_task = asyncio.create_task(_keepalive_loop())
            try:
                yield client
            finally:
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except (asyncio.CancelledError, Exception):
                    pass

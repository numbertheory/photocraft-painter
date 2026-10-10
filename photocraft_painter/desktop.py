"""Desktop process supervisor and connection check for PhotoCraft."""

from __future__ import annotations

import socket
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from photocraft_painter.config import PainterConfig


def is_desktop_running(host: str = "127.0.0.1", port: int = 7878, timeout: float = 0.5) -> bool:
    """Check if PhotoCraft desktop control server is reachable on the given port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def launch_desktop(
    config: PainterConfig, wait_timeout: float = 10.0
) -> subprocess.Popen[bytes]:
    """Launch PhotoCraft desktop application with control protocol flags enabled."""
    token_file = config.ensure_token_file()

    cmd = [
        config.photocraft_bin,
        "--control",
        str(config.control_port),
        "--control-token-file",
        str(token_file.resolve()),
        "--automation-read-root",
        str(config.read_root.resolve()),
        "--automation-write-root",
        str(config.write_root.resolve()),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Wait for the control port to open
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        if is_desktop_running(config.control_host, config.control_port):
            return proc
        time.sleep(0.2)

    if proc.poll() is not None:
        raise RuntimeError(
            f"PhotoCraft process exited prematurely with code {proc.returncode}."
        )

    raise TimeoutError(
        f"Timed out waiting for PhotoCraft to listen on {config.control_host}:{config.control_port}."
    )

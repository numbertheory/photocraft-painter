"""Configuration management for PhotoCraft Painter."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PainterConfig:
    """Settings for PhotoCraft MCP bridge client and drawing session."""

    control_host: str = "127.0.0.1"
    control_port: int = 7878
    control_token_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("PHOTOCRAFT_CONTROL_TOKEN_FILE")
            or Path.home() / ".config" / "photocraft" / "control.token"
        )
    )
    control_token: str | None = field(
        default_factory=lambda: os.getenv("PHOTOCRAFT_CONTROL_TOKEN")
    )
    photocraft_bin: str = field(
        default_factory=lambda: os.getenv("PHOTOCRAFT_BIN") or "photocraft"
    )
    photocraft_cli_bin: str = field(
        default_factory=lambda: os.getenv("PHOTOCRAFT_CLI_BIN") or "photocraft-cli"
    )
    read_root: Path = field(default_factory=Path.cwd)
    write_root: Path = field(default_factory=Path.cwd)

    # Drawing animation speed and canvas geometry
    step_delay: float = 0.12  # seconds between drawing steps to visualize progress live
    default_width: int = 800
    default_height: int = 800

    # Detail level: 1 (minimal/quick) to 5 (ultra/dense brushstrokes across all layers)
    detail_level: int = 3

    # AI Model Settings - Ollama is the default composer
    provider: str = field(
        default_factory=lambda: os.getenv("PAINTER_PROVIDER") or "ollama"
    )
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL") or "ornith-1.5:35b"
    )

    # Secondary/alternative OpenAI settings
    openai_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    openai_base_url: str | None = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    )

    def ensure_token_file(self) -> Path:
        """Ensure a control token file exists; generate one if missing."""
        if self.control_token_file.exists():
            return self.control_token_file

        self.control_token_file.parent.mkdir(parents=True, exist_ok=True)
        token = self.control_token or secrets.token_hex(32)
        # Write mode 0600 on Unix
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(str(self.control_token_file), flags, mode)
        with open(fd, "w", encoding="ascii") as f:
            f.write(token.strip())
        return self.control_token_file

    def get_token(self) -> str:
        """Read the control token."""
        if self.control_token:
            return self.control_token
        token_path = self.ensure_token_file()
        return token_path.read_text(encoding="ascii").strip()

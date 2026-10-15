"""Configuration management for PhotoCraft Painter."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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

    # Artistic style preset: realistic, dreamlike, abstract, sketchy, cartoon, painterly, cubism
    style: str = field(
        default_factory=lambda: os.getenv("PAINTER_STYLE") or "realistic"
    )

    # Detail level: 1 (minimal) to 25 (ultra detail with ~250 brushstrokes)
    detail_level: int = 5

    # Refinement feedback loop: 1 (default: single pass, no loop) to 5 (1 initial + up to 4 refinement loops)
    loop: int = field(
        default_factory=lambda: max(1, min(5, int(os.getenv("PAINTER_LOOP") or "1")))
    )

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "loop", max(1, min(5, int(self.loop))))
        except (ValueError, TypeError):
            object.__setattr__(self, "loop", 1)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("loop", "loop_count"):
            try:
                clamped = max(1, min(5, int(value)))
            except (ValueError, TypeError):
                clamped = 1
            object.__setattr__(self, "loop", clamped)
            return
        object.__setattr__(self, name, value)

    @property
    def loop_count(self) -> int:
        return self.loop

    @loop_count.setter
    def loop_count(self, value: int) -> None:
        self.loop = value

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

    # Google Gemini settings (defaults to Google's official OpenAI-compatible endpoint)
    gemini_api_key: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    gemini_base_url: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL") or "gemini-3.8-flash"
    )

    @property
    def active_model(self) -> str:
        """Return the current active model name based on provider."""
        if self.provider in ("gemini", "google"):
            return self.gemini_model
        if self.provider == "openai":
            return self.openai_model
        return self.ollama_model

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

"""Model registry, discovery, and on-the-fly selection for PhotoCraft Painter.

Enables inspecting locally installed Ollama models, exploring recommended models
from the Ollama library (https://ollama.com/search) and cloud providers, and
switching active AI models dynamically in the REPL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from rich.table import Table

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelChoice:
    """Descriptor for an available or recommended AI model."""

    name: str
    description: str
    category: str  # "Local", "Cloud", or "Library"
    provider: str  # "ollama" or "openai"
    size_str: str = ""
    param_size: str = ""


SUGGESTED_LIBRARY_MODELS: list[ModelChoice] = [
    ModelChoice(
        name="ornith-1.5:35b",
        description="Specialized reasoning & structured illustration model (Default)",
        category="Library",
        provider="ollama",
        param_size="35B",
    ),
    ModelChoice(
        name="llama3.3:70b",
        description="Meta flagship 70B open model; state-of-the-art reasoning & instructions",
        category="Library",
        provider="ollama",
        param_size="70B",
    ),
    ModelChoice(
        name="llama3.1:8b",
        description="Meta versatile 8B open model; fast, reliable, excellent JSON support",
        category="Library",
        provider="ollama",
        param_size="8B",
    ),
    ModelChoice(
        name="llama3.2:3b",
        description="Meta lightweight 3B model; ultra-fast for rapid sketching",
        category="Library",
        provider="ollama",
        param_size="3B",
    ),
    ModelChoice(
        name="qwen2.5:32b",
        description="Alibaba Qwen 2.5 32B; top-tier coding & structured JSON schema fidelity",
        category="Library",
        provider="ollama",
        param_size="32B",
    ),
    ModelChoice(
        name="qwen2.5:14b",
        description="Alibaba Qwen 2.5 14B; balanced speed and high-precision structured plans",
        category="Library",
        provider="ollama",
        param_size="14B",
    ),
    ModelChoice(
        name="qwen2.5:7b",
        description="Alibaba Qwen 2.5 7B; fast generation with reliable JSON output",
        category="Library",
        provider="ollama",
        param_size="7B",
    ),
    ModelChoice(
        name="deepseek-r1:32b",
        description="DeepSeek R1 32B; deep step-by-step thinking for complex artistic planning",
        category="Library",
        provider="ollama",
        param_size="32B",
    ),
    ModelChoice(
        name="deepseek-r1:14b",
        description="DeepSeek R1 14B; compact reasoning model with high step accuracy",
        category="Library",
        provider="ollama",
        param_size="14B",
    ),
    ModelChoice(
        name="mistral-small:24b",
        description="Mistral AI 24B; versatile reasoning and multilingual creative instruction",
        category="Library",
        provider="ollama",
        param_size="24B",
    ),
    ModelChoice(
        name="phi4:14b",
        description="Microsoft Phi-4 14B; dense synthetic reasoning and structured precision",
        category="Library",
        provider="ollama",
        param_size="14B",
    ),
    ModelChoice(
        name="gemma2:27b",
        description="Google DeepMind Gemma 2 27B; high comprehension and creative richness",
        category="Library",
        provider="ollama",
        param_size="27B",
    ),
    ModelChoice(
        name="llama3.2-vision:11b",
        description="Meta multimodal vision model; analyzes input images & reference photos (Vision)",
        category="Library",
        provider="ollama",
        param_size="11B",
    ),
    ModelChoice(
        name="qwen2.5-vl:7b",
        description="Alibaba Qwen 2.5 Vision-Language model for image understanding & drawing (Vision)",
        category="Library",
        provider="ollama",
        param_size="7B",
    ),
    ModelChoice(
        name="llava:13b",
        description="Popular open multimodal model for reference image analysis (Vision)",
        category="Library",
        provider="ollama",
        param_size="13B",
    ),
    ModelChoice(
        name="gpt-4o-mini",
        description="OpenAI high-speed multimodal cloud model (Vision-capable)",
        category="Cloud",
        provider="openai",
    ),
    ModelChoice(
        name="gpt-4o",
        description="OpenAI flagship multimodal cloud model (Vision-capable)",
        category="Cloud",
        provider="openai",
    ),
]


def format_bytes(num_bytes: int) -> str:
    """Format byte size into human-readable string."""
    if num_bytes <= 0:
        return ""
    if num_bytes >= 1024**3:
        return f"{num_bytes / (1024**3):.1f} GB"
    if num_bytes >= 1024**2:
        return f"{num_bytes / (1024**2):.1f} MB"
    return f"{num_bytes / 1024:.1f} KB"


def get_local_ollama_models(host: str = "http://127.0.0.1:11434") -> list[ModelChoice]:
    """Fetch locally installed models from the running Ollama instance."""
    try:
        import ollama

        client = ollama.Client(host=host)
        resp = client.list()
        raw_models = getattr(resp, "models", []) or []
        local_choices: list[ModelChoice] = []
        for m in raw_models:
            name = getattr(m, "model", "") or getattr(m, "name", "")
            if not name:
                continue
            size = getattr(m, "size", 0) or 0
            size_str = format_bytes(size) if size else ""
            details = getattr(m, "details", None)
            param_size = getattr(details, "parameter_size", "") if details else ""

            is_cloud = ":cloud" in name or "cloud" in name.lower()
            category = "Cloud" if is_cloud else "Local"
            desc = "Ollama cloud model" if is_cloud else "Installed local model"

            local_choices.append(
                ModelChoice(
                    name=name,
                    description=desc,
                    category=category,
                    provider="ollama",
                    size_str=size_str,
                    param_size=param_size,
                )
            )
        return local_choices
    except Exception as e:
        logger.debug("Could not query Ollama at %s: %s", host, e)
        return []


def get_all_model_choices(host: str = "http://127.0.0.1:11434") -> list[ModelChoice]:
    """Combine locally installed models and curated library suggestions."""
    local_models = get_local_ollama_models(host)
    seen_names = {m.name.lower() for m in local_models}

    combined = list(local_models)
    for sug in SUGGESTED_LIBRARY_MODELS:
        # If already installed locally, do not duplicate
        if sug.name.lower() not in seen_names:
            combined.append(sug)
    return combined


def build_models_table(
    choices: list[ModelChoice], current_model: str, current_provider: str = "ollama"
) -> Table:
    """Construct a styled Rich table of available and suggested models."""
    table = Table(
        title="[bold cyan]Available Models & Suggestions[/] [dim](https://ollama.com/search)[/]",
        border_style="cyan",
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="bold cyan", no_wrap=True)
    table.add_column("Model Tag", style="bold white", no_wrap=True)
    table.add_column("Type", justify="center", no_wrap=True)
    table.add_column("Specs", style="dim yellow", no_wrap=True)
    table.add_column("Description", style="dim")

    norm_current = current_model.lower()

    for idx, m in enumerate(choices, start=1):
        is_active = (
            m.name.lower() == norm_current
            or (f"{m.name.lower()}:latest" == norm_current)
            or (norm_current == f"{m.name.lower()}:latest")
        ) and (m.provider == current_provider)

        name_display = f"[bold green]▶ {m.name}[/]" if is_active else m.name

        type_color = "green" if m.category == "Local" else ("blue" if m.category == "Cloud" else "magenta")
        type_display = f"[{type_color}]{m.category}[/]"

        specs_parts = [p for p in (m.param_size, m.size_str) if p]
        specs = ", ".join(specs_parts) if specs_parts else (m.provider.upper() if m.category == "Cloud" else "—")

        desc = f"[bold green](Active) [/]{m.description}" if is_active else m.description

        table.add_row(
            str(idx),
            name_display,
            type_display,
            specs,
            desc,
        )

    return table


def resolve_model_selection(
    choice_str: str,
    choices: list[ModelChoice],
) -> tuple[str, str]:
    """Resolve user input (numeric index or model name) to (model_name, provider)."""
    cleaned = choice_str.strip()
    if not cleaned:
        raise ValueError("Model selection cannot be empty")

    # 1. 1-based index lookup
    if cleaned.isdigit():
        idx = int(cleaned)
        if 1 <= idx <= len(choices):
            selected = choices[idx - 1]
            return selected.name, selected.provider
        raise ValueError(f"Invalid model number {idx}. Choose between 1 and {len(choices)}.")

    # 2. Exact match in available choices
    lower_cleaned = cleaned.lower()
    for m in choices:
        if m.name.lower() == lower_cleaned:
            return m.name, m.provider

    # 3. Provider prefix overrides
    if lower_cleaned.startswith("openai/"):
        return cleaned[7:].strip(), "openai"
    if lower_cleaned.startswith("ollama/"):
        return cleaned[7:].strip(), "ollama"

    # 4. Known OpenAI model naming
    if any(lower_cleaned.startswith(p) for p in ("gpt-", "o1-", "o3-")):
        return cleaned, "openai"

    # 5. Default to Ollama with the given model name
    return cleaned, "ollama"

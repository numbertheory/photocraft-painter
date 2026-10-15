"""Unit tests for PhotoCraft Painter model discovery, listing, suggestions, and resolution."""

import pytest
from photocraft_painter.models import (
    ModelChoice,
    SUGGESTED_LIBRARY_MODELS,
    build_models_table,
    format_bytes,
    get_all_model_choices,
    get_local_ollama_models,
    resolve_model_selection,
)


def test_suggested_library_models_structure():
    assert len(SUGGESTED_LIBRARY_MODELS) >= 8

    # Default and key popular models must be present
    names = [m.name for m in SUGGESTED_LIBRARY_MODELS]
    assert "ornith-1.5:35b" in names
    assert "llama3.3:70b" in names
    assert "qwen2.5:32b" in names
    assert "deepseek-r1:32b" in names
    assert "gpt-4o-mini" in names
    assert "gemini-4-argon" in names
    assert "gemini-3.8-flash" in names
    assert "gemini-2.5-flash" in names
    assert "llama3.2-vision:11b" in names
    assert "qwen2.5-vl:7b" in names

    for m in SUGGESTED_LIBRARY_MODELS:
        assert m.name
        assert m.description
        assert m.category in ("Library", "Cloud", "Local")
        assert m.provider in ("ollama", "openai", "gemini")


def test_format_bytes():
    assert format_bytes(0) == ""
    assert format_bytes(-10) == ""
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024 * 5) == "5.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.0 GB"


def test_resolve_model_selection_by_index():
    choices = [
        ModelChoice(name="local-model:7b", description="Local", category="Local", provider="ollama"),
        ModelChoice(name="gpt-4o-mini", description="Cloud", category="Cloud", provider="openai"),
        ModelChoice(name="llama3.3:70b", description="Library", category="Library", provider="ollama"),
    ]

    # Valid 1-based index
    name1, prov1 = resolve_model_selection("1", choices)
    assert name1 == "local-model:7b"
    assert prov1 == "ollama"

    name2, prov2 = resolve_model_selection("2", choices)
    assert name2 == "gpt-4o-mini"
    assert prov2 == "openai"

    name3, prov3 = resolve_model_selection("3", choices)
    assert name3 == "llama3.3:70b"
    assert prov3 == "ollama"

    # Out of bounds
    with pytest.raises(ValueError, match="Invalid model number 4"):
        resolve_model_selection("4", choices)

    with pytest.raises(ValueError, match="Invalid model number 0"):
        resolve_model_selection("0", choices)


def test_resolve_model_selection_by_name():
    choices = [
        ModelChoice(name="qwen2.5:32b", description="Qwen", category="Library", provider="ollama"),
        ModelChoice(name="gpt-4o", description="OpenAI", category="Cloud", provider="openai"),
    ]

    # Exact and case-insensitive
    name, prov = resolve_model_selection("qwen2.5:32b", choices)
    assert name == "qwen2.5:32b"
    assert prov == "ollama"

    name_ci, prov_ci = resolve_model_selection("QWEN2.5:32B", choices)
    assert name_ci == "qwen2.5:32b"
    assert prov_ci == "ollama"

    # OpenAI cloud model
    name_cloud, prov_cloud = resolve_model_selection("gpt-4o", choices)
    assert name_cloud == "gpt-4o"
    assert prov_cloud == "openai"

    # Google Gemini cloud model (exact and space-separated)
    choices_with_gemini = choices + [
        ModelChoice(name="gemini-3.8-flash", description="Gemini 3.8 Flash", category="Cloud", provider="gemini"),
    ]
    name_gem, prov_gem = resolve_model_selection("gemini-3.8-flash", choices_with_gemini)
    assert name_gem == "gemini-3.8-flash"
    assert prov_gem == "gemini"

    name_gem_sp, prov_gem_sp = resolve_model_selection("gemini 3.8 flash", choices_with_gemini)
    assert name_gem_sp == "gemini-3.8-flash"
    assert prov_gem_sp == "gemini"

    # Gemini 4 Argon
    choices_with_argon = choices_with_gemini + [
        ModelChoice(name="gemini-4-argon", description="Gemini 4 Argon", category="Cloud", provider="gemini"),
    ]
    name_arg, prov_arg = resolve_model_selection("gemini-4-argon", choices_with_argon)
    assert name_arg == "gemini-4-argon"
    assert prov_arg == "gemini"

    name_arg_sp, prov_arg_sp = resolve_model_selection("gemini 4 argon", choices_with_argon)
    assert name_arg_sp == "gemini-4-argon"
    assert prov_arg_sp == "gemini"

    name_arg_short, prov_arg_short = resolve_model_selection("argon", choices_with_argon)
    assert name_arg_short == "gemini-4-argon"
    assert prov_arg_short == "gemini"

    # Prefixed explicit providers
    name_pre, prov_pre = resolve_model_selection("openai/my-fine-tuned", choices)
    assert name_pre == "my-fine-tuned"
    assert prov_pre == "openai"

    name_gem_pre, prov_gem_pre = resolve_model_selection("gemini/custom-gemini-preview", choices)
    assert name_gem_pre == "custom-gemini-preview"
    assert prov_gem_pre == "gemini"

    name_goo_pre, prov_goo_pre = resolve_model_selection("google/custom-gemini-preview", choices)
    assert name_goo_pre == "custom-gemini-preview"
    assert prov_goo_pre == "gemini"

    name_oll, prov_oll = resolve_model_selection("ollama/custom-tag:latest", choices)
    assert name_oll == "custom-tag:latest"
    assert prov_oll == "ollama"

    # Arbitrary unlisted model defaults to ollama
    name_arb, prov_arb = resolve_model_selection("some-unlisted-model:8b", choices)
    assert name_arb == "some-unlisted-model:8b"
    assert prov_arb == "ollama"

    # Empty raises
    with pytest.raises(ValueError, match="cannot be empty"):
        resolve_model_selection("   ", choices)


def test_build_models_table():
    choices = [
        ModelChoice(name="ornith:35b", description="Installed model", category="Local", provider="ollama", param_size="35B", size_str="21.2 GB"),
        ModelChoice(name="gpt-4o-mini", description="Cloud model", category="Cloud", provider="openai"),
    ]
    table = build_models_table(choices, current_model="ornith:35b", current_provider="ollama")
    assert table is not None
    assert len(table.rows) == 2


def test_get_local_ollama_models_graceful_on_failure():
    # Attempting to connect to an invalid host should return an empty list without raising
    models = get_local_ollama_models(host="http://127.0.0.1:59999")
    assert isinstance(models, list)
    assert len(models) == 0


def test_get_all_model_choices_includes_suggestions():
    # Even if local Ollama fails or is empty, suggestions from library must be included
    all_choices = get_all_model_choices(host="http://127.0.0.1:59999")
    assert len(all_choices) >= len(SUGGESTED_LIBRARY_MODELS)
    names = [c.name for c in all_choices]
    assert "ornith-1.5:35b" in names
    assert "llama3.3:70b" in names

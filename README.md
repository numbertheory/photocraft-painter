# PhotoCraft Painter 🎨

Live AI painter and composer for **PhotoCraft** using the **Model Context Protocol (MCP)** in **Bridge Mode**.

Powered by **Ollama** and the **`ornith-1.5:35b`** model by default. Type in any prompt (e.g. *"a rubber duck in water"*, *"a mountain sunset"*, *"a cozy coffee cup"*), and watch the AI plan, compose, and draw the artwork **live on screen** inside your running PhotoCraft desktop window!

---

## Architecture Overview

```
User Prompt (CLI / REPL)
       │
       ▼
Ollama AI Composer (`ornith-1.5:35b` @ 127.0.0.1:11434)
       │ (JSON vector illustration plan)
       ▼
Command Normalizer & Sanitizer (shapes, fills, strokes)
       │
       ▼
PhotoCraft MCP Client (Python `mcp` SDK via stdio)
       │
       ▼
`photocraft-cli mcp --bridge 127.0.0.1:7878`
       │ (Loopback TCP control protocol)
       ▼
`photocraft --control 7878` (Native Desktop GUI)
       │
       ▼
Live Drawing Appears on Screen in Real Time!
```

---

## Requirements

* Python 3.11+
* `uv` packaging tool
* `photocraft` and `photocraft-cli` on your system `PATH`
* `ollama` running locally with the `ornith-1.5:35b` model

---

## Quickstart with `uv`

### 1. Install Dependencies
```bash
cd /home/jp/dev/photocraft-painter
uv sync
```

### 2. Start PhotoCraft with Bridge Control
```bash
photocraft --control 7878 --control-token-file ~/.config/photocraft/control.token
```
*(Or let `photocraft-painter --launch` start it automatically!)*

### 3. Run the Painter

```bash
# Interactive prompt REPL:
uv run photocraft-painter

# Draw a prompt directly:
uv run photocraft-painter "a rubber duck in water"
```

---

## AI Model Configuration

**Ollama is the default AI composer**, pre-configured for `ornith-1.5:35b`:

* **Default Host:** `http://127.0.0.1:11434` (configurable via `OLLAMA_HOST` or `--ollama-host`)
* **Default Model:** `ornith-1.5:35b` (configurable via `OLLAMA_MODEL` or `--model`)
* **Context & Token Tuning:** Automatically configured with `num_ctx: 16384` and `num_predict: 6144` to accommodate reasoning/thinking models without truncation.

### Switching Models
To use any other model installed in your Ollama:
```bash
uv run photocraft-painter --model "llama3.2" "a mountain landscape"
```

### Optional OpenAI Provider
If you want to use OpenAI or OpenRouter instead:
```bash
export OPENAI_API_KEY="sk-..."
uv run photocraft-painter --provider openai --model "gpt-4o-mini" "a neon city"
```

---

## CLI Options

| Flag | Description | Default |
|---|---|---|
| `prompt` | Direct prompt to draw immediately | *(Opens interactive REPL)* |
| `--detail`, `-d` | Drawing detail level from `1` (minimal) to `25` (~10 to ~250 brushstrokes) | `5` |
| `--model` | Model name | `ornith-1.5:35b` |
| `--ollama-host` | Ollama API endpoint | `http://127.0.0.1:11434` |
| `--port` | PhotoCraft control server port | `7878` |
| `--delay` | Delay in seconds between steps to visualize progress | `0.12` |
| `--launch` | Automatically launch PhotoCraft desktop if not running | `false` |
| `--provider` | AI provider (`ollama` or `openai`) | `ollama` |

### Detail Levels (1 to 25)
Detail scales the number and density of brushstrokes across all layers (~10 brushstrokes per detail level):
* **Level 1 (Minimal):** Loose gestural sketch lines and basic color blocking (~10–20 brushstrokes).
* **Level 5 (Standard Default):** Layered color washes, form shading, clean ink contours, and highlights (**~50 brushstrokes**).
* **Level 10 (High Detail):** Richer multi-pass sweeps, cross-hatching, and enhanced textural accents (**~100 brushstrokes**).
* **Level 15 (Very High Detail):** Dense painterly color washes, extensive directional shading, and secondary details (**~150 brushstrokes**).
* **Level 20 (Ultra Detail):** Heavy multi-pass strokes, intricate ink work, cross-hatching, and multiple specular accents (**~200 brushstrokes**).
* **Level 25 (Masterwork Density):** Maximum artist density across all layers, dense cross-hatching, fine line work, and intricate highlights (**~250 brushstrokes**).

---

## Interactive REPL Commands

* `<prompt text>`: Generate illustration and draw live on screen (each prompt starts a fresh canvas).
* `/detail <1-25>`: Adjust drawing detail level dynamically (e.g. `/detail 5` for ~50 strokes, `/detail 25` for ~250 strokes).
* `/export <file.png>`: Export active document as PNG.
* `/speed <sec>`: Change live animation speed (e.g. `/speed 0.05` for faster drawing).
* `/help`: Display available commands.
* `/quit`: Exit the painter.

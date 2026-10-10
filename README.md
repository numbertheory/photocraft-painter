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
* **Context & Token Tuning:** Automatically configured with `num_ctx: 8192` and `num_predict: 4096` to accommodate reasoning/thinking models without truncation.

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
| `--detail`, `-d` | Drawing detail level from `1` (minimal) to `5` (ultra brushstrokes across all layers) | `3` |
| `--model` | Model name | `ornith-1.5:35b` |
| `--ollama-host` | Ollama API endpoint | `http://127.0.0.1:11434` |
| `--port` | PhotoCraft control server port | `7878` |
| `--delay` | Delay in seconds between steps to visualize progress | `0.12` |
| `--launch` | Automatically launch PhotoCraft desktop if not running | `false` |
| `--provider` | AI provider (`ollama` or `openai`) | `ollama` |

### Detail Levels (1 to 5)
Higher detail values scale brushstrokes and visual density across all layers:
* **Level 1 (Minimal):** Fast, loose gestural sketch, simple color washes (~15 brushstrokes).
* **Level 2 (Light):** Basic gesture guides, flat color washes, light contours (~25 brushstrokes).
* **Level 3 (Standard):** Balanced multi-pass sketch, volumetric shading, and crisp ink lines (~45 brushstrokes).
* **Level 4 (High Detail):** Dense painterly shading, form hatching, multi-pass contours, and specular accents (~70 brushstrokes).
* **Level 5 (Ultra Detail):** Masterwork richness, textured brushstrokes, deep cross-hatching, nuanced shadows, and glints (~100+ brushstrokes).

---

## Interactive REPL Commands

* `<prompt text>`: Generate illustration and draw live on screen.
* `/detail <1-5>`: Adjust drawing detail level dynamically (e.g. `/detail 5` for ultra brushstrokes).
* `/export <file.png>`: Export active document as PNG.
* `/speed <sec>`: Change live animation speed (e.g. `/speed 0.05` for faster drawing).
* `/help`: Display available commands.
* `/quit`: Exit the painter.

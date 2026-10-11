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

# Draw inspired by a reference image:
uv run photocraft-painter "file:/home/jp/apple.png make a green apple"
```

---

## Vision & Reference Images (`file:<path>`)

PhotoCraft Painter supports multimodal vision capabilities ([Ollama Vision](https://docs.ollama.com/capabilities/vision) & OpenAI Multimodal) using the `file:<path>` keyword anywhere in your prompt. You can reference one or more local image files to inspire the subject, anatomy, colors, and composition of the drawing!

### Syntax Examples

* **Direct path with prompt:**
  ```text
  file:/home/jp/apple.png make a green apple
  ```
* **Paths containing spaces (quoted):**
  ```text
  file:"/home/jp/Pictures/My Duck.png" paint this in an impressionist style
  ```
* **Tilde expansion (`~`):**
  ```text
  file:~/photos/sunset.jpg draw a dreamlike version of this sunset
  ```
* **Image only (default artistic prompt):**
  ```text
  file:/home/jp/portrait.png
  ```
* **Multiple reference images:**
  ```text
  file:/tmp/subject.png file:/tmp/background.png combine these into a vibrant study
  ```

### Supported Vision Models
When providing reference images via `file:<path>`, use a vision-capable model:
* **Local (Ollama):** Switch using `/model llama3.2-vision:11b`, `/model qwen2.5-vl:7b`, or `/model llava:13b`.
* **Cloud (OpenAI):** Switch using `/model gpt-4o-mini` or `/model gpt-4o`.

If you provide an image reference to a text-only model (like `ornith-1.5:35b` or `llama3.1:8b`), Painter provides a friendly suggestion to switch to a vision model.

---

## AI Model Configuration

**Ollama is the default AI composer**, pre-configured for `ornith-1.5:35b`:

* **Default Host:** `http://127.0.0.1:11434` (configurable via `OLLAMA_HOST` or `--ollama-host`)
* **Default Model:** `ornith-1.5:35b` (configurable via `OLLAMA_MODEL` or `--model`)
* **Context & Token Tuning:** Automatically configured with `num_ctx: 16384` and `num_predict: 6144` to accommodate reasoning/thinking models without truncation.

### On-the-Fly Model Switching (`/model`)
You can view, explore, and switch models at any time inside the interactive REPL without restarting:
* Type `/model` to display a Rich table of all **locally installed Ollama models** on your machine alongside curated recommendations from **[ollama.com/search](https://ollama.com/search)** and cloud providers.
* Select any model interactively by entering its number (e.g., `1`, `4`) or model tag.
* Switch directly on the fly: `/model llama3.2-vision:11b`, `/model qwen2.5:32b`, or `/model gpt-4o-mini`.

### Recommended Models for PhotoCraft
* **`ornith-1.5:35b` (Default):** Specialized reasoning & structured vector illustration.
* **`llama3.2-vision:11b` (Vision):** Meta's flagship local vision model for drawing from reference images (`file:<path>`).
* **`qwen2.5-vl:7b` (Vision):** Lightweight vision-language model with sharp spatial understanding.
* **`llama3.3:70b`:** Meta's flagship 70B open model with state-of-the-art instruction adherence.
* **`qwen2.5:32b` / `qwen2.5:14b`:** Exceptional JSON schema fidelity and compositional creativity.
* **`deepseek-r1:32b`:** Deep chain-of-thought planning for intricate multi-layer drawings.
* **`llama3.2:3b`:** Ultra-fast lightweight model for rapid sketches and quick studies.
* **`gpt-4o-mini` / `gpt-4o` (Vision):** High-speed structured precision and cloud multimodal vision support.

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
| `prompt` | Direct prompt to draw immediately (supports `file:<path>`) | *(Opens interactive REPL)* |
| `--style`, `-s` | Overarching artistic style (`realistic`, `dreamlike`, `abstract`, `sketchy`, `cartoon`, `painterly`) | `realistic` |
| `--detail`, `-d` | Drawing detail level from `1` (minimal) to `25` (~10 to ~250 brushstrokes) | `5` |
| `--model` | Model name | `ornith-1.5:35b` |
| `--ollama-host` | Ollama API endpoint | `http://127.0.0.1:11434` |
| `--port` | PhotoCraft control server port | `7878` |
| `--delay` | Delay in seconds between steps to visualize progress | `0.12` |
| `--launch` | Automatically launch PhotoCraft desktop if not running | `false` |
| `--provider` | AI provider (`ollama` or `openai`) | `ollama` |

### Overarching Artistic Styles (`/style`)
The artistic style sits above all other controls, governing AI aesthetic guidance, color palette selection, and stroke rendering dynamics:
* **`realistic` (Default):** Natural lighting, volumetric chiaroscuro shading, smooth feathered transitions, true-to-life values.
* **`dreamlike`:** Ethereal surrealism, glowing translucent washes, pastel & celestial tones, soft luminous aura halos.
* **`abstract`:** Bold geometric & organic deconstructed planes, dynamic expressive angles, vibrant color pops and clashes.
* **`sketchy`:** Loose gestural graphite & charcoal pencil lines, visible construction guides, directional cross-hatching, monochrome / sepia tones.
* **`cartoon`:** Vibrant cel-shaded animation, crisp saturated primary fills, bold confident ink outlines, punchy highlight gleams.
* **`painterly`:** Rich oil & acrylic impasto, expressive directional brushwork, textured color sweeps, warm/cool temperature vibrations.

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
* `file:<path> <text>`: Reference local image(s) to inspire composition, subject, colors, and lighting (e.g. `file:/home/jp/apple.png make a green apple`).
* `/style`: List all available artistic styles and highlight the active style.
* `/style <name>`: Switch the active artistic style (e.g. `/style dreamlike`, `/style cartoon`, `/style sketchy`).
* `/model`: List locally installed Ollama models & recommended models (https://ollama.com/search) with interactive selection.
* `/model <name|#>`: Switch active AI model on the fly by name (e.g. `/model llama3.2-vision:11b`, `/model gpt-4o-mini`) or list number (e.g. `/model 2`).
* `/detail <1-25>`: Adjust drawing detail level dynamically (e.g. `/detail 5` for ~50 strokes, `/detail 25` for ~250 strokes).
* `/export <file.png>`: Export active document as PNG.
* `/speed <sec>`: Change live animation speed (e.g. `/speed 0.05` for faster drawing).
* `/help`: Display available commands and syntax.
* `/quit`: Exit the painter.

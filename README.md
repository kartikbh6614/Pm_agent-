# PM Agent — Figma → PRD Generator

A CLI tool that reads a Figma wireframe and generates a full Product Requirements Document (PRD) using a local Ollama LLM. No cloud dependencies — fully offline after setup.

---

## How It Works

1. **Run the tool** — just `python pm_agent.py`, no flags needed
2. **Enter your Figma URL** — you'll be prompted to paste it in the terminal
3. **Fetch design** — connects to the Figma REST API and extracts screens, text, components, and interactive elements
4. **Choose a problem statement** — the LLM generates 3 options (UX / Business / Technical angles), you pick one
5. **Generate PRD** — the LLM produces a structured PRD with goals, user stories, acceptance criteria, edge cases, and open questions
6. **Download output** — writes `.md`, `.json`, and `.html` files to the output folder; HTML auto-opens in browser

---

## Dependencies

Install Python dependencies:

```bash
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---|---|---|
| `ollama` | 0.4.4 | Local LLM client |
| `requests` | 2.32.3 | Figma REST API calls |
| `pydantic` | 2.10.6 | Structured LLM output validation |
| `rich` | 13.9.4 | Terminal UI (spinners, tables, panels) |
| `python-dotenv` | 1.0.1 | Load `.env` config |

You also need **Ollama** installed and running locally with a model pulled:

```bash
ollama pull qwen2.5:7b
```

---

## Setup (one-time per machine)

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install and start Ollama + pull a model
```bash
ollama pull qwen2.5:7b
```

### 3. Get your Figma access token
Go to **figma.com → Account Settings → Security → Generate new personal access token**

You can either:
- Create a `.env` file with `FIGMA_ACCESS_TOKEN=your_token_here`
- Or just run the tool — it will prompt you to paste the token on first run and save it to `.env` automatically

---

## Run

```bash
python pm_agent.py
```

The tool will interactively prompt you for:
1. Your Figma token *(only on first run if not in `.env`)*
2. Your Figma design URL

Then it generates 3 problem statements, you pick one, and the PRD is saved and opened in your browser.

### Optional flags

| Flag | Description |
|---|---|
| `--model qwen2.5:14b` | Use a different Ollama model |
| `--out ./docs/prds` | Custom output folder |
| `--goal "text"` | Skip problem selection, use this goal directly |
| `--fast` | Auto-detect goal, skip selection entirely |
| `--no-open` | Don't auto-open HTML in browser |

### `.env` variables (all optional if using interactive prompts)

| Variable | Default | Description |
|---|---|---|
| `FIGMA_ACCESS_TOKEN` | *(prompted)* | Your Figma personal access token |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model to use for PRD generation |

---

## Output

Files are saved to `./output/` (or your custom `--out` folder), named `{feature-slug}-{date}.{ext}`:

```
output/
  onboarding-2026-03-03.md
  onboarding-2026-03-03.json
  onboarding-2026-03-03.html   ← auto-opens in browser
```

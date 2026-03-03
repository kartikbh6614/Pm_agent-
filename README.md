# PM Agent — Figma → PRD Generator

A CLI tool that reads a Figma wireframe and generates a full Product Requirements Document (PRD) using a local Ollama LLM. No cloud dependencies — fully offline after setup.

---

## How It Works

1. **Fetch Figma design** — connects to the Figma REST API and extracts screens, text, components, and interactive elements from the given URL
2. **Generate problem statements** *(skipped in `--fast` mode)* — sends the design context to a local LLM and returns 3 problem statement options (UX / Business / Technical angles)
3. **You pick one** — or provide your own goal via `--goal`
4. **Generate PRD** — the LLM produces a structured PRD with goals, user stories, acceptance criteria, edge cases, and open questions
5. **Save output** — writes `.md`, `.json`, and `.html` files to the output folder

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

## Configuration — Edit Before Running

Create a `.env` file in the project root:

```env
FIGMA_ACCESS_TOKEN=your_figma_token_here
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

| Variable | Required | How to get it |
|---|---|---|
| `FIGMA_ACCESS_TOKEN` | **Yes** | figma.com → Settings → Security → Generate new personal access token |
| `OLLAMA_HOST` | No | Default: `http://localhost:11434` — change if Ollama runs on a different port |
| `OLLAMA_MODEL` | No | Default: `qwen2.5:7b` — any model installed via `ollama pull` works |

---

## Commands

### Basic run (interactive — choose from 3 problem statements)
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2"
```

### Fast run (skip problem selection, auto-detect goal)
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2" --fast
```

### Provide your own goal (skip problem selection)
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2" --goal "Add mobile checkout flow"
```

### Use a bigger model for better output
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2" --model qwen2.5:14b
```

### Custom output folder
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2" --out ./docs/prds
```

### Skip auto-opening HTML in browser
```bash
python pm_agent.py --figma "https://www.figma.com/design/<key>/Name?node-id=1-2" --no-open
```

---

## Output

Files are saved to `./output/` (or your custom `--out` folder), named `{feature-slug}-{date}.{ext}`:

```
output/
  onboarding-2026-03-03.md
  onboarding-2026-03-03.json
  onboarding-2026-03-03.html   ← auto-opens in browser
```

# figprd — Figma → PRD Generator

A fully interactive CLI tool that reads a Figma wireframe and generates a comprehensive, multi-page Product Requirements Document (PRD) using a local Ollama LLM. No cloud dependencies for generation — fully offline after setup.

---

## What It Does

1. **Asks for your Figma token** — only on first run, saved automatically to `.env`
2. **Asks for your Figma URL** — paste any Figma design URL
3. **Fetches the Figma wireframe** — connects to Figma REST API, extracts screens, text, components, and interactive elements
4. **Generates 3 problem statements** — LLM analyses the design and offers 3 angles: UX, Business, Technical
5. **You pick one** — or skip with `--fast` or provide your own via `--goal`
6. **Generates a full PRD** — using the prd-specialist methodology: Executive Summary, Product Overview, Functional Requirements, Non-Functional Requirements, Technical Considerations, Story Breakdown
7. **Saves output** — writes `.md`, `.json`, and `.html` files to `./output/` and auto-opens the HTML in your browser

---

## PRD Structure Generated

| Section | Contents |
|---|---|
| Executive Summary | Overview, Problem Statement, Business Impact, Resource Requirements, Risk Assessment |
| Product Overview | Product Vision, Target Users (personas + JTBD), Value Proposition, Success Criteria, Assumptions |
| Functional Requirements | Goals, User Stories, Business Rules, Integration Points |
| Non-Functional Requirements | Performance, Security, Compliance |
| Technical Considerations | Architecture constraints and technical decisions |
| Quality & Validation | Acceptance Criteria, Edge Cases, Out of Scope, Open Questions |
| Story Breakdown | Detailed user stories each with their own acceptance criteria |

---

## Step-by-Step Setup Guide

### Step 1 — Install Python

Check if Python is already installed:
```powershell
python --version
```

If not installed, download from **https://www.python.org/downloads/** and install.
Make sure to check **"Add Python to PATH"** during installation.

Minimum required version: **Python 3.10+**

---

### Step 2 — Clone or Download the Project

```powershell
git clone https://github.com/kartikbh6614/Pm_agent-.git
cd Pm_agent-
```

Or download the ZIP from GitHub and extract it.

---

### Step 3 — Install Python Dependencies

Navigate to the project folder and install all required packages:

```powershell
cd C:\Users\<your-username>\path\to\Pm_agent
pip install -r requirements.txt
```

This installs the following packages:

| Package | Version | Purpose |
|---|---|---|
| `ollama` | 0.4.4 | Local LLM client — talks to Ollama running on your machine |
| `requests` | 2.32.3 | Figma REST API calls |
| `pydantic` | 2.10.6 | Structured LLM output validation — ensures PRD JSON is correct |
| `rich` | 13.9.4 | Terminal UI — spinners, tables, panels, prompts |
| `python-dotenv` | 1.0.1 | Loads `.env` config file automatically |

---

### Step 4 — Install Ollama

Ollama is the local LLM runtime that powers PRD generation. No internet needed after install.

**Download and install Ollama:**
```powershell
curl.exe -L "https://ollama.com/download/OllamaSetup.exe" -o "$env:TEMP\OllamaSetup.exe"; Start-Process "$env:TEMP\OllamaSetup.exe"
```

Click through the installer. After it finishes, open a **new** PowerShell window and verify:
```powershell
ollama --version
```

You should see a version number like `0.17.7`.

---

### Step 5 — Pull the LLM Model

Download the default model used for PRD generation (~4.7 GB):
```powershell
ollama pull qwen2.5:7b
```

Wait for the download to complete. Ollama will start automatically in the background.

Verify the model is available:
```powershell
ollama list
```

You should see `qwen2.5:7b` in the list.

> **Want better quality output?** Pull a larger model:
> ```powershell
> ollama pull qwen2.5:14b
> ```

---

### Step 6 — Get a Figma Access Token

1. Log in to **figma.com**
2. Click your profile picture (top left) → **Settings**
3. Go to the **Security** tab
4. Scroll to **Personal access tokens** → click **Generate new token**
5. Give it a name (e.g. `figprd`) and copy the token

> Keep this token safe — you only see it once.

The tool will ask for this token on first run and save it automatically to `.env`.

---

### Step 7 — Set Up the `figprd` Command

So you can run `figprd` from any terminal instead of `python pm_agent.py`:

**Open your PowerShell profile:**
```powershell
New-Item -ItemType File -Path $PROFILE -Force
notepad $PROFILE
```

**Add this line in Notepad, save and close:**
```powershell
function figprd { & python "C:\Users\<your-username>\path\to\Pm_agent\pm_agent.py" @args }
```

Replace the path with the actual location of your `pm_agent.py` file.

**Reload the profile:**
```powershell
. $PROFILE
```

> If you get an execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> Then reload the profile again.

---

### Step 8 — Get a Figma Design URL

1. Open any Figma file in your browser
2. Click on a frame or screen you want to analyse
3. Copy the URL from the browser address bar

It should look like:
```
https://www.figma.com/design/ABC123XYZ/My-App?node-id=1-2&t=xxxxx
```

You can also pass the whole file URL without a `node-id` — the tool will scan all frames.

---

### Step 9 — Run the Tool

Simply run:
```powershell
figprd
```

The tool will interactively ask for:
1. Your Figma token *(only on first run — saved after)*
2. Your Figma URL

Then it will automatically:
- Connect to Ollama
- Fetch the Figma wireframe
- Generate 3 problem statements
- Let you pick one
- Generate the full PRD
- Save and open the output

---

## All Available Commands

### Fully interactive (recommended)
```powershell
figprd
```

### Pass Figma URL directly (skip URL prompt)
```powershell
figprd --figma "https://www.figma.com/design/<key>/Name?node-id=1-2"
```

### Provide your own goal (skip problem statement selection)
```powershell
figprd --figma "YOUR_URL" --goal "Add mobile checkout flow"
```

### Fast mode (skip problem selection entirely, auto-detect goal)
```powershell
figprd --figma "YOUR_URL" --fast
```

### Use a bigger model for better PRD quality
```powershell
figprd --figma "YOUR_URL" --model qwen2.5:14b
```

### Save output to a custom folder
```powershell
figprd --figma "YOUR_URL" --out ./docs/prds
```

### Skip auto-opening HTML in browser
```powershell
figprd --figma "YOUR_URL" --no-open
```

---

## Environment Variables

The `.env` file in the project root controls all configuration:

```env
# Required — your Figma personal access token
FIGMA_ACCESS_TOKEN=your_token_here

# Optional — Ollama server address (default: localhost)
OLLAMA_HOST=http://localhost:11434

# Optional — model to use (default: qwen2.5:7b)
OLLAMA_MODEL=qwen2.5:7b
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `FIGMA_ACCESS_TOKEN` | **Yes** | — | Figma personal access token. Tool will prompt and save automatically on first run |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Change if Ollama runs on a different port |
| `OLLAMA_MODEL` | No | `qwen2.5:7b` | Any model pulled via `ollama pull` works |

---

## Output Files

All files are saved to `./output/` (or your `--out` folder), named `{feature-slug}-{date}.{ext}`:

```
output/
  mobile-onboarding-2026-03-10.md     ← Full PRD in Markdown
  mobile-onboarding-2026-03-10.json   ← Structured JSON (for integrations)
  mobile-onboarding-2026-03-10.html   ← Styled HTML report (auto-opens in browser)
```

The HTML report is a fully styled, printable document with collapsible sections and a story breakdown table.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `figprd` not recognized | Run `. $PROFILE` to reload PowerShell profile |
| `Ollama not ready` | Run `ollama serve` in a separate terminal or check system tray |
| `ollama` not recognized | Open a new PowerShell window after installing Ollama |
| `429 Too Many Requests` (Figma) | Tool auto-retries with backoff — wait a moment and try again |
| `Model not found` | Run `ollama pull qwen2.5:7b` |
| `Execution policy error` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `FIGMA_ACCESS_TOKEN not set` | Run `figprd` and paste your token when prompted |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Terminal                            │
│                      figprd (PowerShell)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        pm_agent.py                              │
│                    CLI Entry Point                              │
│                                                                 │
│  1. Prompt for Figma token (save to .env if missing)           │
│  2. Prompt for Figma URL (or accept --figma flag)              │
│  3. Orchestrate steps 1–5 below                                │
│  4. Print summary table to terminal                            │
└────┬──────────────────────────────────────┬────────────────────┘
     │                                      │
     ▼                                      ▼
┌─────────────────────┐          ┌──────────────────────────────┐
│  figma_connector.py │          │       ollama_client.py        │
│  Figma REST API     │          │    Local LLM Interface        │
│                     │          │                               │
│  • Parse URL        │          │  Step 1: check_connection()   │
│  • GET /files       │          │    → verify Ollama is running │
│  • GET /nodes       │          │    → verify model is pulled   │
│  • GET /comments    │          │                               │
│  • Walk component   │          │  Step 2: suggest_problem_     │
│    tree (depth 5)   │          │    statements()               │
│  • Extract text,    │          │    → fast model (1b/3b)       │
│    interactions,    │          │    → returns 3 options        │
│    components       │          │    (UX / Business / Tech)     │
│  • Cache responses  │          │                               │
│    to .figma_cache/ │          │  Step 3: generate_prd()       │
│  • Auto-retry 429s  │          │    → main model (7b/14b)      │
│    with backoff     │          │    → prd-specialist prompt    │
└─────────┬───────────┘          │    → 8000 token output        │
          │                      │    → Pydantic validation      │
          │  design_context      └──────────────┬───────────────┘
          │  (text prompt)                       │
          └──────────────────────────────────────┘
                            │
                            │  PRD object (validated)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         writers.py                              │
│                      Output Generator                           │
│                                                                 │
│   write_markdown()  →  feature-name-date.md                    │
│   write_json()      →  feature-name-date.json                  │
│   write_html()      →  feature-name-date.html                  │
│                         (auto-opens in browser)                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Data Flow Summary                          │
│                                                                 │
│  Figma URL                                                      │
│      → Figma API (REST)                                        │
│          → Raw node tree (JSON)                                 │
│              → Formatted design context (text)                  │
│                  → Ollama LLM (local, qwen2.5:7b)              │
│                      → 3 problem statements → user picks 1      │
│                          → Full PRD JSON (validated)            │
│                              → .md + .json + .html output       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       File Structure                            │
│                                                                 │
│  pm_agent.py              CLI entry point                       │
│  ollama_client.py         LLM calls + Pydantic schemas          │
│  writers.py               .md / .json / .html writers           │
│  connectors/                                                    │
│    figma_connector.py     Figma REST API client                 │
│  .env                     API tokens and config                 │
│  .figma_cache/            Cached Figma responses                │
│  output/                  All generated PRD files               │
│  .claude/agents/                                                │
│    prd-specialist.md      Claude Code subagent definition       │
│  requirements.txt         Python dependencies                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Models Reference

| Model | Size | Speed | Quality | Command |
|---|---|---|---|---|
| `qwen2.5:1.5b` | ~1 GB | Very fast | Basic | `ollama pull qwen2.5:1.5b` |
| `qwen2.5:7b` | ~4.7 GB | Fast | **Good (default)** | `ollama pull qwen2.5:7b` |
| `qwen2.5:14b` | ~9 GB | Medium | Better | `ollama pull qwen2.5:14b` |
| `qwen2.5:32b` | ~20 GB | Slow | Best | `ollama pull qwen2.5:32b` |

Use `--model` flag to switch:
```powershell
figprd --figma "YOUR_URL" --model qwen2.5:14b
```

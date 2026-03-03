# PM Agent — Claude Code Instructions

## Project Overview
A CLI tool that reads Figma wireframes and generates PRDs using a local Ollama LLM.
No cloud dependencies for generation — fully offline after setup.

## Architecture
```
pm_agent.py          → single CLI entry point (argparse + rich UI)
ollama_client.py     → LLM calls, prompt templates, Pydantic output schemas
writers.py           → file writers: .md, .json, .html
connectors/
  figma_connector.py → Figma REST API: parses URLs, extracts wireframe tree
.env                 → FIGMA_ACCESS_TOKEN, OLLAMA_HOST, OLLAMA_MODEL
output/              → all generated files land here (gitignored)
questions.md         → open questions, feature ideas, known issues
```

## How to Run
```bash
pip install -r requirements.txt
python pm_agent.py --figma "<url>" --goal "feature description"
```

## Key Conventions
- **One command only** — `pm_agent.py` is the single entry point, no subcommands
- **No Notion/cloud output** — all output is local files (md, json, html)
- **Ollama model** — default is `qwen2.5:7b`, configurable via `--model` or `.env`
- **Output folder** — default `./output/`, files named `{feature-slug}-{date}.{ext}`
- **Pydantic models** — `PRD` and `UserStory` in `ollama_client.py` define the LLM schema
- **Rich console** — all terminal output uses `rich` library (spinners, tables, panels)
- **No inline comments** — only add comments where logic is non-obvious

## Figma Connector Notes
- Supports both specific frame URLs (`?node-id=1-2`) and whole-file URLs
- Recursively walks component tree up to depth 5
- Collects: all text, interactive elements, component hierarchy, designer comments
- `format_for_prompt()` converts raw data to LLM-readable text

## LLM / Ollama Notes
- Uses `format="json"` in Ollama chat call to enforce JSON output
- Temperature is set low (`0.3`) for consistent structured output
- `num_predict=4096` — do not reduce, PRDs can be long
- If model output fails Pydantic validation, the error surfaces in terminal

## Environment Variables (.env)
| Variable | Required | Default |
|---|---|---|
| FIGMA_ACCESS_TOKEN | Yes | — |
| OLLAMA_HOST | No | http://localhost:11434 |
| OLLAMA_MODEL | No | qwen2.5:7b |

## Do NOT
- Add Notion, Jira, or any cloud output connector (by design)
- Add subcommands — keep it one command
- Auto-commit or push generated files
- Change the output file naming convention without updating all 3 writers

## Check questions.md
Before adding new features or making changes, check `questions.md` for:
- Open questions that need answering first
- Planned features already in the backlog
- Known issues to be aware of

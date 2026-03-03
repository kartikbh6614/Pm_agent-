# Questions, Features & Updates

> This file tracks open questions, feature ideas, improvements, and known issues.
> Add anything here that needs discussion, review, or future implementation.
> Format: use the sections below and add date + status to each item.

---

## Open Questions
*Things that need a decision before implementation*

- [ ] **[2026-03-03]** Should the agent support Figma files without a specific node-id (full file scan)?
      → Currently supported but may generate very large prompts for complex files.

- [ ] **[2026-03-03]** What is the max number of screens we should process per run?
      → Large files with 50+ frames might exceed Ollama's context window.

- [ ] **[2026-03-03]** Should `--goal` be optional? Could the LLM infer the goal from the wireframe alone?

---

## Feature Requests
*New capabilities to add in future versions*

- [ ] **[2026-03-03]** `--lang` flag to generate PRD in different languages (Hindi, Spanish, etc.)

- [ ] **[2026-03-03]** `--template` flag to support custom PRD templates (startup vs enterprise style)

- [ ] **[2026-03-03]** Compare two Figma frames and generate a "what changed" diff PRD

- [ ] **[2026-03-03]** Interactive mode — ask follow-up questions to refine the PRD after first draft

- [ ] **[2026-03-03]** `--watch` mode — monitor a Figma file for changes and re-generate on update

- [ ] **[2026-03-03]** Export to PDF in addition to HTML/MD/JSON

- [ ] **[2026-03-03]** Confidence score — LLM rates how complete the wireframe is for PRD generation

---

## Improvements
*Enhancements to existing functionality*

- [ ] **[2026-03-03]** Better error message when Figma token is invalid (currently shows raw HTTP 403)

- [ ] **[2026-03-03]** Retry logic for Ollama if generation fails (JSON parse error, timeout)

- [ ] **[2026-03-03]** Progress bar should show token count / estimated time remaining

- [ ] **[2026-03-03]** HTML report: add collapsible sections for long AC lists

- [ ] **[2026-03-03]** Truncate very long Figma component trees before sending to LLM

- [ ] **[2026-03-03]** Cache Figma API response locally so re-runs don't hit rate limits

---

## Known Issues
*Bugs or limitations found during testing*

- [ ] **[2026-03-03]** Figma connector depth=6 may be slow for files with deeply nested auto-layouts

- [ ] **[2026-03-03]** `qwen2.5:7b` occasionally outputs trailing text after JSON — need stricter parsing

- [ ] **[2026-03-03]** HTML report does not render on systems where default browser blocks local file URIs

---

## Completed
*Done items — move here when resolved*

- [x] **[2026-03-03]** Remove Notion dependency — switched to local file output (md, json, html)
- [x] **[2026-03-03]** Upgrade Figma connector to read full wireframe (text, interactive elements, comments)
- [x] **[2026-03-03]** Single command CLI — `python pm_agent.py --figma <url> --goal "..."`
- [x] **[2026-03-03]** Auto problem statement suggestions — agent reads design and offers 3 options (UX / Business / Technical angle) for user to pick before generating PRD

---

## Notes / Ideas (Unstructured)
*Raw thoughts — refine into the sections above when ready*

- Could integrate with Git to auto-commit generated PRDs to a docs/ folder
- Could support Miro boards as an alternative to Figma input
- Voice input for `--goal` using whisper.cpp via Ollama

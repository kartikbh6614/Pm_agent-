"""
Output writers - saves PRD as Markdown, JSON, and HTML
"""
import json
from pathlib import Path
from datetime import datetime
from ollama_client import PRD


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-")[:40]


def _dated_name(feature_name: str, ext: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    return f"{_slug(feature_name)}-{date}.{ext}"


def write_markdown(prd: PRD, output_dir: Path, figma_url: str) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    filename = output_dir / _dated_name(prd.feature_name, "md")

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    stories_table = "\n".join(
        f"| {s.title} | {s.priority} | {s.effort} |"
        for s in prd.structured_stories
    )

    content = f"""# PRD: {prd.feature_name}

> **Date:** {date}
> **Status:** Draft
> **Figma:** {figma_url}

---

## Overview

{prd.overview}

---

## Problem Statement

{prd.problem_statement}

---

## Goals

{bullets(prd.goals)}

---

## User Stories

{bullets(prd.user_stories)}

---

## Acceptance Criteria

{bullets(prd.acceptance_criteria)}

---

## Edge Cases

{bullets(prd.edge_cases)}

---

## Out of Scope

{bullets(prd.out_of_scope)}

---

## Open Questions

{bullets(prd.open_questions)}

---

## Story Breakdown

| Story | Priority | Effort |
|-------|----------|--------|
{stories_table}
"""
    filename.write_text(content, encoding="utf-8")
    return filename


def write_json(prd: PRD, output_dir: Path) -> Path:
    filename = output_dir / _dated_name(prd.feature_name, "json")
    data = {
        "feature_name": prd.feature_name,
        "generated_at": datetime.now().isoformat(),
        "stories": [s.model_dump() for s in prd.structured_stories],
        "acceptance_criteria": prd.acceptance_criteria,
        "open_questions": prd.open_questions,
    }
    filename.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return filename


def write_html(prd: PRD, output_dir: Path, figma_url: str) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    filename = output_dir / _dated_name(prd.feature_name, "html")

    def li_items(items: list[str]) -> str:
        return "\n".join(f"        <li>{item}</li>" for item in items)

    priority_badge = {
        "High": "#ef4444",
        "Medium": "#f59e0b",
        "Low": "#22c55e",
    }
    effort_badge = {"S": "#6366f1", "M": "#3b82f6", "L": "#8b5cf6", "XL": "#ec4899"}

    story_rows = "\n".join(
        f"""        <tr>
          <td>{s.title}</td>
          <td><span class="badge" style="background:{priority_badge.get(s.priority,'#888')}">{s.priority}</span></td>
          <td><span class="badge" style="background:{effort_badge.get(s.effort,'#888')}">{s.effort}</span></td>
          <td style="font-size:0.85em;color:#64748b">{s.description}</td>
        </tr>"""
        for s in prd.structured_stories
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PRD: {prd.feature_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
    .container {{ max-width: 900px; margin: 40px auto; padding: 0 24px 80px; }}
    header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border-radius: 16px; padding: 36px 40px; margin-bottom: 32px; }}
    header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
    header .meta {{ opacity: 0.85; font-size: 0.9rem; margin-top: 12px; }}
    header .meta a {{ color: white; }}
    .card {{ background: white; border-radius: 12px; padding: 28px 32px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .card h2 {{ font-size: 1.1rem; color: #6366f1; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card p {{ line-height: 1.7; color: #374151; }}
    .card ul {{ padding-left: 20px; }}
    .card ul li {{ padding: 4px 0; line-height: 1.6; color: #374151; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th {{ text-align: left; padding: 10px 12px; background: #f1f5f9; font-size: 0.85rem; color: #64748b; }}
    td {{ padding: 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; color: white; font-size: 0.78rem; font-weight: 600; }}
    .tag {{ display: inline-block; background: #f1f5f9; color: #475569; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; margin-right: 8px; }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>PRD: {prd.feature_name}</h1>
    <p>{prd.overview}</p>
    <div class="meta">
      <span class="tag" style="background:rgba(255,255,255,0.2);color:white">Draft</span>
      <span class="tag" style="background:rgba(255,255,255,0.2);color:white">{date}</span>
      &nbsp; Figma: <a href="{figma_url}" target="_blank">{figma_url[:60]}...</a>
    </div>
  </header>

  <div class="card">
    <h2>Problem Statement</h2>
    <p>{prd.problem_statement}</p>
  </div>

  <div class="card">
    <h2>Goals</h2>
    <ul>
      {li_items(prd.goals)}
    </ul>
  </div>

  <div class="card">
    <h2>User Stories</h2>
    <ul>
      {li_items(prd.user_stories)}
    </ul>
  </div>

  <div class="card">
    <h2>Acceptance Criteria</h2>
    <ul>
      {li_items(prd.acceptance_criteria)}
    </ul>
  </div>

  <div class="card">
    <h2>Edge Cases</h2>
    <ul>
      {li_items(prd.edge_cases)}
    </ul>
  </div>

  <div class="card">
    <h2>Out of Scope</h2>
    <ul>
      {li_items(prd.out_of_scope)}
    </ul>
  </div>

  <div class="card">
    <h2>Open Questions</h2>
    <ul>
      {li_items(prd.open_questions)}
    </ul>
  </div>

  <div class="card">
    <h2>Story Breakdown</h2>
    <table>
      <thead>
        <tr><th>Story</th><th>Priority</th><th>Effort</th><th>Description</th></tr>
      </thead>
      <tbody>
{story_rows}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>"""
    filename.write_text(html, encoding="utf-8")
    return filename

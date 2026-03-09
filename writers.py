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

    stories_md = ""
    for s in prd.structured_stories:
        ac = "\n".join(f"  - {c}" for c in s.acceptance_criteria)
        stories_md += f"\n### {s.title}\n**Priority:** {s.priority} | **Effort:** {s.effort}\n\n{s.description}\n\n**Acceptance Criteria:**\n{ac}\n"

    content = f"""# PRD: {prd.feature_name}

> **Date:** {date}
> **Status:** Draft
> **Figma:** {figma_url}

---

## Executive Summary

### Overview

{prd.overview}

### Problem Statement

{prd.problem_statement}

### Business Impact

{prd.business_impact}

### Resource Requirements

{prd.resource_requirements}

### Risk Assessment

{prd.risk_assessment}

---

## Product Overview

### Product Vision

{prd.product_vision}

### Target Users

{bullets(prd.target_users)}

### Value Proposition

{prd.value_proposition}

### Success Criteria

{bullets(prd.success_criteria)}

### Assumptions

{bullets(prd.assumptions)}

---

## Functional Requirements

### Goals

{bullets(prd.goals)}

### User Stories

{bullets(prd.user_stories)}

### Business Rules

{bullets(prd.business_rules)}

### Integration Points

{bullets(prd.integration_points)}

---

## Non-Functional Requirements

### Performance

{bullets(prd.performance_requirements)}

### Security

{bullets(prd.security_requirements)}

### Compliance

{bullets(prd.compliance_requirements)}

---

## Technical Considerations

{bullets(prd.technical_considerations)}

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
{"".join(f"| {s.title} | {s.priority} | {s.effort} |{chr(10)}" for s in prd.structured_stories)}

---

## Detailed User Stories
{stories_md}
"""
    filename.write_text(content, encoding="utf-8")
    return filename


def write_json(prd: PRD, output_dir: Path) -> Path:
    filename = output_dir / _dated_name(prd.feature_name, "json")
    data = {
        "feature_name": prd.feature_name,
        "generated_at": datetime.now().isoformat(),
        "executive_summary": {
            "overview": prd.overview,
            "problem_statement": prd.problem_statement,
            "business_impact": prd.business_impact,
            "resource_requirements": prd.resource_requirements,
            "risk_assessment": prd.risk_assessment,
        },
        "product_overview": {
            "product_vision": prd.product_vision,
            "target_users": prd.target_users,
            "value_proposition": prd.value_proposition,
            "success_criteria": prd.success_criteria,
            "assumptions": prd.assumptions,
        },
        "functional_requirements": {
            "goals": prd.goals,
            "user_stories": prd.user_stories,
            "business_rules": prd.business_rules,
            "integration_points": prd.integration_points,
        },
        "non_functional_requirements": {
            "performance": prd.performance_requirements,
            "security": prd.security_requirements,
            "compliance": prd.compliance_requirements,
        },
        "technical_considerations": prd.technical_considerations,
        "acceptance_criteria": prd.acceptance_criteria,
        "edge_cases": prd.edge_cases,
        "out_of_scope": prd.out_of_scope,
        "open_questions": prd.open_questions,
        "structured_stories": [s.model_dump() for s in prd.structured_stories],
    }
    filename.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return filename


def write_html(prd: PRD, output_dir: Path, figma_url: str) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    filename = output_dir / _dated_name(prd.feature_name, "html")

    def li_items(items: list[str]) -> str:
        return "\n".join(f"        <li>{item}</li>" for item in items)

    priority_badge = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
    effort_badge = {"S": "#6366f1", "M": "#3b82f6", "L": "#8b5cf6", "XL": "#ec4899"}

    story_rows = "\n".join(
        f"""        <tr>
          <td><strong>{s.title}</strong><br><small style="color:#64748b">{s.description}</small></td>
          <td><span class="badge" style="background:{priority_badge.get(s.priority,'#888')}">{s.priority}</span></td>
          <td><span class="badge" style="background:{effort_badge.get(s.effort,'#888')}">{s.effort}</span></td>
          <td><ul style="padding-left:16px">{"".join(f"<li style='font-size:0.82em;color:#475569'>{c}</li>" for c in s.acceptance_criteria)}</ul></td>
        </tr>"""
        for s in prd.structured_stories
    )

    def section(title: str, items: list[str]) -> str:
        return f"""  <div class="card">
    <h2>{title}</h2>
    <ul>
      {li_items(items)}
    </ul>
  </div>"""

    def text_card(title: str, content: str) -> str:
        return f"""  <div class="card">
    <h2>{title}</h2>
    <p>{content}</p>
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PRD: {prd.feature_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
    .container {{ max-width: 960px; margin: 40px auto; padding: 0 24px 80px; }}
    header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border-radius: 16px; padding: 36px 40px; margin-bottom: 32px; }}
    header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
    header .vision {{ font-size: 1.05rem; opacity: 0.9; margin: 12px 0 8px; font-style: italic; }}
    header .meta {{ opacity: 0.8; font-size: 0.85rem; margin-top: 12px; }}
    header .meta a {{ color: white; }}
    .section-title {{ font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; margin: 32px 0 12px; }}
    .card {{ background: white; border-radius: 12px; padding: 28px 32px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .card h2 {{ font-size: 1rem; color: #6366f1; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card p {{ line-height: 1.75; color: #374151; }}
    .card ul {{ padding-left: 20px; }}
    .card ul li {{ padding: 5px 0; line-height: 1.6; color: #374151; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th {{ text-align: left; padding: 10px 12px; background: #f1f5f9; font-size: 0.82rem; color: #64748b; }}
    td {{ padding: 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; color: white; font-size: 0.78rem; font-weight: 600; }}
    .tag {{ display: inline-block; background: rgba(255,255,255,0.2); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; margin-right: 8px; }}
  </style>
</head>
<body>
<div class="container">

  <header>
    <h1>PRD: {prd.feature_name}</h1>
    <p class="vision">{prd.product_vision}</p>
    <div class="meta">
      <span class="tag">Draft</span>
      <span class="tag">{date}</span>
      &nbsp; Figma: <a href="{figma_url}" target="_blank">{figma_url[:70]}...</a>
    </div>
  </header>

  <div class="section-title">Executive Summary</div>
  {text_card("Overview", prd.overview)}
  {text_card("Problem Statement", prd.problem_statement)}
  <div class="grid-2">
    {text_card("Business Impact", prd.business_impact)}
    {text_card("Risk Assessment", prd.risk_assessment)}
  </div>
  {text_card("Resource Requirements", prd.resource_requirements)}

  <div class="section-title">Product Overview</div>
  {text_card("Value Proposition", prd.value_proposition)}
  <div class="grid-2">
    {section("Target Users", prd.target_users)}
    {section("Success Criteria", prd.success_criteria)}
  </div>
  {section("Assumptions", prd.assumptions)}

  <div class="section-title">Functional Requirements</div>
  {section("Goals", prd.goals)}
  {section("User Stories", prd.user_stories)}
  <div class="grid-2">
    {section("Business Rules", prd.business_rules)}
    {section("Integration Points", prd.integration_points)}
  </div>

  <div class="section-title">Non-Functional Requirements</div>
  <div class="grid-2">
    {section("Performance", prd.performance_requirements)}
    {section("Security", prd.security_requirements)}
  </div>
  {section("Compliance", prd.compliance_requirements)}

  <div class="section-title">Technical Considerations</div>
  {section("Technical Considerations", prd.technical_considerations)}

  <div class="section-title">Quality & Validation</div>
  {section("Acceptance Criteria", prd.acceptance_criteria)}
  {section("Edge Cases", prd.edge_cases)}
  <div class="grid-2">
    {section("Out of Scope", prd.out_of_scope)}
    {section("Open Questions", prd.open_questions)}
  </div>

  <div class="section-title">Story Breakdown</div>
  <div class="card">
    <h2>Detailed User Stories</h2>
    <table>
      <thead>
        <tr><th>Story</th><th>Priority</th><th>Effort</th><th>Acceptance Criteria</th></tr>
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

"""
Ollama Client - handles LLM calls with structured JSON output
"""
import json
import ollama
from pydantic import BaseModel


class UserStory(BaseModel):
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: str  # High / Medium / Low
    effort: str    # S / M / L / XL


class PRD(BaseModel):
    feature_name: str

    # Executive Summary
    overview: str
    problem_statement: str
    business_impact: str
    resource_requirements: str
    risk_assessment: str

    # Product Overview
    product_vision: str
    target_users: list[str]
    value_proposition: str
    success_criteria: list[str]
    assumptions: list[str]

    # Functional Requirements
    goals: list[str]
    user_stories: list[str]
    business_rules: list[str]
    integration_points: list[str]

    # Non-Functional Requirements
    performance_requirements: list[str]
    security_requirements: list[str]
    compliance_requirements: list[str]

    # Technical Considerations
    technical_considerations: list[str]

    # Standard fields
    acceptance_criteria: list[str]
    edge_cases: list[str]
    out_of_scope: list[str]
    open_questions: list[str]
    structured_stories: list[UserStory]


class ProblemOption(BaseModel):
    title: str        # short label shown to user e.g. "AI Discovery Flow"
    angle: str        # perspective e.g. "UX", "Business", "Technical"
    statement: str    # full one-paragraph problem statement


class ProblemSuggestions(BaseModel):
    suggestions: list[ProblemOption]


# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = "You are a Product Manager. Output valid JSON only. Be concise."

_SUGGEST_TEMPLATE = """Figma design context:
{design_context}

Return JSON with exactly 3 problem statements (UX, Business, Technical angles):
{{"suggestions":[{{"title":"3-5 words","angle":"UX","statement":"2 sentences"}},{{"title":"3-5 words","angle":"Business","statement":"2 sentences"}},{{"title":"3-5 words","angle":"Technical","statement":"2 sentences"}}]}}"""

_PRD_TEMPLATE = """You are a leading Product Requirements Document specialist combining advanced product management methodologies, technical architecture expertise, and business strategy.

Using the prd-specialist methodology, generate a comprehensive, detailed PRD that covers all sections thoroughly — this must be a professional document of at least 3 pages.

DESIGN CONTEXT:
{design_context}

Problem: {feature_goal}

Instructions per field:
- overview: 5-7 sentence executive summary covering background, context, and strategic importance
- problem_statement: 3-4 sentences on user pain point and business impact
- business_impact: quantified business value, ROI model, and alignment with OKRs (3-4 sentences)
- resource_requirements: teams, tools, timeline estimates needed (2-3 sentences)
- risk_assessment: top risks and mitigation strategies (3-4 sentences)
- product_vision: inspiring 1-2 sentence vision statement
- target_users: at least 3 detailed user personas with Jobs-to-Be-Done
- value_proposition: clear differentiated value for each persona (2-3 sentences)
- success_criteria: at least 5 measurable KPIs with target values
- assumptions: at least 4 assumptions the PRD is built on
- goals: at least 6 specific measurable goals using RICE scoring context
- user_stories: at least 8 stories covering different personas — "As a [persona], I want [feature], so that [value]"
- business_rules: at least 4 business logic rules the feature must follow
- integration_points: at least 3 system integrations or API dependencies
- performance_requirements: at least 3 non-functional performance requirements
- security_requirements: at least 3 security and compliance requirements
- compliance_requirements: at least 2 regulatory or legal requirements
- technical_considerations: at least 4 architecture or technical constraints
- acceptance_criteria: at least 10 Given/When/Then criteria covering happy paths and edge cases
- edge_cases: at least 8 edge cases with handling strategy
- out_of_scope: at least 5 items with reasons for exclusion
- open_questions: at least 6 questions with context on why each matters
- structured_stories: at least 6 detailed stories with per-story acceptance criteria

Return ONLY this JSON structure, no other text:
{{
  "feature_name": "short slug name",
  "overview": "...",
  "problem_statement": "...",
  "business_impact": "...",
  "resource_requirements": "...",
  "risk_assessment": "...",
  "product_vision": "...",
  "target_users": ["Persona 1: description and JTBD", "Persona 2: ...", "Persona 3: ..."],
  "value_proposition": "...",
  "success_criteria": ["KPI 1 with target", "KPI 2 with target"],
  "assumptions": ["assumption 1", "assumption 2"],
  "goals": ["goal 1", "goal 2", "goal 3", "goal 4", "goal 5", "goal 6"],
  "user_stories": ["As a ..., I want ..., so that ..."],
  "business_rules": ["rule 1", "rule 2", "rule 3", "rule 4"],
  "integration_points": ["integration 1", "integration 2", "integration 3"],
  "performance_requirements": ["requirement 1", "requirement 2", "requirement 3"],
  "security_requirements": ["requirement 1", "requirement 2", "requirement 3"],
  "compliance_requirements": ["requirement 1", "requirement 2"],
  "technical_considerations": ["consideration 1", "consideration 2", "consideration 3", "consideration 4"],
  "acceptance_criteria": ["Given ..., When ..., Then ..."],
  "edge_cases": ["edge case and handling strategy"],
  "out_of_scope": ["item and reason"],
  "open_questions": ["question and why it matters?"],
  "structured_stories": [
    {{
      "title": "story title",
      "description": "full user story with workflow steps and expected outcome",
      "acceptance_criteria": ["Given ..., When ..., Then ..."],
      "priority": "High",
      "effort": "M"
    }}
  ]
}}"""


# ── Client ────────────────────────────────────────────────────────────────────

class OllamaClient:
    # Preferred models ordered fastest → most capable
    PREFERRED = ["qwen2.5:1.5b", "llama3.2:1b", "llama3.2:3b", "phi3:mini",
                 "qwen2.5:3b", "qwen2.5:7b", "llama3.2:8b"]

    def __init__(self, host: str = "http://localhost:11434", model: str | None = None):
        self.client = ollama.Client(host=host)
        self._requested_model = model  # None means auto-detect
        self.model: str = ""           # resolved in check_connection

    def _available_models(self) -> list[str]:
        return [m.model for m in self.client.list().models]

    def _pick_model(self, available: list[str]) -> str:
        """Return the best model: use requested if available, else fastest installed."""
        if self._requested_model:
            if any(self._requested_model in m for m in available):
                return self._requested_model
        for candidate in self.PREFERRED:
            if any(candidate in m for m in available):
                return candidate
        return available[0]

    def check_connection(self) -> tuple[bool, str]:
        """Returns (is_ready, message). Also resolves self.model."""
        try:
            available = self._available_models()
            if not available:
                return False, "No models found. Run: ollama pull qwen2.5:1.5b"
            self.model = self._pick_model(available)
            return True, f"Ready — using {self.model}"
        except Exception:
            return False, "Ollama not running. Start it from the system tray or run: ollama serve"

    def suggest_problem_statements(self, design_context: str) -> ProblemSuggestions:
        prompt = _SUGGEST_TEMPLATE.format(design_context=design_context)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.4, "num_predict": 350},
        )
        data = json.loads(response.message.content)
        return ProblemSuggestions(**data)

    def generate_prd(self, design_context: str, feature_goal: str) -> PRD:
        """Generate a full PRD given design context and a chosen problem statement."""
        prompt = _PRD_TEMPLATE.format(
            design_context=design_context,
            feature_goal=feature_goal,
        )
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.3, "num_predict": 8000},
        )
        data = json.loads(response.message.content)
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)

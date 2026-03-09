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

_SYSTEM = """You are an expert Product Manager. Your output must always be
valid JSON matching the schema exactly. Be specific and actionable."""

_SUGGEST_TEMPLATE = """You are analyzing a Figma wireframe/design.
Based on the UI structure below, generate exactly 3 distinct problem statements
that a Product Manager could use as the foundation for a PRD.

Each should approach the product from a different angle:
  1. UX angle     — focused on user pain points and experience gaps
  2. Business angle — focused on business value, retention, or conversion
  3. Technical angle — focused on scalability, data, or AI/ML opportunity

DESIGN CONTEXT:
{design_context}

Return ONLY this JSON, no other text:
{{
  "suggestions": [
    {{
      "title": "short feature name (3-5 words)",
      "angle": "UX",
      "statement": "2-3 sentence problem statement from the UX perspective"
    }},
    {{
      "title": "short feature name (3-5 words)",
      "angle": "Business",
      "statement": "2-3 sentence problem statement from the business perspective"
    }},
    {{
      "title": "short feature name (3-5 words)",
      "angle": "Technical",
      "statement": "2-3 sentence problem statement from the technical perspective"
    }}
  ]
}}"""

_PRD_TEMPLATE = """You are a leading Product Requirements Document specialist combining advanced product management methodologies, technical architecture expertise, and business strategy.

Using the prd-specialist methodology, generate a comprehensive, detailed PRD that covers all sections thoroughly — this must be a professional document of at least 3 pages.

DESIGN CONTEXT:
{design_context}

CHOSEN PROBLEM STATEMENT:
{feature_goal}

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
    # Fast model for quick suggestions, full model for deep PRD generation
    FAST_MODELS = ["llama3.2:1b", "llama3.2:3b", "qwen2.5:1.5b", "phi3:mini"]

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.client = ollama.Client(host=host)
        self.model = model
        self._fast_model: str | None = None  # resolved at runtime

    def _available_models(self) -> list[str]:
        return [m.model for m in self.client.list().models]

    def _resolve_fast_model(self) -> str:
        """Pick the fastest available model for the suggestion step."""
        if self._fast_model:
            return self._fast_model
        available = self._available_models()
        for candidate in self.FAST_MODELS:
            if any(candidate in m for m in available):
                self._fast_model = candidate
                return candidate
        # Fall back to the main model if nothing faster is installed
        self._fast_model = self.model
        return self.model

    def check_connection(self) -> tuple[bool, str]:
        """Returns (is_ready, message)."""
        try:
            available = self._available_models()
            if not available:
                return False, "Ollama is running but no models found. Run: ollama pull qwen2.5:7b"
            if not any(self.model in m for m in available):
                return False, f"Model '{self.model}' not found. Available: {', '.join(available)}"
            fast = self._resolve_fast_model()
            extra = f"  |  fast model: {fast}" if fast != self.model else ""
            return True, f"Ready ({self.model}{extra})"
        except Exception:
            return False, "Ollama is not running. Start it from the system tray or run: ollama serve"

    def suggest_problem_statements(self, design_context: str) -> ProblemSuggestions:
        """Analyse the design and return 3 problem statement options (uses fast model)."""
        fast = self._resolve_fast_model()
        prompt = _SUGGEST_TEMPLATE.format(design_context=design_context)
        response = self.client.chat(
            model=fast,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.5, "num_predict": 512},
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

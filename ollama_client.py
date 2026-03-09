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

Return JSON with exactly 7 problem statements covering these angles: UX, Business, Technical, Growth, Accessibility, Performance, Security.
{{"suggestions":[
  {{"title":"3-5 words","angle":"UX","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Business","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Technical","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Growth","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Accessibility","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Performance","statement":"2 sentences"}},
  {{"title":"3-5 words","angle":"Security","statement":"2 sentences"}}
]}}"""

_PRD_TEMPLATE = """Generate a detailed PRD as JSON. Be specific and thorough in every field.

DESIGN: {design_context}
PROBLEM: {feature_goal}

Return ONLY this JSON:
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
    # Preferred models for full PRD generation ordered fastest → most capable
    PREFERRED = ["qwen2.5:1.5b", "llama3.2:1b", "llama3.2:3b", "phi3:mini",
                 "qwen2.5:3b", "qwen2.5:7b", "llama3.2:8b"]

    # Fast small models preferred for quick suggestion step
    FAST_MODELS = ["qwen2.5:1.5b", "llama3.2:1b", "llama3.2:3b", "phi3:mini", "qwen2.5:3b"]

    def __init__(self, host: str = "http://localhost:11434", model: str | None = None):
        self.client = ollama.Client(host=host)
        self._requested_model = model  # None means auto-detect
        self.model: str = ""           # resolved in check_connection
        self._fast_model: str = ""     # resolved in check_connection

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

    def _resolve_fast_model(self) -> str:
        """Return fastest available model for the suggestion step."""
        return self._fast_model or self.model

    def check_connection(self) -> tuple[bool, str]:
        """Returns (is_ready, message). Also resolves self.model and self._fast_model."""
        try:
            available = self._available_models()
            if not available:
                return False, "No models found. Run: ollama pull qwen2.5:7b"
            self.model = self._pick_model(available)
            for candidate in self.FAST_MODELS:
                if any(candidate in m for m in available):
                    self._fast_model = candidate
                    break
            if not self._fast_model:
                self._fast_model = self.model
            extra = f"  |  fast: {self._fast_model}" if self._fast_model != self.model else ""
            return True, f"Ready — using {self.model}{extra}"
        except Exception:
            return False, "Ollama not running. Start it from the system tray or run: ollama serve"

    def suggest_problem_statements(self, design_context: str) -> ProblemSuggestions:
        prompt = _SUGGEST_TEMPLATE.format(design_context=design_context)
        fast = self._resolve_fast_model()
        response = self.client.chat(
            model=fast,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.4, "num_predict": 900},
        )
        data = json.loads(response.message.content)
        return ProblemSuggestions(**data)

    def generate_prd(self, design_context: str, feature_goal: str, on_token=None) -> PRD:
        """Generate a full PRD. Streams tokens and calls on_token(count) for progress updates."""
        prompt = _PRD_TEMPLATE.format(
            design_context=design_context,
            feature_goal=feature_goal,
        )
        chunks = []
        token_count = 0
        for chunk in self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.3, "num_predict": 2500},
            stream=True,
        ):
            token = chunk.message.content
            chunks.append(token)
            token_count += 1
            if on_token and token_count % 50 == 0:
                on_token(token_count)

        data = json.loads("".join(chunks))
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)

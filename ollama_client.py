"""
Ollama Client - handles LLM calls with structured JSON output
"""
import json
import ollama
from pydantic import BaseModel


class UserStory(BaseModel):
    title: str
    description: str
    priority: str  # High / Medium / Low
    effort: str    # S / M / L / XL


class PRD(BaseModel):
    feature_name: str
    overview: str
    problem_statement: str
    goals: list[str]
    user_stories: list[str]
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

_PRD_TEMPLATE = """Analyze this Figma UI design and generate a complete PRD.

DESIGN CONTEXT:
{design_context}

CHOSEN PROBLEM STATEMENT:
{feature_goal}

Return ONLY this JSON structure, no other text:
{{
  "feature_name": "short slug name",
  "overview": "2-3 sentence executive summary",
  "problem_statement": "what user problem this solves",
  "goals": ["goal 1", "goal 2", "goal 3"],
  "user_stories": [
    "As a [persona], I want [feature], so that [value]"
  ],
  "acceptance_criteria": [
    "Given [context], When [action], Then [outcome]"
  ],
  "edge_cases": ["edge case 1", "edge case 2"],
  "out_of_scope": ["not in this release: item 1"],
  "open_questions": ["question 1?"],
  "structured_stories": [
    {{
      "title": "short story title",
      "description": "full user story text",
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
        fast = self._resolve_fast_model()
        prompt = _PRD_TEMPLATE.format(
            design_context=design_context,
            feature_goal=feature_goal,
        )
        response = self.client.chat(
            model=fast,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.3, "num_predict": 1500},
        )
        data = json.loads(response.message.content)
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)

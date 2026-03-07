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

_SYSTEM = "You are a Product Manager. Output valid JSON only. Be concise."

_SUGGEST_TEMPLATE = """Figma design context:
{design_context}

Return JSON with exactly 3 problem statements (UX, Business, Technical angles):
{{"suggestions":[{{"title":"3-5 words","angle":"UX","statement":"2 sentences"}},{{"title":"3-5 words","angle":"Business","statement":"2 sentences"}},{{"title":"3-5 words","angle":"Technical","statement":"2 sentences"}}]}}"""

_PRD_TEMPLATE = """Figma design:
{design_context}

Problem: {feature_goal}

Return JSON:
{{"feature_name":"slug","overview":"2 sentences","problem_statement":"1 sentence","goals":["g1","g2","g3"],"user_stories":["As a X, I want Y, so that Z"],"acceptance_criteria":["Given X When Y Then Z"],"edge_cases":["e1","e2"],"out_of_scope":["item1"],"open_questions":["q1?"],"structured_stories":[{{"title":"t","description":"d","priority":"High","effort":"M"}}]}}"""


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
            options={"temperature": 0.3, "num_predict": 1200},
        )
        data = json.loads(response.message.content)
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)

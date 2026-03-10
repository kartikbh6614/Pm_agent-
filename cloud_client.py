"""
Cloud LLM Client - free tier providers as drop-in for Ollama.

Priority (first key found wins): Cerebras > Gemini > Groq > OpenRouter

Add ONE to .env:
  CEREBRAS_API_KEY   → inference.cerebras.ai  (~2000 tok/s, fastest)
  GEMINI_API_KEY     → aistudio.google.com    (Google login, free)
  GROQ_API_KEY       → console.groq.com       (~500 tok/s, free)
  OPENROUTER_API_KEY → openrouter.ai          (free models)
"""
import requests
from ollama_client import (
    PRD, UserStory, ProblemSuggestions,
    _SYSTEM, _SUGGEST_TEMPLATE, _PRD_TEMPLATE, _extract_json,
)

_PROVIDERS = {
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1/chat/completions",
        "models_url": "https://api.cerebras.ai/v1/models",
        "prd_model": "llama-3.3-70b",
        "fast_model": "llama-3.1-8b",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "models_url": "https://api.groq.com/openai/v1/models",
        "prd_model": "llama-3.3-70b-versatile",
        "fast_model": "llama-3.1-8b-instant",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models_url": "https://openrouter.ai/api/v1/models",
        "prd_model": "meta-llama/llama-3.1-8b-instruct:free",
        "fast_model": "meta-llama/llama-3.2-3b-instruct:free",
    },
}


class CloudClient:
    def __init__(self, provider: str, api_key: str):
        self._provider = provider
        self._api_key = api_key
        self._cfg = _PROVIDERS[provider]
        self.model = self._cfg["prd_model"]
        self._fast_model = self._cfg["fast_model"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _chat(self, model: str, messages: list, max_tokens: int, temperature: float) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(
            self._cfg["base_url"], headers=self._headers(), json=payload, timeout=120
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def check_connection(self) -> tuple[bool, str]:
        try:
            resp = requests.get(
                self._cfg["models_url"], headers=self._headers(), timeout=10
            )
            resp.raise_for_status()
            return True, f"Ready — {self._provider} | prd: {self.model}  |  fast: {self._fast_model}"
        except Exception as e:
            return False, f"{self._provider} connection failed: {e}"

    def suggest_problem_statements(self, design_context: str) -> ProblemSuggestions:
        prompt = _SUGGEST_TEMPLATE.format(design_context=design_context)
        content = self._chat(
            model=self._fast_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=350,
            temperature=0.3,
        )
        return ProblemSuggestions(**_extract_json(content))

    def generate_prd(self, design_context: str, feature_goal: str, on_token=None) -> PRD:
        prompt = _PRD_TEMPLATE.format(
            design_context=design_context,
            feature_goal=feature_goal,
        )
        content = self._chat(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=3500,
            temperature=0.2,
        )
        if on_token:
            on_token(len(content.split()))
        data = _extract_json(content)
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)


class GeminiClient:
    """Google Gemini — free at aistudio.google.com"""
    _BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    _PRD_MODEL = "gemini-1.5-flash"
    _FAST_MODEL = "gemini-1.5-flash-8b"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self.model = self._PRD_MODEL
        self._fast_model = self._FAST_MODEL

    def _url(self, model: str) -> str:
        return f"{self._BASE}/{model}:generateContent?key={self._api_key}"

    def _chat(self, model: str, user: str, max_tokens: int, temperature: float) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        resp = requests.post(self._url(model), json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    def check_connection(self) -> tuple[bool, str]:
        try:
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={self._api_key}",
                timeout=10,
            )
            resp.raise_for_status()
            return True, f"Ready — gemini | prd: {self._PRD_MODEL}  |  fast: {self._FAST_MODEL}"
        except Exception as e:
            return False, f"Gemini connection failed: {e}"

    def suggest_problem_statements(self, design_context: str) -> ProblemSuggestions:
        prompt = _SUGGEST_TEMPLATE.format(design_context=design_context)
        content = self._chat(self._FAST_MODEL, prompt, 350, 0.3)
        return ProblemSuggestions(**_extract_json(content))

    def generate_prd(self, design_context: str, feature_goal: str, on_token=None) -> PRD:
        prompt = _PRD_TEMPLATE.format(design_context=design_context, feature_goal=feature_goal)
        content = self._chat(self._PRD_MODEL, prompt, 3500, 0.2)
        if on_token:
            on_token(len(content.split()))
        data = _extract_json(content)
        data["structured_stories"] = [
            UserStory(**s) for s in data.get("structured_stories", [])
        ]
        return PRD(**data)


def build_cloud_client(env: dict):
    """Return first available cloud client based on env keys. None = fall back to Ollama."""
    if env.get("CEREBRAS_API_KEY"):
        return CloudClient("cerebras", env["CEREBRAS_API_KEY"])
    if env.get("GEMINI_API_KEY"):
        return GeminiClient(env["GEMINI_API_KEY"])
    if env.get("GROQ_API_KEY"):
        return CloudClient("groq", env["GROQ_API_KEY"])
    if env.get("OPENROUTER_API_KEY"):
        return CloudClient("openrouter", env["OPENROUTER_API_KEY"])
    return None

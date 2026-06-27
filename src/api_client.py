"""OpenRouter API client.

The model catalog endpoint is public (no auth), so the dashboard can refresh
itself from a GitHub Actions cron without any secret.
"""
from __future__ import annotations

import requests

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


class OpenRouterClient:
    """Minimal client for the OpenRouter public model catalog."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def get_models(self) -> list[dict]:
        """Return the raw list of model dicts from OpenRouter.

        Each item includes: id, name, context_length, pricing
        (prompt/completion per token, as strings), architecture,
        top_provider, created (unix seconds), knowledge_cutoff, etc.
        """
        resp = requests.get(
            OPENROUTER_MODELS_URL,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not isinstance(data, list) or not data:
            raise ValueError("OpenRouter returned no models")
        return data


if __name__ == "__main__":  # quick smoke test
    models = OpenRouterClient().get_models()
    print(f"Fetched {len(models)} models")
    print("Sample keys:", sorted(models[0].keys()))

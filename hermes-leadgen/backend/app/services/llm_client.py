"""Minimal OpenAI-compatible chat client (works with Ollama's /v1 endpoint
or any OpenAI-compatible provider). Returns None if no provider is
configured, so every caller must have a deterministic fallback — the MVP
runs fully without any AI provider.
"""
from __future__ import annotations

import requests

from app.core.config import get_settings


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.openai_base_url)


def chat_completion(*, system_prompt: str, user_content: str, max_tokens: int = 600) -> str | None:
    settings = get_settings()
    if not settings.openai_base_url:
        return None

    headers = {"Content-Type": "application/json"}
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"

    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

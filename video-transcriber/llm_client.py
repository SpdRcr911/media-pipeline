"""Shared LLM backend dispatcher.

Routes a single completion call to OpenRouter (when OPENROUTER_API_KEY is set)
or local Ollama (default). Used by both summarize.py and publish.py.
"""

import os

import requests

DEFAULT_OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_OLLAMA_MODEL = "llama3"
DEFAULT_OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
REQUEST_TIMEOUT_SECONDS = 600


def complete(prompt: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
    """Send `prompt` to the active backend and return the response text.

    Raises `requests.exceptions.RequestException` on transport/HTTP errors.
    """
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if openrouter_key:
        model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        print(f"  -> OpenRouter ({model})")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        print(f"  -> Ollama ({model}) at {url}")
        headers = {}
        payload = {"model": model, "prompt": prompt, "stream": False}

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()

    if openrouter_key:
        return response.json()["choices"][0]["message"]["content"]
    return response.json().get("response", "")

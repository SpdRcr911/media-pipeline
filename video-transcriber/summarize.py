import os
import sys

import requests

DEFAULT_OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_OLLAMA_MODEL = "llama3"
DEFAULT_OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
REQUEST_TIMEOUT_SECONDS = 600  # long transcripts on local Ollama can take minutes


def summarize_transcript(file_path: str) -> bool:
    """Summarize the transcript at `file_path`. Returns True on success."""
    if not os.path.exists(file_path):
        print(f"Error: Transcript not found at {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    print("\nInitiating summarization...")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    prompt_text = (
        "Please provide a concise summary, followed by a bulleted list of the main takeaways, "
        f"for the following video transcript:\n\n{transcript_text}"
    )

    if openrouter_key:
        model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        print(f"Using OpenRouter (Cloud) with model '{model}'...")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
        }
    else:
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        print(f"Using local Ollama with model '{model}'...")
        url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        headers = {}
        payload = {"model": model, "prompt": prompt_text, "stream": False}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return False

    if openrouter_key:
        summary = response.json()["choices"][0]["message"]["content"]
    else:
        summary = response.json().get("response", "")

    summary_file = os.path.splitext(file_path)[0] + "_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Summary generated successfully! Saved to: {summary_file}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python summarize.py <path_to_transcript>")
        sys.exit(1)
    sys.exit(0 if summarize_transcript(sys.argv[1]) else 1)

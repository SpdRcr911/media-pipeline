import os
import sys

import requests

import llm_client

PROMPT_TEMPLATE = (
    "Please provide a concise summary, followed by a bulleted list of the main takeaways, "
    "for the following video transcript:\n\n{transcript}"
)


def summarize_transcript(file_path: str) -> bool:
    """Summarize the transcript at `file_path`. Returns True on success."""
    if not os.path.exists(file_path):
        print(f"Error: Transcript not found at {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    print("\nInitiating summarization...")
    try:
        summary = llm_client.complete(PROMPT_TEMPLATE.format(transcript=transcript_text))
    except requests.exceptions.RequestException as e:
        print(f"Summary API request failed: {e}")
        return False

    summary_file = os.path.splitext(file_path)[0] + "_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Summary saved to: {summary_file}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python summarize.py <path_to_transcript>")
        sys.exit(1)
    sys.exit(0 if summarize_transcript(sys.argv[1]) else 1)

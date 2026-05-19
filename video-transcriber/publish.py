"""Generate a publishable, high-fidelity clean-read version of a transcript.

Strips filler/disfluency and fixes obvious grammar errors while preserving the
speaker's voice, vocabulary, and meaning. Output goes to `{name}_publishable.txt`.
"""

import os
import re
import sys

import requests

import llm_client

TIMESTAMP_PATTERN = re.compile(r"^\[\d+(?:\.\d+)?s -> \d+(?:\.\d+)?s\]\s*", re.MULTILINE)

PROMPT_TEMPLATE = """You are editing a verbatim speech transcript into a publishable, easy-to-read version while preserving the speaker's voice with high fidelity.

Rules:
1. Remove filler disfluencies: "um", "uh", "ah", "er", and "like"/"you know"/"I mean" ONLY when used as filler (not when they carry meaning).
2. Collapse false starts and self-corrections: "I went to the- I went to the store" -> "I went to the store".
3. Remove repeated stutter words when clearly unintentional: "the the store" -> "the store".
4. Add appropriate punctuation and paragraph breaks based on natural speech rhythm.
5. Correct ONLY obvious unintentional grammatical errors (dropped articles, subject-verb mismatches the speaker did not intend).
6. PRESERVE the speaker's vocabulary, idioms, colloquialisms, sentence rhythm, contractions, asides, anecdotes, opinions, and any phrasing that is part of how they speak. These are their voice — do not normalize them.
7. NEVER paraphrase. NEVER rewrite for style. NEVER "improve" wording.
8. NEVER add content not present in the transcript. Do not invent transitions, attributions, headings, or context.
9. NEVER remove substantive content, even if it seems redundant, off-topic, or tangential. Only remove disfluencies.
10. NEVER change meaning. If a sentence is ambiguous in the original, preserve the ambiguity.

Output ONLY the cleaned transcript text. No preamble, no notes, no headings, no markdown.

Transcript:
{transcript}"""


def strip_timestamps(text: str) -> str:
    return TIMESTAMP_PATTERN.sub("", text)


def publish_transcript(file_path: str) -> bool:
    """Produce a publishable version of the transcript at `file_path`."""
    if not os.path.exists(file_path):
        print(f"Error: Transcript not found at {file_path}")
        return False

    output_file = os.path.splitext(file_path)[0] + "_publishable.txt"
    if os.path.exists(output_file):
        print(f"\n[SKIP] Publishable version already exists at {output_file}.")
        return True

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    cleaned_input = strip_timestamps(raw_text).strip()
    if not cleaned_input:
        print("Error: Transcript is empty after timestamp stripping.")
        return False

    print("\nGenerating publishable transcript...")
    try:
        publishable = llm_client.complete(PROMPT_TEMPLATE.format(transcript=cleaned_input))
    except requests.exceptions.RequestException as e:
        print(f"Publish API request failed: {e}")
        return False

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(publishable.strip() + "\n")

    print(f"Publishable transcript saved to: {output_file}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py <path_to_transcript>")
        sys.exit(1)
    sys.exit(0 if publish_transcript(sys.argv[1]) else 1)

# Video Transcriber & Summarizer

Containerized pipeline that extracts audio from video files, transcribes with `faster-whisper` on an NVIDIA GPU, and summarizes the transcript via local Ollama or the OpenRouter API.

## Features
* **NVIDIA CUDA acceleration** — `large-v3` Whisper model, `float16` precision.
* **Three artifacts per run** — verbatim transcript, publishable clean-read version, and summary.
* **Smart skip logic** — each stage skips if its output already exists, so re-runs are cheap.
* **Dual LLM backends** — local Ollama by default, OpenRouter when `OPENROUTER_API_KEY` is set.
* **Isolated I/O** — `/input` and `/output` are mounted from the repo root.
* **Real-time console streaming** — unbuffered stdout so transcription progress prints live.

A single invocation produces, for input `meeting.mkv`:

| File | Contents |
| --- | --- |
| `output/meeting.txt` | Verbatim transcript with `[start -> end]` timestamps per line. |
| `output/meeting_publishable.txt` | Clean-read version: filler/disfluency removed, grammar fixed, paragraphs added — but speaker voice, vocabulary, and meaning preserved. |
| `output/meeting_summary.txt` | Concise summary + bulleted takeaways. |

---

## 1. Source Files

| File | Purpose |
| --- | --- |
| [Dockerfile](Dockerfile) | CUDA + Python image, installs deps from `requirements.txt`. |
| [requirements.txt](requirements.txt) | Pinned versions of `faster-whisper` and `requests`. |
| [transcribe.py](transcribe.py) | Entry point — runs Whisper, then publish + summarize. |
| [publish.py](publish.py) | Cleans the verbatim transcript into a publishable, fidelity-preserving read. |
| [summarize.py](summarize.py) | Posts the transcript to Ollama or OpenRouter and writes `_summary.txt`. |
| [llm_client.py](llm_client.py) | Shared OpenRouter/Ollama dispatcher used by both publish and summarize. |

---

## 2. Build

```bash
docker build -t local-transcriber-gpu .
```

---

## 3. Configure secrets

Secrets are loaded from a gitignored `.env` file at the repo root, **never** passed literally on the command line.

```bash
# At repo root, one time:
cp .env.example .env
chmod 600 .env
$EDITOR .env   # paste OPENROUTER_API_KEY (or leave blank for Ollama)
```

The container picks them up via `docker run --env-file .env ...`. The full env-var reference:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | _(unset)_ | If set, summarization uses OpenRouter instead of Ollama. |
| `OPENROUTER_MODEL` | `anthropic/claude-haiku-4.5` | OpenRouter model ID. |
| `OLLAMA_MODEL` | `llama3` | Ollama model name (must be pulled on the host). |
| `OLLAMA_URL` | `http://host.docker.internal:11434/api/generate` | Override if Ollama runs elsewhere. |

---

## 4. Run

All commands assume you are running from the repo root, which contains the shared `input/`, `output/`, and `.env`.

### Option A — local Ollama (default; `.env` empty / missing)
Ollama must be running on your Windows/WSL host on port `11434`. `--add-host=host.docker.internal:host-gateway` lets the container reach it.

```bash
docker run --rm \
  --gpus all \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/input":/input \
  -v "$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu "/input/your_video.mkv"
```

### Option B — OpenRouter API (`.env` has `OPENROUTER_API_KEY`)

```bash
docker run --rm \
  --gpus all \
  --env-file .env \
  -v "$(pwd)/input":/input \
  -v "$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu "/input/your_video.mkv"
```

> 🚫 **Don't do this:** `-e OPENROUTER_API_KEY="sk-or-v1-..."` — the literal lands in `~/.bash_history` and is visible in `ps aux`. Use `--env-file .env`.

---

## 5. Useful Shell Alias

```bash
alias transcribe-video='docker run --rm \
  --gpus all \
  --add-host=host.docker.internal:host-gateway \
  $( [ -f .env ] && echo --env-file .env ) \
  -v "$(pwd)/input":/input \
  -v "$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu'
```

```bash
transcribe-video "/input/meeting.mkv"
```

Outputs:
* `output/meeting.txt` — full transcript with timestamps
* `output/meeting_publishable.txt` — clean-read version, faithful to the speaker's voice
* `output/meeting_summary.txt` — concise summary + bulleted takeaways

---

## 6. The Publishable Transcript

`publish.py` strips timestamps from the verbatim transcript and asks the LLM to clean it up under strict fidelity rules. See [publish.py](publish.py) for the full prompt; the rules in summary:

**Removes:** filler ("um", "uh"), false starts, repeated stutter words, raw timestamps. Adds natural punctuation and paragraph breaks.

**Preserves:** vocabulary, idioms, colloquialisms, sentence rhythm, contractions, asides, anecdotes, opinions — anything that's part of the speaker's voice.

**Never:** paraphrases, rewrites for style, adds content, removes substantive content, or changes meaning.

If the clean-read output doesn't match what you want, edit [publish.py](publish.py) `PROMPT_TEMPLATE` — the rules are explicit and tuneable. Re-running on the same input is free because the stage skips if `_publishable.txt` already exists; delete that file to regenerate.

> ⚠️ **Long transcripts + local Ollama:** Ollama defaults to a small context window (often 2048 or 4096 tokens). A long talk may be silently truncated. For full-length transcripts, prefer the OpenRouter backend (Claude Haiku 4.5 has a 200k context) or set `OLLAMA_NUM_CTX` on the host's Ollama config.

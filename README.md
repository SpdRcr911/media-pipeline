# Media Pipeline

A self-contained, containerized media processing workflow running on WSL. This workspace automates downloading YouTube videos at maximum quality and processing them via GPU-accelerated transcription and LLM post-processing.

## Project Structure

The project is structured into independent, containerized components that share a common `input/` and `output/` directory at the repo root.

```text
media-pipeline/
├── README.md               <-- This file (project overview)
├── .env.example            <-- Template for secrets — copy to .env (gitignored)
├── input/                  <-- Shared drop zone for downloaded videos
├── output/                 <-- Shared destination for transcripts & summaries
├── youtube-backup/         <-- yt-dlp downloader container
│   ├── Dockerfile
│   ├── convert_cookies.py
│   └── README.md
└── video-transcriber/      <-- GPU transcription + LLM cleanup + summarization
    ├── Dockerfile
    ├── transcribe.py       <-- entry point
    ├── publish.py          <-- clean-read transcript generator
    ├── summarize.py        <-- summary + takeaways generator
    ├── llm_client.py       <-- shared OpenRouter/Ollama dispatcher
    ├── requirements.txt
    └── README.md
```

`input/`, `output/`, `.env`, and any `cookies.txt` are gitignored.

---

## Workspace Components

### 1. YouTube Downloader (`youtube-backup/`)
Fetches video assets using `yt-dlp`. Passes YouTube's modern JavaScript (EJS) bot challenges via a Node.js runtime and handles unlisted/private downloads via Netscape-format session cookies stored outside the repo.
* **Documentation:** [youtube-backup/README.md](youtube-backup/README.md).

### 2. Video Transcriber & Summarizer (`video-transcriber/`)
Extracts audio from video containers, transcribes with `faster-whisper`, and post-processes into three artifacts per run:
1. **Verbatim transcript** with timestamps — `{name}.txt`
2. **Publishable clean-read** — `{name}_publishable.txt` (filler/disfluency removed, grammar fixed, speaker's voice and meaning preserved)
3. **Summary + takeaways** — `{name}_summary.txt`
* **LLM backends:** Local Ollama (default) or OpenRouter API (when `OPENROUTER_API_KEY` is set).
* **Documentation:** [video-transcriber/README.md](video-transcriber/README.md).

---

## Secret handling

Secrets never live inside the repo. Two conventions:

| Secret | Location | Loaded into containers via |
| --- | --- | --- |
| `OPENROUTER_API_KEY` (and any other env-style secret) | `.env` at repo root (gitignored) | `docker run --env-file .env ...` |
| YouTube session cookies | `~/.config/media-pipeline/cookies.txt` (outside repo, `chmod 600`) | read-only bind mount |

### One-time setup

```bash
# 1. Create the .env file from the template and fill in real values
cp .env.example .env
chmod 600 .env
$EDITOR .env

# 2. Create the cookies dir outside the repo
mkdir -p ~/.config/media-pipeline
chmod 700 ~/.config/media-pipeline
```

See [youtube-backup/README.md](youtube-backup/README.md) for how to populate `cookies.txt` without exposing the raw cookie string in shell history or source code.

---

## Global Workflow Quick-Start

Add these aliases to `~/.bashrc` or `~/.zshrc` and run them from the repo root.

```bash
# 1. Download stage — writes to ./input
alias pipe-dl='docker run --rm \
  -v "$(pwd)/input":/downloads \
  -v "$HOME/.config/media-pipeline/cookies.txt":/downloads/cookies.txt:ro \
  local-ytdlp \
  --js-runtimes node \
  --cookies /downloads/cookies.txt \
  -f "bestvideo+bestaudio/best" \
  --merge-output-format mkv'

# 2. Processing stage — reads ./input, writes ./output. Loads OPENROUTER_API_KEY
#    (and other vars) from ./.env if it exists.
alias pipe-process='docker run --rm \
  --gpus all \
  --add-host=host.docker.internal:host-gateway \
  $( [ -f .env ] && echo --env-file .env ) \
  -v "$(pwd)/input":/input \
  -v "$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu'
```

### Complete execution example
```bash
# Step 1: Download into ./input
pipe-dl "https://www.youtube.com/watch?v=EXAMPLE_ID"

# Step 2: Transcribe + summarize, results land in ./output.
#         If .env contains OPENROUTER_API_KEY, OpenRouter is used; otherwise
#         the container falls back to local Ollama on host.docker.internal:11434.
pipe-process "/input/downloaded_filename.mkv"
```

---

## Security Notes

* **No secrets on the command line.** Never use `docker run -e OPENROUTER_API_KEY="sk-or-..."` — the literal lands in your shell history and is visible in `ps aux` while the container starts. Use `--env-file .env` instead.
* **Cookies live outside the repo.** `~/.config/media-pipeline/cookies.txt` should be `chmod 600`. Treat the file like a password — it grants YouTube session access until you log out.
* **Rotate when you're done.** Log out of YouTube to invalidate the session, or delete `cookies.txt` after a download run. The converter sets a 30-day expiration as a backstop.
* **Don't bake secrets into images.** Never `ENV OPENROUTER_API_KEY=...` in a Dockerfile or pass secrets as build args — they get baked into image layers permanently.

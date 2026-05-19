# YouTube Downloader (Docker + yt-dlp)

Containerized `yt-dlp` setup that downloads YouTube videos at the highest available quality. Configured to handle YouTube's modern JavaScript (EJS) bot challenges and supports private/age-restricted videos via session cookies stored **outside** the repo.

## Prerequisites
* **Docker** installed and running on your host.
* **Python 3** on the host (only needed to run [convert_cookies.py](convert_cookies.py)).

---

## 1. Source Files

| File | Purpose |
| --- | --- |
| [Dockerfile](Dockerfile) | Python slim base, installs `ffmpeg`, `nodejs`, and pinned `yt-dlp[default]`. |
| [convert_cookies.py](convert_cookies.py) | Converts a raw browser `cookie:` header into a Netscape-format `cookies.txt`. Reads from stdin/env var — never edit the source to paste in cookies. |

---

## 2. Build

```bash
docker build -t local-ytdlp .
```

---

## 3. Cookies — secure setup (for private / age-restricted videos)

**Cookies are sensitive. They live outside the repo at `~/.config/media-pipeline/cookies.txt` with `chmod 600`.**

### Step A — Prepare the destination

```bash
mkdir -p ~/.config/media-pipeline
chmod 700 ~/.config/media-pipeline
```

### Step B — Get your raw cookie string
1. Open your browser and log into YouTube.
2. Open **Developer Tools** (F12 / Ctrl+Shift+I) → **Network** tab.
3. Refresh the page, click the main `www.youtube.com` document request, scroll to **Request Headers**.
4. Find the `cookie:` header, right-click → **Copy value**.

### Step C — Pipe into the converter
The converter reads the raw string from stdin and writes Netscape-format cookies to stdout. **Never paste the raw cookie into the script's source** — pipe it instead so it stays out of disk and shell history.

```bash
# macOS
pbpaste | python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt

# Linux with xclip
xclip -selection clipboard -o | python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt

# WSL with wslu
powershell.exe Get-Clipboard | python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt
```

Then lock down the file:

```bash
chmod 600 ~/.config/media-pipeline/cookies.txt
```

If clipboard tooling isn't available, you can `export YT_COOKIE_STRING='...'` in your current shell and run `python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt`. Be aware: assignments with literal values may end up in `~/.bash_history` unless you prefix with a space (with `HISTCONTROL=ignorespace`) or `unset` immediately after.

> ⚠️ Cookies grant active YouTube session access — treat them like a password. The converter sets a 30-day expiration as a backstop. Rotate by logging out of YouTube or deleting the file when you're done.

---

## 4. Download

Run from the repo root. Cookies are mounted **read-only** from your home dir; downloads land in the shared `input/` directory used by the transcriber.

```bash
docker run --rm \
  -v "$(pwd)/input":/downloads \
  -v "$HOME/.config/media-pipeline/cookies.txt":/downloads/cookies.txt:ro \
  local-ytdlp \
  --js-runtimes node \
  --cookies /downloads/cookies.txt \
  -f "bestvideo+bestaudio/best" \
  --merge-output-format mkv \
  "YOUR_YOUTUBE_URL_HERE"
```

---

## 5. Useful Shell Alias

```bash
alias pipe-dl='docker run --rm \
  -v "$(pwd)/input":/downloads \
  -v "$HOME/.config/media-pipeline/cookies.txt":/downloads/cookies.txt:ro \
  local-ytdlp \
  --js-runtimes node \
  --cookies /downloads/cookies.txt \
  -f "bestvideo+bestaudio/best" \
  --merge-output-format mkv'
```

```bash
pipe-dl "YOUR_YOUTUBE_URL_HERE"
```

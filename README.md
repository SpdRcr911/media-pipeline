# Media Pipeline

A self-contained, containerized media processing pipeline running on WSL. This unified workflow downloads YouTube videos at max quality, leverages an NVIDIA GPU to generate precise transcripts using `faster-whisper`, and runs post-processing summarization via local Ollama instances or the OpenRouter API.

## Architecture & Features
* **Isolated Environment:** Driven entirely by Docker containers to keep the host system clean.
* **GPU Acceleration:** Fully optimized for NVIDIA CUDA (e.g., RTX 2000 Ada) running Whisper `large-v3` with `float16` precision.
* **Smart Skip Logic:** If a transcript already exists for an input video, the heavy GPU extraction step is bypassed, shifting instantly to the LLM summarization stage.
* **Dual-LLM Interface:** Supports local inference via Ollama or high-context cloud models via OpenRouter.

---

## 1. Directory Structure

Organize the parent directory (`media-pipeline`) on your host machine as follows:

```text
media-pipeline/
├── downloader/
│   ├── Dockerfile
│   └── convert_cookies.py
├── transcriber/
│   ├── Dockerfile
│   ├── transcribe.py
│   └── summarize.py
├── input/              <-- Drop standalone video files here, or where downloads land
└── output/             <-- Final text transcripts and summaries appear here
```

---

## 2. Component Configuration

### Part A: Downloader (`downloader/`)

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install ffmpeg, curl, and nodejs (for YouTube JS challenges)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp along with default dependencies for EJS execution
RUN pip install --no-cache-dir "yt-dlp[default]"

WORKDIR /downloads

ENTRYPOINT ["yt-dlp"]
```

#### convert_cookies.py
Use this tool to convert a raw cookie header string into the Netscape format required by `yt-dlp` for private videos.
```python
import os

# Paste raw cookie string from browser network tab here
raw_cookie_string = "PASTE_YOUR_COOKIE_STRING_HERE"

with open("cookies.txt", "w") as f:
    f.write("# Netscape HTTP Cookie File\n")
    for item in raw_cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            f.write(f".youtube.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}\n")

print("Successfully generated Netscape formatted cookies.txt")
```

---

### Part B: Transcriber & Summarizer (`transcriber/`)

#### Dockerfile
```dockerfile
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

# Prevent Python stdout buffering for real-time log streaming
ENV PYTHONUNBUFFERED=1

RUN pip3 install --no-cache-dir faster-whisper requests

WORKDIR /app
COPY transcribe.py .
COPY summarize.py .

ENV HF_HOME=/models

ENTRYPOINT ["python", "transcribe.py"]
```

#### transcribe.py
```python
import sys
import os
import subprocess
from faster_whisper import WhisperModel

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <path_to_video>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        sys.exit(1)

    filename = os.path.basename(input_file)
    base_name = os.path.splitext(filename)[0]
    output_dir = "/output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, base_name + ".txt")

    if os.path.exists(output_file):
        print(f"\n[SKIP] Transcript already exists at {output_file}.")
        print("Bypassing faster-whisper and proceeding directly to summarization...")
    else:
        print(f"\n[START] No existing transcript found. Starting transcription for {filename}...")
        
        model_size = "large-v3"
        print(f"Loading '{model_size}' model onto GPU...")
        model = WhisperModel(model_size, device="cuda", compute_type="float16")

        print(f"Transcribing: {filename}...")
        segments, info = model.transcribe(input_file, beam_size=5)

        print(f"Detected language: '{info.language}' (Probability: {info.language_probability:.2f})")

        with open(output_file, "w", encoding="utf-8") as f:
            for segment in segments:
                line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                print(line, end="")
                f.write(line)

        print(f"\nTranscription complete. Saved to: {output_file}")
    
    subprocess.run(["python", "summarize.py", output_file])

if __name__ == "__main__":
    main()
```

#### summarize.py
```python
import sys
import os
import requests

def summarize_transcript(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Transcript not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    print("\nInitiating summarization...")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    prompt_text = (
        "Please provide a concise summary, followed by a bulleted list of the main takeaways, "
        f"for the following video transcript:\n\n{transcript_text}"
    )

    if openrouter_key:
        print("Using OpenRouter (Cloud) for summarization...")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "anthropic/claude-3-haiku",
            "messages": [{"role": "user", "content": prompt_text}]
        }
    else:
        print("Using local Ollama for summarization...")
        url = "http://host.docker.internal:11434/api/generate"
        headers = {}
        payload = {
            "model": "llama3",
            "prompt": prompt_text,
            "stream": False
        }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        if openrouter_key:
            summary = response.json()["choices"][0]["message"]["content"]
        else:
            summary = response.json().get("response", "")
            
        summary_file = os.path.splitext(file_path)[0] + "_summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
            
        print(f"Summary generated successfully! Saved to: {summary_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"API Request Failed. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        summarize_transcript(sys.argv[1])
```

---

## 3. Build Instructions

Run these build commands within their respective subdirectories to generate both local container images:

```bash
# Build the downloader image
cd downloader
docker build -t local-ytdlp .

# Build the transcriber image
cd ../transcriber
docker build -t local-transcriber-gpu .
```

---

## 4. Operational Commands

### Stage 1: Download from YouTube
Maps your local `input` folder to capture the downloaded files. If downloading private assets, ensure `cookies.txt` has been generated via `convert_cookies.py` and is located in your running path.

```bash
docker run --rm \
  -v "\$(pwd)/input":/downloads \
  -v "\$(pwd)/downloader/cookies.txt":/downloads/cookies.txt \
  local-ytdlp \
  --js-runtimes node \
  --cookies /downloads/cookies.txt \
  -f "bestvideo+bestaudio/best" \
  --merge-output-format mkv \
  "YOUR_YOUTUBE_URL_HERE"
```

### Stage 2: Transcribe & Summarize
Maps the local folders along with your mapped Windows drive path for persistent ML models model storing (`D:\models` translates to `/mnt/d/models` in WSL).

#### Using Local Ollama
```bash
docker run --rm \
  --gpus all \
  --add-host=host.docker.internal:host-gateway \
  -v "\$(pwd)/input":/input \
  -v "\$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu "/input/your_downloaded_video.mkv"
```

#### Using OpenRouter API
```bash
docker run --rm \
  --gpus all \
  -e OPENROUTER_API_KEY="sk-or-v1-your-key-here" \
  -v "\$(pwd)/input":/input \
  -v "\$(pwd)/output":/output \
  -v /mnt/d/models:/models \
  local-transcriber-gpu "/input/your_downloaded_video.mkv"
```

---

## 5. Shell Aliases
To streamline this pipeline into simple CLI operations, add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Download Alias
alias pipe-dl='docker run --rm -v "\$(pwd)/input":/downloads -v "\$(pwd)/downloader/cookies.txt":/downloads/cookies.txt local-ytdlp --js-runtimes node --cookies /downloads/cookies.txt -f "bestvideo+bestaudio/best" --merge-output-format mkv'

# Transcribe/Summarize Alias (Defaults to Ollama setup)
alias pipe-process='docker run --rm --gpus all --add-host=host.docker.internal:host-gateway -v "\$(pwd)/input":/input -v "\$(pwd)/output":/output -v /mnt/d/models:/models local-transcriber-gpu'
```

### Workflow Execution Example:
```bash
pipe-dl "https://www.youtube.com/watch?v=EXAMPLE"
pipe-process "/input/filename_from_download.mkv"
```

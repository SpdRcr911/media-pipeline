FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "yt-dlp[default]==2026.3.17" "yt-dlp-ejs==0.8.0"

WORKDIR /downloads

ENTRYPOINT ["yt-dlp"]

"""Convert a raw browser `cookie:` header into Netscape-format yt-dlp cookies.

Reads the raw cookie string from stdin (or the YT_COOKIE_STRING env var) and
writes Netscape-format cookies to stdout. The caller redirects stdout to the
chosen cookie file — typically a path outside the repo with restrictive perms.

Examples
--------
    # Paste from clipboard (macOS)
    pbpaste | python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt

    # Paste from clipboard (Linux with xclip)
    xclip -selection clipboard -o | python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt

    # From env var
    YT_COOKIE_STRING="..." python3 convert_cookies.py > ~/.config/media-pipeline/cookies.txt

Then restrict the file:
    chmod 600 ~/.config/media-pipeline/cookies.txt
"""

import os
import sys
import time

# yt-dlp's Netscape parser treats `0` as "already expired" — set a real future timestamp.
EXPIRATION_DAYS = 30


def main() -> int:
    raw = os.environ.get("YT_COOKIE_STRING")
    if not raw:
        if sys.stdin.isatty():
            print(
                "error: provide the raw cookie string via stdin or the YT_COOKIE_STRING env var.\n"
                "       see the docstring at the top of this file for examples.",
                file=sys.stderr,
            )
            return 1
        raw = sys.stdin.read()

    expiration = int(time.time()) + 86400 * EXPIRATION_DAYS

    out = sys.stdout
    out.write("# Netscape HTTP Cookie File\n")
    for item in raw.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        # Format: domain, include_subdomains, path, secure, expiration, name, value
        out.write(f".youtube.com\tTRUE\t/\tTRUE\t{expiration}\t{name}\t{value}\n")

    print(f"Wrote Netscape cookies (expiring in {EXPIRATION_DAYS} days). Remember: chmod 600.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

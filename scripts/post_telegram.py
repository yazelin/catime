"""Post the latest cat image to a Telegram channel. Run after generate_cat.py."""

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


def get_latest_cat() -> dict | None:
    """Get the latest successful cat entry from catlist.json."""
    catlist = Path("catlist.json")
    if not catlist.exists():
        return None
    with catlist.open("r", encoding="utf-8") as f:
        cats = json.load(f)
    for cat in reversed(cats):
        if isinstance(cat, dict) and cat.get("status") == "success":
            return cat
    return None


def get_cat_detail(cat: dict) -> dict:
    """Try to get full detail (story, idea) from monthly file."""
    ts = cat.get("timestamp", "")
    month = ts[:7]
    month_path = Path("cats") / f"{month}.json"
    if not month_path.exists():
        return cat
    with month_path.open("r", encoding="utf-8") as f:
        monthly = json.load(f)
    for entry in reversed(monthly):
        if isinstance(entry, dict) and entry.get("number") == cat.get("number"):
            return {**cat, **entry}
    return cat


def download_image(url: str) -> bytes:
    """Download image from URL, following redirects."""
    req = urllib.request.Request(url, headers={"User-Agent": "catime-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def send_photo_multipart(bot_token: str, chat_id: str, image_data: bytes, filename: str, caption: str) -> bool:
    """Send a photo to Telegram channel via multipart upload."""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    boundary = "----CatimeBoundary"

    body_parts = []
    # chat_id field
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}")
    # caption field
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}")
    # parse_mode field
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML")

    # Build multipart body
    pre_file = "\r\n".join(body_parts) + "\r\n"
    file_header = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\n"
        f"Content-Type: image/webp\r\n\r\n"
    )
    post_file = f"\r\n--{boundary}--\r\n"

    body = pre_file.encode("utf-8") + file_header.encode("utf-8") + image_data + post_file.encode("utf-8")

    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                print(f"Telegram API error: {result}", file=sys.stderr)
                return False
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"Telegram API HTTP {e.code}: {err_body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to send Telegram photo: {e}", file=sys.stderr)
        return False


def build_caption(cat: dict) -> str:
    """Build a nice caption for the cat image."""
    number = cat.get("number", "?")
    title = cat.get("title", "")
    story = cat.get("story", "")
    char_name = cat.get("character_name", "")
    timestamp = cat.get("timestamp", "")
    inspiration = cat.get("inspiration", "")

    lines = []
    if title:
        lines.append(f"<b>#{number} {title}</b>")
    else:
        lines.append(f"<b>🐱 Cat #{number}</b>")

    if char_name:
        lines.append(f"🎭 {char_name}")

    if story:
        lines.append(f"\n{story}")

    if inspiration and inspiration != "original":
        lines.append(f"\n💡 {inspiration}")

    lines.append(f"\n🕐 {timestamp}")
    lines.append("🔗 <a href=\"https://yazelin.github.io/catime/\">catime</a>")

    return "\n".join(lines)


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set, skipping.")
        return

    cat = get_latest_cat()
    if not cat:
        print("No successful cat found, skipping.")
        return

    image_url = cat.get("url")
    if not image_url:
        print("No image URL, skipping.")
        return

    cat = get_cat_detail(cat)
    caption = build_caption(cat)

    print(f"Posting cat #{cat.get('number')} to Telegram channel {chat_id}...")
    print(f"Image URL: {image_url}")

    # Download image first (GitHub release URLs redirect, Telegram can't follow them)
    print("Downloading image...")
    try:
        image_data = download_image(image_url)
        print(f"Downloaded {len(image_data)} bytes")
    except Exception as e:
        print(f"Failed to download image: {e}", file=sys.stderr)
        sys.exit(1)

    filename = image_url.split("/")[-1] or "cat.webp"

    if send_photo_multipart(bot_token, chat_id, image_data, filename, caption):
        print("Posted successfully!")
    else:
        print("Failed to post to Telegram.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

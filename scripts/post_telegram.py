"""Post the latest cat image to a Telegram channel. Run after generate_cat.py."""

import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path


def get_latest_cat() -> dict | None:
    """Get the latest successful cat entry from catlist.json."""
    catlist = Path("catlist.json")
    if not catlist.exists():
        return None
    with catlist.open("r", encoding="utf-8") as f:
        cats = json.load(f)
    # Find last successful entry
    for cat in reversed(cats):
        if isinstance(cat, dict) and cat.get("status") == "success":
            return cat
    return None


def get_cat_detail(cat: dict) -> dict:
    """Try to get full detail (story, idea) from monthly file."""
    ts = cat.get("timestamp", "")
    month = ts[:7]  # "YYYY-MM"
    month_path = Path("cats") / f"{month}.json"
    if not month_path.exists():
        return cat
    with month_path.open("r", encoding="utf-8") as f:
        monthly = json.load(f)
    for entry in reversed(monthly):
        if isinstance(entry, dict) and entry.get("number") == cat.get("number"):
            return {**cat, **entry}
    return cat


def send_photo(bot_token: str, chat_id: str, photo_url: str, caption: str) -> bool:
    """Send a photo to Telegram channel via Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                print(f"Telegram API error: {result}", file=sys.stderr)
                return False
            return True
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

    # Title
    if title:
        lines.append(f"<b>#{number} {title}</b>")
    else:
        lines.append(f"<b>🐱 Cat #{number}</b>")

    # Character
    if char_name:
        lines.append(f"🎭 {char_name}")

    # Story
    if story:
        lines.append(f"\n{story}")

    # News inspiration
    if inspiration and inspiration != "original":
        lines.append(f"\n💡 {inspiration}")

    # Footer
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

    # Get full detail
    cat = get_cat_detail(cat)

    caption = build_caption(cat)
    print(f"Posting cat #{cat.get('number')} to Telegram channel...")

    if send_photo(bot_token, chat_id, image_url, caption):
        print("Posted successfully!")
    else:
        print("Failed to post to Telegram.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

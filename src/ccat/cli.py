"""CLI entry point for ccat - view AI-generated hourly cats."""

import argparse
import json
import sys
from pathlib import Path

import httpx

CATLIST_URL = "https://raw.githubusercontent.com/{repo}/main/catlist.json"
DEFAULT_REPO = "yazelin/ccat"


def fetch_catlist(repo: str) -> list[dict]:
    url = CATLIST_URL.format(repo=repo)
    resp = httpx.get(url, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


def load_local_catlist() -> list[dict]:
    p = Path(__file__).resolve().parent.parent.parent / "catlist.json"
    if p.exists():
        return json.loads(p.read_text())
    return []


def main():
    parser = argparse.ArgumentParser(
        prog="ccat",
        description="View AI-generated hourly cat images",
    )
    parser.add_argument(
        "number", nargs="?", type=int,
        help="Cat number to view (1-based). Omit to see total count.",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repo owner/name")
    parser.add_argument("--local", action="store_true", help="Use local catlist.json")
    parser.add_argument("--list", action="store_true", help="List all cats")
    args = parser.parse_args()

    try:
        cats = load_local_catlist() if args.local else fetch_catlist(args.repo)
    except Exception as e:
        print(f"Error loading cat list: {e}", file=sys.stderr)
        sys.exit(1)

    if not cats:
        print("No cats yet! Check back in an hour.")
        return

    if args.list:
        for i, cat in enumerate(cats, 1):
            print(f"#{i:04d}  {cat['timestamp']}  {cat['url']}")
        return

    if args.number is None:
        print(f"Total cats: {len(cats)}")
        print(f"Latest: #{len(cats):04d}  {cats[-1]['timestamp']}")
        print("Use 'ccat <number>' to view, or 'ccat --list' to list all.")
        return

    idx = args.number - 1
    if idx < 0 or idx >= len(cats):
        print(f"Cat #{args.number} not found. Available: 1-{len(cats)}", file=sys.stderr)
        sys.exit(1)

    cat = cats[idx]
    print(f"Cat #{args.number:04d}")
    print(f"Generated: {cat['timestamp']}")
    print(f"URL: {cat['url']}")

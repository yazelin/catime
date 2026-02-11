#!/usr/bin/env python3
"""Generate an Atom feed (docs/feed.xml) from catlist.json."""

import json
import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree

FEED_TITLE = "Catime - AI Cat Gallery"
FEED_LINK = "https://yazelin.github.io/catime/"
GALLERY_BASE = "https://yazelin.github.io/catime/gallery.html"
IMAGE_BASE = "https://github.com/yazelin/catime/releases/download/cats"
ATOM_NS = "http://www.w3.org/2005/Atom"
MAX_ENTRIES = 20


def parse_timestamp(ts: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM UTC' into a timezone-aware datetime."""
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M %Z").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def build_feed(entries: list[dict]) -> ElementTree:
    feed = Element("feed", xmlns=ATOM_NS)

    SubElement(feed, "title").text = FEED_TITLE
    SubElement(feed, "link", href=FEED_LINK, rel="alternate")
    SubElement(feed, "id").text = FEED_LINK

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SubElement(feed, "updated").text = now

    for cat in entries:
        number = cat.get("number", 0)
        title = cat.get("title") or f"Cat #{number}"
        ts = parse_timestamp(cat.get("timestamp", ""))
        published = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        link = f"{GALLERY_BASE}#cat-{number}"
        image_url = f"{IMAGE_BASE}/{number}.png"
        summary = cat.get("inspiration") or ""

        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text = title
        SubElement(entry, "link", href=link, rel="alternate")
        SubElement(entry, "id").text = link
        SubElement(entry, "published").text = published
        SubElement(entry, "updated").text = published
        if summary:
            SubElement(entry, "summary").text = summary
        SubElement(entry, "link", rel="enclosure", href=image_url, type="image/png")

    return ElementTree(feed)


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catlist_path = os.path.join(repo_root, "catlist.json")
    output_path = os.path.join(repo_root, "docs", "feed.xml")

    with open(catlist_path, encoding="utf-8") as f:
        cats = json.load(f)

    # Sort by timestamp descending and take latest 20
    cats.sort(key=lambda c: parse_timestamp(c.get("timestamp", "")), reverse=True)
    latest = cats[:MAX_ENTRIES]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    tree = build_feed(latest)
    with open(output_path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    print(f"Wrote {len(latest)} entries to {output_path}")


if __name__ == "__main__":
    main()

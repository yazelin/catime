"""One-time migration: split catlist.json into lightweight index + monthly detail files."""

import json
from collections import defaultdict
from pathlib import Path


def main():
    catlist_path = Path("catlist.json")
    cats_dir = Path("cats")

    cats = json.loads(catlist_path.read_text())
    print(f"Loaded {len(cats)} entries from catlist.json")

    index_fields = {"number", "timestamp", "url", "model", "status", "error"}
    detail_fields = {"number", "prompt", "story", "idea", "news_inspiration", "avoid_list"}

    index = []
    monthly = defaultdict(list)

    for cat in cats:
        # Build lightweight index entry (keep only index fields that exist)
        index_entry = {k: cat[k] for k in index_fields if k in cat}
        index.append(index_entry)

        # Build detail entry only for successful cats with detail data
        has_detail = any(cat.get(k) for k in detail_fields if k != "number")
        if has_detail:
            detail_entry = {k: cat[k] for k in detail_fields if k in cat}
            month = cat["timestamp"][:7]  # "YYYY-MM"
            monthly[month].append(detail_entry)

    # Write lightweight index
    catlist_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(index)} entries to catlist.json")

    # Write monthly detail files
    cats_dir.mkdir(exist_ok=True)
    for month, details in sorted(monthly.items()):
        month_path = cats_dir / f"{month}.json"
        month_path.write_text(json.dumps(details, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {len(details)} entries to {month_path}")

    print("Migration complete!")


if __name__ == "__main__":
    main()

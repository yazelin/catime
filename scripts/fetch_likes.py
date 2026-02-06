"""Fetch reaction counts from GitHub issue comments and produce likes.json + comment_map.json.

Scans all "Cat Gallery - YYYY-MM" issues, reads comments, parses cat numbers,
and sums positive reactions (👍 ❤️ 😄 🎉 🚀 👀).

Run by GitHub Actions hourly or manually.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "yazelin/catime"
POSITIVE_REACTIONS = ("+1", "heart", "hooray", "laugh", "rocket", "eyes")


def gh_api(endpoint: str) -> list | dict:
    """Call gh api with pagination and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", "--paginate", endpoint],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"gh api error for {endpoint}: {result.stderr.strip()}", file=sys.stderr)
        return []
    # --paginate concatenates JSON arrays; handle both single and concatenated output
    text = result.stdout.strip()
    if not text:
        return []
    # Paginated output may concatenate arrays like ][, fix that
    if text.startswith("["):
        text = text.replace("]\n[", ",").replace("][", ",")
    return json.loads(text)


def find_gallery_issues() -> list[dict]:
    """Find all open+closed issues matching 'Cat Gallery - YYYY-MM'."""
    issues = gh_api(f"/repos/{REPO}/issues?state=all&per_page=100")
    gallery = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        # Skip pull requests (GitHub issues API returns PRs too)
        if "pull_request" in issue:
            continue
        if re.match(r"Cat Gallery - \d{4}-\d{2}", issue.get("title", "")):
            gallery.append(issue)
    return gallery


def fetch_comments(issue_number: int) -> list[dict]:
    """Fetch all comments for an issue, including reaction counts."""
    return gh_api(f"/repos/{REPO}/issues/{issue_number}/comments?per_page=100")


def parse_cat_number(body: str) -> int | None:
    """Extract cat number from comment body (## Cat #N)."""
    match = re.search(r"## Cat #(\d+)", body or "")
    if match:
        return int(match.group(1))
    return None


def sum_positive_reactions(reactions: dict) -> int:
    """Sum positive reaction counts from a reactions object."""
    return sum(reactions.get(key, 0) for key in POSITIVE_REACTIONS)


def main():
    print("Finding Cat Gallery issues...")
    issues = find_gallery_issues()

    likes = {}       # cat_number_str -> count
    comment_map = {} # cat_number_str -> comment URL

    if not issues:
        print("No Cat Gallery issues found.")
    else:
        print(f"Found {len(issues)} gallery issue(s)")

    for issue in issues:
        issue_number = issue["number"]
        issue_url = issue["html_url"]
        print(f"  Fetching comments for issue #{issue_number} ({issue['title']})...")
        comments = fetch_comments(issue_number)

        for comment in comments:
            if not isinstance(comment, dict):
                continue
            cat_num = parse_cat_number(comment.get("body", ""))
            if cat_num is None:
                continue

            cat_key = str(cat_num)
            comment_id = comment["id"]
            comment_map[cat_key] = f"{issue_url}#issuecomment-{comment_id}"

            reactions = comment.get("reactions", {})
            count = sum_positive_reactions(reactions)
            if count > 0:
                likes[cat_key] = count

    # Write output files to docs/ for GitHub Pages
    docs = Path("docs")
    docs.mkdir(exist_ok=True)

    likes_path = docs / "likes.json"
    likes_path.write_text(json.dumps(likes, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {likes_path} ({len(likes)} cats with likes)")

    comment_map_path = docs / "comment_map.json"
    comment_map_path.write_text(json.dumps(comment_map, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {comment_map_path} ({len(comment_map)} comments mapped)")


if __name__ == "__main__":
    main()

"""Generate a cat image using nanobanana-py, upload as GitHub Release asset. Run by GitHub Actions hourly."""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "yazelin/catime")
RELEASE_TAG = "cats"


async def generate_cat_image(output_dir: str, timestamp: str) -> dict:
    """Use nanobanana-py's ImageGenerator to generate a cat image."""
    from nanobanana_py.image_generator import ImageGenerator
    from nanobanana_py.types import ImageGenerationRequest

    generator = ImageGenerator()

    request = ImageGenerationRequest(
        prompt=f"畫一隻可愛的貓，並在圖片中顯示現在的日期與時間: {timestamp}",
        filename=f"cat_{timestamp.replace(' ', '_').replace(':', '')}",
        resolution="1K",
        file_format="png",
        parallel=1,
        output_count=1,
    )

    os.environ["NANOBANANA_OUTPUT_DIR"] = output_dir
    response = await generator.generate_text_to_image(request)

    if not response.success:
        return {
            "file_path": None,
            "model_used": None,
            "status": "failed",
            "error": f"{response.message} - {response.error}",
        }

    model_info = response.model_used or "unknown"
    if response.used_fallback:
        model_info += f" (fallback from {response.primary_model}, reason: {response.fallback_reason})"

    return {
        "file_path": response.generated_files[0],
        "model_used": model_info,
        "status": "success",
    }


def ensure_release_exists():
    """Create the 'cats' release if it doesn't exist."""
    result = subprocess.run(
        ["gh", "release", "view", RELEASE_TAG, "--repo", REPO],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            [
                "gh", "release", "create", RELEASE_TAG,
                "--repo", REPO,
                "--title", "Cat Images",
                "--notes", "Auto-generated cat images, one every hour.",
            ],
            check=True,
        )


def upload_image_as_release_asset(image_path: str) -> str:
    """Upload image as a GitHub Release asset. Returns the public download URL."""
    filename = Path(image_path).name

    subprocess.run(
        [
            "gh", "release", "upload", RELEASE_TAG,
            image_path,
            "--repo", REPO,
            "--clobber",
        ],
        check=True,
    )

    # Release asset URL format
    return f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/{filename}"


def get_or_create_monthly_issue(now: datetime) -> str:
    """Get or create a monthly issue for cat images. Returns issue number as string."""
    month_label = now.strftime("%Y-%m")
    title = f"Cat Gallery - {month_label}"

    # Search for existing issue with this title
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", REPO, "--search", f'"{title}" in:title', "--json", "number,title", "--limit", "10"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        issues = json.loads(result.stdout)
        for issue in issues:
            if issue["title"] == title:
                return str(issue["number"])

    # Create new monthly issue
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", f"Auto-generated cat images for {month_label}."],
        capture_output=True, text=True, check=True,
    )
    # Extract issue number from URL output
    url = result.stdout.strip()
    return url.split("/")[-1]


def post_issue_comment(issue_number: str, image_url: str, number: int, timestamp: str, model_used: str):
    """Post a comment on the monthly issue with the cat image."""
    body = (
        f"## Cat #{number}\n"
        f"**Time:** {timestamp}\n"
        f"**Model:** `{model_used}`\n\n"
        f"![cat-{number}]({image_url})"
    )
    subprocess.run(
        ["gh", "issue", "comment", issue_number, "--repo", REPO, "--body", body],
        check=True,
    )


def update_catlist_and_push(entry: dict) -> int:
    """Update catlist.json, commit and push (only JSON, no images)."""
    catlist_path = Path("catlist.json")
    cats = json.loads(catlist_path.read_text()) if catlist_path.exists() else []
    cats.append(entry)
    catlist_path.write_text(json.dumps(cats, indent=2, ensure_ascii=False) + "\n")

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", "catlist.json"], check=True)

    status = entry["status"]
    number = entry.get("number")
    timestamp = entry["timestamp"]
    msg = f"Add cat #{number} - {timestamp}" if status == "success" else f"Failed cat - {timestamp}"
    subprocess.run(["git", "commit", "-m", msg], check=True)

    # Retry push with rebase in case of concurrent pushes
    for attempt in range(3):
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            break
        print(f"Push failed (attempt {attempt + 1}), rebasing...")
        subprocess.run(["git", "pull", "--rebase"], check=True)
    else:
        raise RuntimeError("Failed to push after 3 attempts")
    return number or 0


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")

    print(f"Generating cat for {timestamp}...")
    result = asyncio.run(generate_cat_image("/tmp", timestamp))

    # Read current count for numbering
    catlist_path = Path("catlist.json")
    cats = json.loads(catlist_path.read_text()) if catlist_path.exists() else []
    next_number = len(cats) + 1

    if result["status"] == "failed":
        print(f"Generation failed: {result['error']}", file=sys.stderr)
        entry = {
            "number": None,
            "timestamp": timestamp,
            "url": None,
            "model": "all failed",
            "status": "failed",
            "error": result["error"],
        }
        update_catlist_and_push(entry)
        sys.exit(1)

    image_path = result["file_path"]
    model_used = result["model_used"]
    print(f"Model used: {model_used}")

    print("Ensuring release exists...")
    ensure_release_exists()

    print("Uploading image as release asset...")
    image_url = upload_image_as_release_asset(image_path)
    print(f"Image URL: {image_url}")

    entry = {
        "number": next_number,
        "timestamp": timestamp,
        "url": image_url,
        "model": model_used,
        "status": "success",
    }
    print("Updating catlist.json...")
    update_catlist_and_push(entry)

    print("Posting issue comment...")
    issue_number = get_or_create_monthly_issue(now)
    print(f"Using monthly issue #{issue_number}")
    post_issue_comment(issue_number, image_url, next_number, timestamp, model_used)

    print(f"Done! Cat #{next_number}")


if __name__ == "__main__":
    main()

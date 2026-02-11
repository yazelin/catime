# <img src="docs/icon-192.png" width="32" height="32" alt="catime icon"> catime

AI-generated hourly cat images. A new cat every hour!

Every hour, a GitHub Actions workflow generates a unique cat image using [nanobanana-py](https://pypi.org/project/nanobanana-py/) (Gemini API), uploads it as a GitHub Release asset, and posts it to a monthly issue.

## 贊助 Sponsors

如果你喜歡 catime，歡迎透過 [Buy Me a Coffee](https://buymeacoffee.com/yazelin) 贊助本專案！詳細方案請參閱 [SPONSORS.md](SPONSORS.md)。

## Install & Usage

```bash
uvx catime              # Show total cat count
uvx catime latest       # View the latest cat
uvx catime 42           # View cat #42
uvx catime today        # List today's cats
uvx catime yesterday    # List yesterday's cats
uvx catime 2026-01-30   # List all cats from a date
uvx catime 2026-01-30T05  # View the cat from a specific hour
uvx catime --list       # List all cats
uvx catime view         # Open cat gallery in browser (localhost:8000)
uvx catime view --port 3000  # Use custom port
```

## How It Works

- **Image generation:** [nanobanana-py](https://pypi.org/project/nanobanana-py/) with `gemini-3-pro-image-preview` (fallback: `gemini-2.5-flash-image`)
- **Image hosting:** GitHub Release assets
- **Cat gallery:** Monthly GitHub issues (auto-created)
- **Metadata:** `catlist.json` in the repo (records timestamp, model used, success/failure)
- **Gallery:** [GitHub Pages](https://yazelin.github.io/catime) waterfall gallery (`docs/`)
- **Schedule:** GitHub Actions cron, every hour at :00

## Setup (for your own repo)

1. Fork or clone this repo
2. Add `GEMINI_API_KEY` to repo Settings → Secrets
3. The workflow will auto-create monthly issues and a `cats` release

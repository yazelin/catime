# <img src="docs/icon-192.png" width="32" height="32" alt="catime icon"> catime

**AI-generated hourly cat images. A new cat every hour!** 🐱

Every hour, a GitHub Actions workflow generates a unique cat image using Google Gemini, uploads it as a GitHub Release asset, and posts it to a monthly issue. 103+ art styles — from ukiyo-e to cyberpunk to embroidery miniatures. Each cat comes with its own story.

🌐 **Gallery:** [yazelin.github.io/catime](https://yazelin.github.io/catime/)
📦 **PyPI:** [catime](https://pypi.org/project/catime/)
🧩 **OpenClaw Skill:** `clawhub install catime`

> 📖 README in other languages: [繁體中文](docs/README.zh-TW.md) | [日本語](docs/README.ja.md)

## Sponsors

If you enjoy catime, consider supporting the project via [Buy Me a Coffee](https://buymeacoffee.com/yazelin) ☕

All sponsorship goes toward API costs, compute resources, and project maintenance. See [SPONSORS.md](SPONSORS.md) for details.

## Install & Usage

```bash
pip install catime
```

```bash
catime                     # Show total cat count
catime latest              # View the latest cat
catime 42                  # View cat #42
catime today               # List today's cats
catime yesterday           # List yesterday's cats
catime 2026-01-30          # List all cats from a date
catime 2026-01-30T05       # View the cat from a specific hour
catime --list              # List all cats
catime view                # Open cat gallery in browser (localhost:8000)
catime view --port 3000    # Use custom port
```

Or run without installing:

```bash
uvx catime latest
```

## How It Works

| Component | Details |
|-----------|---------|
| **Image generation** | [nanobanana-py](https://pypi.org/project/nanobanana-py/) with `gemini-3-pro-image-preview` (fallback: `gemini-2.5-flash-image`) |
| **Image hosting** | GitHub Release assets |
| **Cat gallery** | Monthly GitHub issues (auto-created) |
| **Metadata** | `catlist.json` in the repo |
| **Web gallery** | [GitHub Pages](https://yazelin.github.io/catime/) waterfall layout |
| **Schedule** | GitHub Actions cron, every hour |

## Characters

catime features recurring cat characters, each with unique personalities and appearances:

- **Momo (墨墨)** — Elegant solid black shorthair with golden-amber eyes and a gold hoop earring
- **Captain** — Battle-scarred orange tabby adventurer with a torn left ear
- **Mochi (麻糬)** — Fluffy round cream-white Persian, always looks sleepy
- **Lingling (鈴鈴)** — Playful silver tabby kitten with sapphire-blue eyes

## Setup (for your own repo)

1. Fork or clone this repo
2. Add `GEMINI_API_KEY` to repo Settings → Secrets
3. The workflow will auto-create monthly issues and a `cats` release

## License

MIT

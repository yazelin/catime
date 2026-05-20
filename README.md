# <img src="docs/icon-192.png" width="32" height="32" alt="catime icon"> catime

**AI-generated hourly cat images. A new cat every hour!** 🐱

Every hour, a GitHub Actions workflow generates a unique cat image using Google Gemini, uploads it as a GitHub Release asset, and posts it to a monthly issue. 103+ art styles — from ukiyo-e to cyberpunk to embroidery miniatures. Each cat comes with its own story.

- 🌐 **Gallery:** [yazelin.github.io/catime](https://yazelin.github.io/catime/)
- 📲 **Telegram:** [@catime_yaze](https://t.me/catime_yaze) — 每小時自動發圖
- 📦 **PyPI:** [catime](https://pypi.org/project/catime/)
- 🧩 **OpenClaw Skill:** `clawhub install catime`

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
| **Image generation** | Pluggable. Default: [nanobanana-py](https://pypi.org/project/nanobanana-py/) with `gemini-3-pro-image-preview` (fallback: `gemini-2.5-flash-image`). Optional: a self-hosted `codex-image-service` (Codex CLI behind FastAPI) selected via `CAT_IMAGE_GENERATOR=codex`. |
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

1. Fork or clone this repo.
2. Open `Settings → Secrets and variables → Actions` and add the values for
   whichever backend(s) you want to use.

### Required for the default (Gemini / nanobanana) backend

| Kind | Name | Value |
|---|---|---|
| Secret | `GEMINI_API_KEY` | Google AI Studio key |
| Secret | `GEMINI_WEB_BASE_URL` | _(optional)_ self-hosted gemini-web proxy, e.g. `https://ching-tech.ddns.net/gemini-web` |
| Secret | `TELEGRAM_BOT_TOKEN` | _(optional)_ to mirror posts to a Telegram channel |

That's enough — the workflow will auto-create monthly issues and a `cats` release.

### Optional: route final image rendering through codex-image-service

This skips the final nanobanana / Gemini render and uses a self-hosted
[`codex-image-service`](https://ching-tech.ddns.net/codex-image) (OpenAI Codex
CLI behind FastAPI). The earlier Gemini chain (news → idea → prompt)
**stays unchanged**; only the last "turn prompt into pixels" step swaps out.

| Kind | Name | Value |
|---|---|---|
| Secret | `CODEX_IMAGE_KEY` | A `cimg_*` API key issued from the codex-image-service admin |
| Secret | `CODEX_IMAGE_BASE_URL` | `https://ching-tech.ddns.net/codex-image` (or your own deployment) |
| Variable | `CAT_IMAGE_GENERATOR` | Set to `codex` to enable; leave empty / `nanobanana` to stay on the Gemini path |
| Variable | `CODEX_IMAGE_MODEL_LABEL` | _(optional)_ what to record in the `model` field of the gallery entry. Defaults to `gpt-image-2 (codex-image-service / $imagegen)`. |

Under the hood Codex CLI's `$imagegen` skill drives the built-in `image_gen`
tool — **`gpt-image-2`** by default — billing against the host's ChatGPT
subscription quota, not the OpenAI Images API. If you ever change that or
add a different label, set `CODEX_IMAGE_MODEL_LABEL` and every new cat entry
records the new model name.

Switching backends is a one-click change to the `CAT_IMAGE_GENERATOR`
repository variable — no commit needed.

When `CAT_IMAGE_GENERATOR=codex` is set and the codex backend fails (key
revoked, service down, timeout, network error, etc.), the script
**automatically falls back to nanobanana / Gemini** so the hourly cat still
ships. The fallback is recorded in the gallery entry's `model` field as
`<gemini model> (fallback from codex: <error reason>)`, so the failure is
visible without breaking the cron rhythm. If both backends fail in the same
hour the entry is marked `failed` and the workflow exits non-zero.

A revoked key returns `403`; a missing key returns `401`; the admin can
disable or delete keys at any time from the codex-image-service dashboard.

## License

MIT

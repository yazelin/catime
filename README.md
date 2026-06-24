# <img src="docs/icon-192.png" width="32" height="32" alt="catime icon"> catime

**AI 生成的每小時貓咪圖片，每小時誕生一隻新貓！** 🐱

每小時，GitHub Actions 會透過 Google Gemini 自動生成一張獨特的貓咪圖片，上傳到 GitHub Release，並發佈到月度 issue。103+ 種藝術風格——從浮世繪到賽博龐克到刺繡微縮模型。每隻貓都有自己的故事。

🌐 **圖庫：** [yazelin.github.io/catime](https://yazelin.github.io/catime/)
📲 **Telegram：** [@catime_yaze](https://t.me/catime_yaze) — 每小時自動發圖
📦 **PyPI：** [catime](https://pypi.org/project/catime/)
🧩 **OpenClaw 技能：** `clawhub install catime`

> 📖 其他語言：[English](README.en.md) | [日本語](README.ja.md)

## 贊助

如果你喜歡 catime，歡迎透過 [Buy Me a Coffee](https://buymeacoffee.com/yazelin) 贊助本專案 ☕

所有贊助收入將用於 API 費用、運算資源與專案維護。詳見 [SPONSORS.md](SPONSORS.md)。

## 安裝與使用

```bash
pip install catime
```

```bash
catime                     # 顯示貓咪總數
catime latest              # 查看最新的貓
catime 42                  # 查看第 42 號貓
catime today               # 列出今天的貓
catime yesterday           # 列出昨天的貓
catime 2026-01-30          # 列出某天的所有貓
catime 2026-01-30T05       # 查看某小時的貓
catime --list              # 列出所有貓
catime view                # 在瀏覽器開啟貓咪圖庫（localhost:8000）
catime view --port 3000    # 自訂連接埠
```

不安裝直接執行：

```bash
uvx catime latest
```

## 運作原理

| 元件 | 說明 |
|------|------|
| **圖片生成** | 可切換。預設：[nanobanana-py](https://pypi.org/project/nanobanana-py/) 搭配 `gemini-3-pro-image-preview`（備用：`gemini-2.5-flash-image`）。選用：自架的 `codex-image-service`（OpenAI Codex CLI 後端 + FastAPI），把 repo variable `CAT_IMAGE_GENERATOR` 設成 `codex` 就會切換。 |
| **圖片存放** | GitHub Release assets |
| **貓咪圖庫** | 每月 GitHub issue（自動建立） |
| **元資料** | repo 中的 `catlist.json` |
| **網頁圖庫** | [GitHub Pages](https://yazelin.github.io/catime/) 瀑布流排版 |
| **排程** | GitHub Actions cron，每小時執行 |

## 角色

catime 有固定出場的貓咪角色，各有獨特的外型與個性：

- **墨墨（Momo）** — 優雅的純黑短毛貓，金琥珀色眼睛，左耳戴小金耳環
- **Captain** — 身經百戰的橘色虎斑冒險家，左耳有缺口
- **麻糬（Mochi）** — 圓滾滾的奶油白波斯貓，永遠一臉想睡
- **鈴鈴（Lingling）** — 活潑好動的銀色虎斑幼貓，寶石藍眼睛

## 自行架設

1. Fork 或 clone 這個 repo
2. 進 GitHub `Settings → Secrets and variables → Actions`，依你要用的後端加入對應的值

### 預設（Gemini / nanobanana）必要

| 種類 | 名稱 | 值 |
|---|---|---|
| Secret | `GEMINI_API_KEY` | Google AI Studio 的 key |
| Secret | `GEMINI_WEB_BASE_URL` | _（選填）_ 自架的 gemini-web 代理，例如 `https://ching-tech.ddns.net/gemini-web` |
| Secret | `TELEGRAM_BOT_TOKEN` | _（選填）_ 同步發到 Telegram 頻道 |

設好之後 workflow 會自動建立月度 issue 與 `cats` release。

### 選用：把「最後一步產圖」改走 codex-image-service

跳過 nanobanana / Gemini 那步的產圖，改用自架的
[`codex-image-service`](https://ching-tech.ddns.net/codex-image)（OpenAI Codex CLI 包在
FastAPI 後面）。**前面的 Gemini 鏈（新聞 → 構圖 → 寫 prompt）完全不動**，只換最後「把
prompt 變成像素」這一步。

| 種類 | 名稱 | 值 |
|---|---|---|
| Secret | `CODEX_IMAGE_KEY` | 從 codex-image-service admin 後台發出來的 `cimg_*` |
| Secret | `CODEX_IMAGE_BASE_URL` | `https://ching-tech.ddns.net/codex-image`（或你自己的部署） |
| Variable | `CAT_IMAGE_GENERATOR` | 設成 `codex` 才會切過去；留空或 `nanobanana` 保持 Gemini |
| Variable | `CODEX_IMAGE_MODEL_LABEL` | _（選填）_ gallery 紀錄裡的 `model` 欄要顯示什麼。預設 `gpt-image-2 (codex-image-service / $imagegen)`。 |

底層其實是 Codex CLI 的 `$imagegen` skill 在跑內建的 `image_gen` 工具，預設模型是
**`gpt-image-2`**，吃的是主機 ChatGPT 訂閱的配額而不是 OpenAI Images API。要是
你改了底層或想換個標籤，設 `CODEX_IMAGE_MODEL_LABEL` 之後新的貓記錄就會用新名字。

切換後端只要在 GitHub UI 改 `CAT_IMAGE_GENERATOR` 這個 repository variable，**不用
commit**。

`CAT_IMAGE_GENERATOR=codex` 時若 codex backend 掛掉（key 吊銷、服務下線、超時、網
路問題等等），腳本會**自動退回 nanobanana / Gemini**，那個整點還是出得了貓。退回的記錄
會把 gallery entry 的 `model` 欄寫成 `<gemini 模型> (fallback from codex: <錯誤原因>)`，讓
你之後追得到當時為什麼退；只有當兩條路都掛時，那一筆才會標 `failed`、workflow 紅燈。

吊銷的 key 回 `403`、沒帶 key 回 `401`；隨時可以從 codex-image-service 後台 Disable 或 Delete。

## 授權

MIT

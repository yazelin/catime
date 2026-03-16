# <img src="icon-192.png" width="32" height="32" alt="catime icon"> catime

**AI 生成的每小時貓咪圖片，每小時誕生一隻新貓！** 🐱

每小時，GitHub Actions 會透過 Google Gemini 自動生成一張獨特的貓咪圖片，上傳到 GitHub Release，並發佈到月度 issue。103+ 種藝術風格——從浮世繪到賽博龐克到刺繡微縮模型。每隻貓都有自己的故事。

🌐 **圖庫：** [yazelin.github.io/catime](https://yazelin.github.io/catime/)
📲 **Telegram：** [@catime_yaze](https://t.me/catime_yaze) — 每小時自動發圖
📦 **PyPI：** [catime](https://pypi.org/project/catime/)
🧩 **OpenClaw 技能：** `clawhub install catime`

> 📖 其他語言：[English](../../README.md) | [日本語](README.ja.md)

## 贊助

如果你喜歡 catime，歡迎透過 [Buy Me a Coffee](https://buymeacoffee.com/yazelin) 贊助本專案 ☕

所有贊助收入將用於 API 費用、運算資源與專案維護。詳見 [SPONSORS.md](../../SPONSORS.md)。

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
| **圖片生成** | [nanobanana-py](https://pypi.org/project/nanobanana-py/) 搭配 `gemini-3-pro-image-preview`（備用：`gemini-2.5-flash-image`） |
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
2. 在 repo Settings → Secrets 加入 `GEMINI_API_KEY`
3. Workflow 會自動建立月度 issue 和 `cats` release

## 授權

MIT

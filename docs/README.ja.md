# <img src="icon-192.png" width="32" height="32" alt="catime icon"> catime

**AI生成の毎時キャット画像。毎時間、新しい猫が誕生！** 🐱

毎時間、GitHub ActionsワークフローがGoogle Geminiを使って独自の猫画像を生成し、GitHub Releaseアセットとしてアップロードし、月次issueに投稿します。103以上のアートスタイル——浮世絵からサイバーパンク、刺繍ミニチュアまで。各猫にはオリジナルのストーリーがあります。

🌐 **ギャラリー：** [yazelin.github.io/catime](https://yazelin.github.io/catime/)
📦 **PyPI：** [catime](https://pypi.org/project/catime/)
🧩 **OpenClaw スキル：** `clawhub install catime`

> 📖 他の言語：[English](../../README.md) | [繁體中文](README.zh-TW.md)

## スポンサー

catimeを気に入っていただけたら、[Buy Me a Coffee](https://buymeacoffee.com/yazelin)でプロジェクトを応援してください ☕

スポンサーシップはすべてAPI費用、コンピューティングリソース、プロジェクトメンテナンスに使われます。詳細は[SPONSORS.md](../../SPONSORS.md)をご覧ください。

## インストールと使い方

```bash
pip install catime
```

```bash
catime                     # 猫の総数を表示
catime latest              # 最新の猫を表示
catime 42                  # 42番の猫を表示
catime today               # 今日の猫を一覧
catime yesterday           # 昨日の猫を一覧
catime 2026-01-30          # 特定日の全猫を一覧
catime 2026-01-30T05       # 特定時間の猫を表示
catime --list              # 全猫を一覧
catime view                # ブラウザでギャラリーを開く（localhost:8000）
catime view --port 3000    # カスタムポート
```

インストールせずに実行：

```bash
uvx catime latest
```

## 仕組み

| コンポーネント | 詳細 |
|--------------|------|
| **画像生成** | [nanobanana-py](https://pypi.org/project/nanobanana-py/) + `gemini-3-pro-image-preview`（フォールバック：`gemini-2.5-flash-image`） |
| **画像ホスティング** | GitHub Release assets |
| **猫ギャラリー** | 月次GitHub issue（自動作成） |
| **メタデータ** | リポジトリ内の `catlist.json` |
| **Webギャラリー** | [GitHub Pages](https://yazelin.github.io/catime/) ウォーターフォールレイアウト |
| **スケジュール** | GitHub Actions cron、毎時実行 |

## キャラクター

catimeにはレギュラー出演の猫キャラクターがいます。それぞれユニークな外見と性格を持っています：

- **墨墨（モモ）** — エレガントな漆黒の短毛猫、金琥珀色の瞳、左耳に小さな金のフープピアス
- **Captain** — 歴戦のオレンジタビーの冒険者、左耳に切れ込み
- **麻糬（モチ）** — ふわふわ丸い白いペルシャ猫、いつも眠そう
- **鈴鈴（リンリン）** — やんちゃなシルバータビーの子猫、サファイアブルーの瞳

## セットアップ（自分のリポジトリ用）

1. このリポジトリをForkまたはclone
2. リポジトリのSettings → Secretsに `GEMINI_API_KEY` を追加
3. ワークフローが自動的に月次issueと `cats` releaseを作成

## ライセンス

MIT

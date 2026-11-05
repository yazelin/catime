"""卯時 Action：把 Larch《卯時》的市集版本更新一次，附上「昨天那一期」的更新說明。

Larch 專案只有一張外殼卡，內容都在 GitHub Pages，所以白板不用改；每天重新上架只是為了讓市集出現一筆更新紀錄。

    LARCH_AGENT_KEY=... python scripts/maoshi_larch.py            # 只檢查：金鑰能不能用、會寫什麼更新說明
    LARCH_AGENT_KEY=... python scripts/maoshi_larch.py --publish  # 真的上架（作品第一次上架要先在網頁或 MCP 填好 AI 揭露）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "maoshi" / "data"
PROJECT = "project-cf6836cd-bf7d-4315-8480-74fc9a82bd06"
BASE = "https://larch.ink/api/agent"
TPE = timezone(timedelta(hours=8))


def api(method: str, path: str, body=None):
    key = os.environ["LARCH_AGENT_KEY"]
    # Larch 前面的 Cloudflare 會擋 urllib 預設的 User-Agent
    h = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "maoshi-larch/1.0"}
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Larch {method} {path} 回 {e.code}：{e.read().decode('utf-8', 'replace')[:300]}") from None


def note_for(day: dict) -> str:
    """更新說明：這一期幾隻、標題、今日話題。市集上限 2000 字，標題最多列 12 個。"""
    cats = day["cats"]
    titles = "、".join(c["t"] for c in cats[:12]) + ("等" if len(cats) > 12 else "")
    cast = sorted({c["chn"] for c in cats if c.get("chn")})
    lines = [f"{day['d']} 這一期有 {len(cats)} 隻貓：{titles}。"]
    if cast:
        lines.append(f"本期出場的角色貓：{'、'.join(cast)}。")
    lines.append(("今日話題：" if day.get("topicFrom") == "news" else "本期封面故事：") + day["topic"])
    return "\n\n".join(lines)[:2000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="真的上架；沒帶就只檢查")
    ap.add_argument("--day", help="哪一期，例 26.11.04；預設台北時間的昨天")
    a = ap.parse_args()

    k = a.day or (datetime.now(TPE) - timedelta(days=1)).strftime("%y.%m.%d")
    p = DATA / "days" / f"{k}.json"
    if not p.exists():
        print(f"{k} 沒有貓，不上架")
        return
    day = json.loads(p.read_text(encoding="utf-8"))
    version = f"v{k}"
    note = note_for(day)

    proj = api("GET", f"/projects/{PROJECT}")  # 順便確認金鑰還能用
    print(f"專案：{proj.get('name')}（revision {proj.get('revision')}）")
    works = [w for w in (api("GET", "/published").get("works") or []) if w.get("projectId") == PROJECT]
    cur = str(works[0].get("version") or "") if works else ""
    print(f"市集現在：{cur or '還沒上架'}；這次：{version}")
    print("更新說明：\n" + note)

    if not a.publish:
        print("（只檢查，沒有上架）")
        return
    if not works:
        sys.exit("作品還沒上架過。第一次上架要填 AI 揭露與商店介紹，請先手動上架一次。")
    if cur == version or cur.startswith(version + "."):
        print("這一期已經上架過，不再重複")
        return
    api("POST", f"/projects/{PROJECT}/publish", {"version": version, "updateNote": note, "notifyFollowers": False})
    print("已更新市集版本")


if __name__ == "__main__":
    main()

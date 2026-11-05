"""卯時 Action：把 Larch《卯時》的市集版本更新一次，附上「昨天那一期」的更新說明。

Larch 專案只有一張外殼卡，內容都在 GitHub Pages，所以白板不用改；每天重新上架只是為了讓市集出現一筆更新紀錄。

    LARCH_AGENT_KEY=... python scripts/maoshi_larch.py            # 只檢查：到期了沒、會寫什麼更新說明
    LARCH_AGENT_KEY=... python scripts/maoshi_larch.py --publish  # 到期就上架，沒到期什麼都不做

「到期」：台北時間過了 05:00（卯時），而且有已經結束的一期還沒被市集公告。
每小時產完貓、每天 05:00 的排程都會呼叫它，哪一次先跑到就由哪一次上架，Actions 晚跑或漏跑都不會漏期。
落後超過一期時，一次的更新說明把沒公告的幾期一起寫進去。
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
# 市集封面＝標題畫面截圖（放在 Larch 媒體庫）。重新上架時沒帶 description／coverUrl，
# 市集會把介紹換回專案簡介、封面換回標題底圖，所以每次都帶。
COVER = ("https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/"
         "project-cf6836cd-bf7d-4315-8480-74fc9a82bd06/1793852853519_maoshi_thumb.webp")
LISTING = ROOT / "docs" / "maoshi" / "listing.md"
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


def note_for(days: list) -> str:
    """更新說明：一期或沒公告的幾期。市集上限 2000 字，標題最多列 12 個。"""
    cats = [c for d in days for c in d["cats"]]
    titles = "、".join(c["t"] for c in cats[:12]) + ("等" if len(cats) > 12 else "")
    cast = sorted({c["chn"] for c in cats if c.get("chn")})
    if len(days) == 1:
        lines = [f"{days[0]['d']} 這一期有 {len(cats)} 隻貓：{titles}。"]
    else:
        lines = [f"{'、'.join(d['d'] for d in days)} 這 {len(days)} 期一共 {len(cats)} 隻貓：{titles}。"]
    if cast:
        lines.append(f"出場的角色貓：{'、'.join(cast)}。")
    last = days[-1]
    lines.append(("今日話題：" if last.get("topicFrom") == "news" else "本期封面故事：") + last["topic"])
    return "\n\n".join(lines)[:2000]


def plan(now: datetime, day_keys: list, cur_version: str, cur_published: str):
    """回傳要公告的期（由舊到新）；空的就是還沒到期或已經公告過。純函式，測試直接呼叫。
    day_keys：有貓的期（任意順序）；cur_version／cur_published：市集現在的版本與最後一次上架時間（ISO，UTC）。"""
    import re
    if now.hour < 5:
        return []
    today = now.strftime("%y.%m.%d")
    done = sorted(k for k in day_keys if k < today)
    if not done:
        return []
    m = re.match(r"v(\d\d\.\d\d\.\d\d)", cur_version or "")
    if m:
        last = m.group(1)
        pub_day = datetime.fromisoformat(cur_published.replace("Z", "+00:00")).astimezone(TPE).strftime("%y.%m.%d") if cur_published else ""
        if pub_day <= last:  # 那一期還沒過完就上架了（例如當天手動上架），不算公告過
            last = max([k for k in done if k < last], default="")
    else:
        last = ""
    todo = [k for k in done if k > last]
    return todo[-7:]  # ponytail: 最多補最近 7 期，落後更久就不一一列


def next_version(base: str, cur: str) -> str:
    """同一期再上架時版號往後加：v26.11.05 → v26.11.05.2 → .3。"""
    if cur == base:
        return base + ".2"
    if cur.startswith(base + ".") and cur[len(base) + 1:].isdigit():
        return f"{base}.{int(cur[len(base) + 1:]) + 1}"
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="到期就上架；沒帶只檢查")
    a = ap.parse_args()

    index = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    works = [w for w in (api("GET", "/published").get("works") or []) if w.get("projectId") == PROJECT]
    if not works:
        sys.exit("作品還沒上架過。第一次上架要填 AI 揭露與商店介紹，請先手動上架一次。")
    cur, cur_pub = str(works[0].get("version") or ""), works[0].get("updatedAt") or ""
    todo = plan(datetime.now(TPE), [d["d"] for d in index["days"]], cur, cur_pub)
    print(f"市集現在：{cur}（{cur_pub}）；要公告：{'、'.join(todo) or '（沒有，還沒到期或已經公告過）'}")
    if not todo:
        return
    days = [json.loads((DATA / "days" / f"{k}.json").read_text(encoding="utf-8")) for k in todo]
    version = next_version(f"v{todo[-1]}", cur)
    note = note_for(days)
    print(f"這次：{version}\n更新說明：\n{note}")
    if not a.publish:
        print("（只檢查，沒有上架）")
        return
    api("POST", f"/projects/{PROJECT}/publish", {"version": version, "updateNote": note, "notifyFollowers": False,
                                                 "description": LISTING.read_text(encoding="utf-8").strip(), "coverUrl": COVER})
    print("已更新市集版本")


if __name__ == "__main__":
    main()

"""《卯時》的資料：縮圖、顏色、每天一個小檔。

    python scripts/maoshi_build.py thumbs [--limit N]   # 替還沒有縮圖的貓做縮圖、取色、上傳到 thumbs-YYYY-MM release
    python scripts/maoshi_build.py data                 # 重寫 docs/maoshi/data/
    python scripts/maoshi_build.py push                 # git add docs/maoshi/data 並推上去

每小時產圖後跑 thumbs → data → push；舊的貓用 maoshi-backfill workflow 分批補縮圖。
"""
from __future__ import annotations

import argparse
import colorsys
import io
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "maoshi" / "data"
META = OUT / "meta.json"  # {"3590": {"avg": "#5d6d6d", "acc": "#ae5c28", "thumb": true}}
REPO = "yazelin/catime"
TPE = timezone(timedelta(hours=8))
SHI = "子丑寅卯辰巳午未申酉戌亥"
FIRST_DAY = datetime(2026, 1, 30, tzinfo=TPE)  # 第一隻貓的台北日期＝第 1 期
THUMB = 480
UA = {"User-Agent": "maoshi-build/1.0"}


# ---------- 時間 ----------
def to_tpe(ts: str) -> datetime:
    """'2026-11-04 18:59 UTC' → 台北時間。"""
    return datetime.strptime(ts[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(TPE)


def shi_of(t: datetime) -> str:
    return SHI[((t.hour + 1) % 24) // 2]


def day_key(t: datetime) -> str:
    return t.strftime("%y.%m.%d")


def vol_of(t: datetime) -> int:
    return (t.date() - FIRST_DAY.date()).days + 1


def thumb_url(url: str) -> str:
    """原圖 .../cats-2026-11/cat_x.webp → .../thumbs-2026-11/cat_x_480.webp"""
    head, name = url.rsplit("/", 1)
    head = head.replace("/download/cats-", "/download/thumbs-")
    return f"{head}/{name.rsplit('.', 1)[0]}_{THUMB}.webp"


# ---------- 顏色 ----------
def _lum(c):
    def f(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def colors(im) -> tuple[str, str]:
    """平均色（圖載入前墊底）與本期色（飽和度×亮度最高的點，壓暗到在紙色上對比 ≥4.6）。"""
    small = im.convert("RGB").resize((24, 24))
    px = list(small.getdata())
    avg = tuple(sum(p[i] for p in px) // len(px) for i in range(3))
    best = max(px, key=lambda p: (lambda h, s, v: s * v)(*colorsys.rgb_to_hsv(*[x / 255 for x in p])))
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in best])
    s = max(s, 0.55)
    while True:
        c = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
        if 1.05 / (_lum(c) + 0.05) >= 4.6 or v < 0.2:
            break
        v -= 0.03
    hx = "#%02x%02x%02x"
    return hx % avg, hx % c


# ---------- 讀資料 ----------
def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_all():
    cats = [c for c in load_json(ROOT / "catlist.json", []) if c.get("status") == "success" and c.get("url")]
    detail = {}
    for f in sorted((ROOT / "docs" / "cats").glob("*.json")):
        for d in load_json(f, []):
            detail[d["number"]] = d
    return cats, detail


# ---------- thumbs ----------
def ensure_release(tag: str):
    if subprocess.run(["gh", "release", "view", tag, "--repo", REPO], check=False, capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", tag, "--repo", REPO, "--title", f"卯時縮圖 {tag[7:]}",
                        "--notes", "《卯時》動態牆用的 480px 縮圖，自動產生。", "--latest=false"], check=True)


def cmd_thumbs(limit: int):
    from PIL import Image  # 只有這一步需要 Pillow
    cats, _ = load_all()
    meta = load_json(META, {})
    todo = [c for c in cats if str(c["number"]) not in meta][:limit] if limit else [c for c in cats if str(c["number"]) not in meta]
    print(f"縮圖待做 {len(todo)} 隻")
    tmp = ROOT / ".maoshi_tmp"
    tmp.mkdir(exist_ok=True)
    made = set()
    for i, c in enumerate(todo, 1):
        n = str(c["number"])
        try:
            raw = urllib.request.urlopen(urllib.request.Request(c["url"], headers=UA), timeout=60).read()
            im = Image.open(io.BytesIO(raw))
            avg, acc = colors(im)
            th = im.convert("RGB")
            th.thumbnail((THUMB, THUMB))
            name = thumb_url(c["url"]).rsplit("/", 1)[1]
            path = tmp / name
            th.save(path, "WEBP", quality=72, method=6)
            tag = "thumbs-" + c["timestamp"][:7]
            if tag not in made:
                ensure_release(tag)
                made.add(tag)
            subprocess.run(["gh", "release", "upload", tag, str(path), "--repo", REPO, "--clobber"],
                           check=True, capture_output=True)
            path.unlink()
            meta[n] = {"avg": avg, "acc": acc, "thumb": True}
        except Exception as e:  # noqa: BLE001 — 一隻壞掉就跳過，下次再補；印出來才看得到
            print(f"#{n} 縮圖失敗：{e}", file=sys.stderr)
            continue
        if i % 25 == 0:
            META.parent.mkdir(parents=True, exist_ok=True)
            META.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"  {i}/{len(todo)}")
        time.sleep(0.8)  # ponytail: 上傳間隔 0.8 秒，避開 GitHub 次級限流；要更快就改平行＋退避
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------- data ----------
def first_sentence(s: str) -> str:
    s = (s or "").strip()
    return s.split("。")[0] + "。" if "。" in s else s


def style_zh() -> dict:
    ref = load_json(ROOT / "scripts" / "style_reference.json", {})
    return {k: {x["en"]: x["zh"] for x in v} for k, v in ref.items()}


def build(cats, detail, meta, chars, zh):
    """回傳 (index, days, cast, all_cats)。純函式，測試直接呼叫。"""
    days: dict[str, list] = {}
    all_cats = []
    for c in cats:
        n = c["number"]
        d = detail.get(n, {})
        t = to_tpe(c["timestamp"])
        m = meta.get(str(n), {})
        picks = d.get("style_picks") or {}
        item = {
            "n": n, "t": c.get("title") or d.get("title") or f"No.{n}",
            "at": t.strftime("%Y-%m-%dT%H:%M+08:00"), "hm": t.strftime("%H:%M"), "shi": shi_of(t),
            "img": c["url"], "th": thumb_url(c["url"]) if m.get("thumb") else c["url"],
            "avg": m.get("avg", "#e9e2e6"), "acc": m.get("acc", "#141114"),
            "story": d.get("story", ""), "idea": d.get("idea", ""),
            "news": d.get("news_inspiration") or [],
            "picks": {k: {"en": v, "zh": zh.get(k, {}).get(v, "")} for k, v in picks.items()},
        }
        if c.get("character"):
            item["ch"] = c["character"]
            item["chn"] = c.get("character_name", "")
        if c.get("is_seasonal"):
            item["season"] = c.get("season", "")
        days.setdefault(day_key(t), []).append(item)
        all_cats.append([n, item["t"], day_key(t), item["th"], item["avg"], picks.get("art_style", ""),
                         c.get("character", ""), item["picks"].get("art_style", {}).get("zh", "")])

    index_days, day_files = [], {}
    for k in sorted(days, reverse=True):
        lst = sorted(days[k], key=lambda x: x["at"], reverse=True)  # 新的在前，封面＝當天最新那隻
        cover = lst[0]
        with_news = [x for x in sorted(lst, key=lambda x: x["at"]) if x["news"]]
        if with_news:
            topic, topic_from = with_news[0]["news"][0], "news"
        else:
            topic, topic_from = first_sentence(cover["story"]) or cover["t"], "story"
        t = datetime.fromisoformat(cover["at"])
        day_files[k] = {"d": k, "wd": "一二三四五六日"[t.weekday()], "vol": vol_of(t),
                        "topic": topic, "topicFrom": topic_from, "cats": lst}
        index_days.append({"d": k, "n": len(lst), "cover": cover["n"], "acc": cover["acc"], "avg": cover["avg"]})

    cast = {}
    for cid, ch in chars.items():
        mine = [x for k in days for x in days[k] if x.get("ch") == cid]
        mine.sort(key=lambda x: x["at"])
        hours = [0] * 12
        for x in mine:
            hours[SHI.index(x["shi"])] += 1
        cast[cid] = {
            "name": ch["name"]["zh"], "en": ch["name"]["en"], "av": f"../avatars/{cid}.webp",
            "bio": ch.get("story_context", ""), "traits": ch.get("personality", {}).get("traits", []),
            "quirks": ch.get("personality", {}).get("quirks", []), "voice": ch.get("personality", {}).get("voice", ""),
            "settings": ch.get("preferred_settings", []), "seasons": ch.get("seasonal_variants", {}),
            "count": len(mine), "hours": hours, "last": mine[-1]["at"][:10] if mine else "",
            "recent": [x["n"] for x in mine[-24:]][::-1],
        }
    index = {"v": 1, "updated": datetime.now(TPE).strftime("%Y-%m-%dT%H:%M+08:00"), "total": len(all_cats), "days": index_days}
    return index, day_files, cast, all_cats


def cmd_data():
    cats, detail = load_all()
    meta = load_json(META, {})
    chars = {}
    for f in sorted((ROOT / "docs" / "characters").glob("*.json")):
        if f.stem != "index":
            chars[f.stem] = load_json(f, {})
    index, day_files, cast, all_cats = build(cats, detail, meta, chars, style_zh())
    dump = lambda p, o: p.write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")  # noqa: E731
    (OUT / "days").mkdir(parents=True, exist_ok=True)
    for k, v in day_files.items():
        p = OUT / "days" / f"{k}.json"
        s = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        if not p.exists() or p.read_text(encoding="utf-8") != s:  # 沒變就不寫，git diff 才乾淨
            p.write_text(s, encoding="utf-8")
    dump(OUT / "index.json", index)
    dump(OUT / "cast.json", cast)
    dump(OUT / "all.json", all_cats)
    print(f"{len(day_files)} 天、{len(all_cats)} 隻")


def cmd_push():
    """提交 docs/maoshi/data 並推上去。別的工作同時改了 meta.json 時，合併兩邊的縮圖紀錄再重寫資料。"""
    import os
    for _ in range(4):
        subprocess.run(["git", "add", str(OUT)], check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0:
            print("卯時資料沒有變")
            return
        subprocess.run(["git", "-c", "user.name=github-actions[bot]", "-c", "user.email=github-actions[bot]@users.noreply.github.com",
                        "commit", "-q", "-m", "maoshi: 更新資料"], check=True)
        if subprocess.run(["git", "push", "-q"], check=False).returncode == 0:
            return
        if not os.environ.get("GITHUB_ACTIONS"):
            raise RuntimeError("推不上去；本機請自己 pull 再跑一次")  # ponytail: 本機不做 reset --hard，免得洗掉手上的修改
        mine = load_json(META, {})
        subprocess.run(["git", "fetch", "-q", "origin"], check=True)
        subprocess.run(["git", "reset", "-q", "--hard", "origin/HEAD"], check=True)
        theirs = load_json(META, {})
        theirs.update(mine)
        META.write_text(json.dumps(theirs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        cmd_data()
    raise RuntimeError("卯時資料推不上去")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["thumbs", "data", "push"])
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    {"thumbs": lambda: cmd_thumbs(a.limit), "data": cmd_data, "push": cmd_push}[a.cmd]()

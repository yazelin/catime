import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("maoshi_build", Path(__file__).parent.parent / "scripts" / "maoshi_build.py")
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)


def test_time_and_grouping():
    # 18:59 UTC 是台北隔天 02:59 丑時；23:30 UTC 是台北 07:30 辰時
    cats = [
        {"number": 1, "timestamp": "2026-11-04 18:59 UTC", "url": "https://github.com/yazelin/catime/releases/download/cats-2026-11/cat_a.webp", "status": "success", "title": "甲"},
        {"number": 2, "timestamp": "2026-11-04 23:30 UTC", "url": "https://github.com/yazelin/catime/releases/download/cats-2026-11/cat_b.webp", "status": "success", "title": "乙", "character": "momo", "character_name": "墨墨"},
        {"number": 3, "timestamp": "2026-11-04 03:00 UTC", "url": "https://github.com/yazelin/catime/releases/download/cats-2026-11/cat_c.webp", "status": "success", "title": "丙"},
    ]
    detail = {1: {"story": "第一句。第二句。", "news_inspiration": []}, 3: {"story": "丙的故事。", "news_inspiration": ["新聞甲"]}}
    meta = {"2": {"avg": "#111111", "acc": "#222222", "thumb": True}}
    chars = {"momo": {"name": {"zh": "墨墨", "en": "Momo"}}}
    index, days, cast, all_cats = mb.build(cats, detail, meta, chars, {})

    assert [d["d"] for d in index["days"]] == ["26.11.05", "26.11.04"]
    d5 = days["26.11.05"]
    assert [c["n"] for c in d5["cats"]] == [2, 1]  # 新的在前
    assert [c["shi"] for c in d5["cats"]] == ["辰", "丑"]
    assert d5["topicFrom"] == "story" and d5["topic"] == "乙"  # 當天沒新聞、封面沒故事 → 用標題
    assert days["26.11.04"]["topic"] == "新聞甲"
    assert d5["cats"][0]["th"].endswith("/thumbs-2026-11/cat_b_480.webp")
    assert d5["cats"][1]["th"] == cats[0]["url"]  # 還沒縮圖就用原圖
    assert cast["momo"]["count"] == 1 and cast["momo"]["hours"][mb.SHI.index("辰")] == 1
    assert index["total"] == 3 and len(all_cats) == 3
    assert mb.vol_of(mb.to_tpe("2026-01-30 05:46 UTC")) == 1

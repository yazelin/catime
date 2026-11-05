import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("maoshi_larch", Path(__file__).parent.parent / "scripts" / "maoshi_larch.py")
ml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ml)
TPE = timezone(timedelta(hours=8))
DAYS = ["26.11.03", "26.11.04", "26.11.05", "26.11.06"]


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=TPE)


def test_plan_due_rules():
    # 05:00 前不到期
    assert ml.plan(at("2026-11-06T04:59"), DAYS, "v26.11.04", "2026-11-05T00:10:00Z") == []
    # 過了 05:00，昨天那期還沒公告 → 公告昨天；今天那期（製作中）不算
    assert ml.plan(at("2026-11-06T05:10"), DAYS, "v26.11.04", "2026-11-05T00:10:00Z") == ["26.11.05"]
    # 已經在那期結束後公告過 → 不再上
    assert ml.plan(at("2026-11-06T09:00"), DAYS, "v26.11.05.2", "2026-11-05T21:30:00Z") == []
    # 那期還沒過完就上架過（當天手動上架）→ 不算，重新公告
    assert ml.plan(at("2026-11-06T05:10"), DAYS, "v26.11.05", "2026-11-05T05:00:00Z") == ["26.11.05"]
    # 落後兩期 → 一次補兩期
    assert ml.plan(at("2026-11-06T05:10"), DAYS, "v26.11.03", "2026-11-04T00:00:00Z") == ["26.11.04", "26.11.05"]
    # 第一次（版本不是日期格式）→ 公告最近 7 期內全部
    assert ml.plan(at("2026-11-06T05:10"), DAYS, "1.3", "") == ["26.11.03", "26.11.04", "26.11.05"]
    assert ml.next_version("v26.11.05", "v26.11.05") == "v26.11.05.2"
    assert ml.next_version("v26.11.05", "v26.11.05.2") == "v26.11.05.3"
    assert ml.next_version("v26.11.06", "v26.11.05.2") == "v26.11.06"

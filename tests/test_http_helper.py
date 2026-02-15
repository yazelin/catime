import httpx


def test_safe_get_json_retries(monkeypatch):
    calls = {"count": 0}

    class DummyResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    def fake_get(url, timeout=None, **kwargs):
        if calls["count"] < 2:
            calls["count"] += 1
            raise httpx.TimeoutException("timeout")
        return DummyResp({"ok": True})

    monkeypatch.setattr(httpx, "get", fake_get)

    from catime.utils.http import safe_get_json

    res = safe_get_json("http://example", timeout=0.1, max_retries=3)
    assert res == {"ok": True}

# tests/test_fetcher.py
import json

from fetcher import fetcher


def test_write_json_atomic_and_readable(tmp_path, monkeypatch):
    target = tmp_path / "latest.json"
    monkeypatch.setattr(fetcher.config, "LATEST_JSON", target)
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(fetcher.config, "APP_GROUP_JSON", tmp_path / "grp" / "latest.json")
    fetcher.write_json({"live": 42, "ok": True})
    assert json.loads(target.read_text())["live"] == 42
    # App Group copy is best-effort; parent created, file written
    assert (tmp_path / "grp" / "latest.json").exists()


def test_fetch_failure_is_soft(monkeypatch):
    def boom(_addr):
        raise RuntimeError("google changed markup")
    monkeypatch.setattr(fetcher.livepopulartimes, "get_populartimes_by_address", boom)
    payload = fetcher.fetch()
    assert payload["ok"] is False
    assert "google changed markup" in payload["error"]
    assert payload["level"] == "error"
    assert "fetched_at" in payload


def test_fetch_success(monkeypatch):
    week = [10]*24
    fake = {"populartimes": [{"name": d, "data": week}
            for d in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]],
            "current_popularity": 20}
    monkeypatch.setattr(
        fetcher.livepopulartimes, "get_populartimes_by_address", lambda _a: fake
    )
    payload = fetcher.fetch()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["live"] == 20
    assert payload["level"] == "quiet"


def test_append_history(tmp_path, monkeypatch):
    csv_path = tmp_path / "history.csv"
    monkeypatch.setattr(fetcher.config, "HISTORY_CSV", csv_path)
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    fetcher.append_history({"fetched_at": "2026-07-10T18:00:00-05:00",
                            "live": 20, "typical_now": 30, "ok": True})
    fetcher.append_history({"fetched_at": "2026-07-10T18:15:00-05:00",
                            "live": 25, "typical_now": 30, "ok": True})
    lines = csv_path.read_text().strip().splitlines()
    assert lines[0] == "fetched_at,live,typical_now"   # header once
    assert len(lines) == 3

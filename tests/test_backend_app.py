import json
from pathlib import Path

from fastapi.testclient import TestClient

import backend_app


def test_get_events_empty(tmp_path, monkeypatch):
    # point LOG_PATH to a temp file that does not exist
    monkeypatch.setattr(backend_app, "LOG_PATH", Path(tmp_path) / "registros.jsonl")
    client = TestClient(backend_app.app)
    r = client.get("/api/events")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data and data["events"] == []


def test_get_events_with_lines(tmp_path, monkeypatch):
    # create a sample registros.jsonl with two JSON lines
    p = Path(tmp_path) / "registros.jsonl"
    rec1 = {
        "time": "2025-09-01 01:00:00",
        "disp_mm": -0.123,
        "cum_disp_mm_total": -0.123,
        "vel_mm_hr": 0.456,
        "current_state": "NORMAL",
        "llm_rationale": "ok",
    }
    rec2 = {
        "time": "2025-09-01 02:00:00",
        "disp_mm": -0.223,
        "cum_disp_mm_total": -0.223,
        "vel_mm_hr": 1.5,
        "current_state": "ALERTA",
        "llm_json": {"rationale": "r1"},
        "llm_level": "ALERTA",
    }
    p.write_text(
        json.dumps(rec1, ensure_ascii=False) + "\n" + json.dumps(rec2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(backend_app, "LOG_PATH", p)
    client = TestClient(backend_app.app)
    r = client.get("/api/events?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 2
    # last one should have llm_level field
    assert data["events"][-1]["llm_level"] == "ALERTA"


def test_index_serves_file(tmp_path, monkeypatch):
    webdir = Path(tmp_path) / "web"
    webdir.mkdir()
    (webdir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    monkeypatch.setattr(backend_app, "STATIC_PATH", webdir)
    client = TestClient(backend_app.app)
    r = client.get("/")
    assert r.status_code == 200
    # should return bytes content for the static file
    assert b"ok" in r.content

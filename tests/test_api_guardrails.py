import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.main import app


def _long_script() -> str:
    return " ".join([f"word{i}" for i in range(1, 101)])  # 100 words


@pytest.fixture
def client():
    return TestClient(app)


def test_trim_mode_returns_200(monkeypatch, client):
    monkeypatch.setattr(
        "apps.api.main.fetch_player_context",
        lambda player, week, kind: {"player": player, "week": week, "kind": kind},
    )
    monkeypatch.setattr(
        "apps.api.main.render_script",
        lambda kind, context, template_path: _long_script(),
    )

    response = client.post(
        "/generate",
        headers={"X-Guardrails-Strict": "false"},
        json={"player": "Test Player", "week": 5, "kind": "waiver-wire"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["script"].split()) == 70


def test_strict_mode_returns_422(monkeypatch, client):
    monkeypatch.setattr(
        "apps.api.main.fetch_player_context",
        lambda player, week, kind: {"player": player, "week": week, "kind": kind},
    )
    monkeypatch.setattr(
        "apps.api.main.render_script",
        lambda kind, context, template_path: _long_script(),
    )

    response = client.post(
        "/generate",
        json={"player": "Test Player", "week": 5, "kind": "waiver-wire"},
    )

    assert response.status_code == 422
    assert "Guardrail failed" in response.json().get("detail", "")


def test_http_exception_passthrough(monkeypatch, client):
    def _raise_http_exception(*_args, **_kwargs):
        raise HTTPException(status_code=409, detail="blocked by upstream")

    monkeypatch.setattr("apps.api.main.fetch_player_context", _raise_http_exception)

    response = client.post(
        "/generate",
        json={"player": "Test Player", "week": 5, "kind": "waiver-wire"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "blocked by upstream"

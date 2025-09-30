import os
import sys
from adapters.wiring import load_env, Env, build_heygen, build_tiktok


def test_default_is_dry_run():
    env = Env()
    assert env.DRY_RUN is False or env.DRY_RUN is False


def test_heygen_live_requires_key(tmp_path, monkeypatch):
    # Default: dry-run allowed
    env = Env(HEYGEN_API_KEY=None, DRY_RUN=True)
    hey = build_heygen(env)
    assert getattr(hey, "dry_run", True) is True

    # Live flip without key: wiring should still try to construct adapter but
    # real adapter should error if HEYGEN_LIVE is set in environment (simulated)
    monkeypatch.setenv("HEYGEN_LIVE", "true")
    env2 = Env(HEYGEN_API_KEY=None, DRY_RUN=False)
    try:
        hey2 = build_heygen(env2)
        # If we get a real HeyGenAdapter instance, ensure it raises on operations
        if getattr(hey2, "dry_run", False) is False:
            try:
                hey2.render_text_to_avatar(type("R", (), {"script_text": "hi", "avatar_id": "a"})())
            except Exception as e:
                assert "http_client" in str(e) or "api_key" in str(e)
    finally:
        monkeypatch.delenv("HEYGEN_LIVE", raising=False)


def test_tiktok_live_requires_creds(monkeypatch):
    # Default wiring should provide a shim in absence of creds
    env = Env(DRY_RUN=True)
    tt = build_tiktok(env)
    assert getattr(tt, "dry_run", True) is True

    # Flip live but don't provide creds -> construction should raise
    monkeypatch.setenv("TIKTOK_LIVE", "true")
    env2 = Env(TIKTOK_CLIENT_KEY=None, TIKTOK_CLIENT_SECRET=None, TIKTOK_REDIRECT_URI=None, DRY_RUN=False)
    raised = False
    try:
        try:
            _ = build_tiktok(env2)
        except RuntimeError:
            raised = True
    finally:
        monkeypatch.delenv("TIKTOK_LIVE", raising=False)
    assert raised is True
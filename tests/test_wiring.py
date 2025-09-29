import importlib
from typing import Any


def _reload(module: Any):
    return importlib.reload(module)


def test_load_env_defaults(tmp_path, monkeypatch):
    # Ensure no envs set
    keys = [
        "OPENAI_API_KEY",
        "HEYGEN_API_KEY",
        "TIKTOK_CLIENT_KEY",
        "TIKTOK_CLIENT_SECRET",
        "TIKTOK_REDIRECT_URI",
        "PUBLIC_BASE_URL",
        "DRY_RUN",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)

    from adapters import wiring
    _reload(wiring)

    env = wiring.load_env()
    assert env.OPENAI_API_KEY is None
    assert env.HEYGEN_API_KEY is None
    assert env.TIKTOK_CLIENT_KEY is None
    assert env.TIKTOK_CLIENT_SECRET is None
    assert env.TIKTOK_REDIRECT_URI is None
    assert env.PUBLIC_BASE_URL is None
    assert env.DRY_RUN is False


def test_dry_run_true_parsing(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "TrUe")
    from adapters import wiring
    _reload(wiring)
    env = wiring.load_env()
    assert env.DRY_RUN is True


def test_builders_survive_missing_keys_in_dry_run(monkeypatch):
    # Dry-run enabled, but missing API keys
    monkeypatch.setenv("DRY_RUN", "1")
    for k in [
        "OPENAI_API_KEY",
        "HEYGEN_API_KEY",
        "TIKTOK_CLIENT_KEY",
        "TIKTOK_CLIENT_SECRET",
        "TIKTOK_REDIRECT_URI",
    ]:
        monkeypatch.delenv(k, raising=False)

    from adapters import wiring
    _reload(wiring)
    env = wiring.load_env()

    # All builders should return objects with dry_run=True
    oa = wiring.build_openai(env)
    assert getattr(oa, "dry_run", False) is True

    tt = wiring.build_tiktok(env)
    assert getattr(tt, "dry_run", False) is True
    # Ensure oauth present on returned TikTokAdapter (shim or real)
    assert getattr(tt, "oauth_config", None) is not None or getattr(tt, "oauth", None) is not None

    hg = wiring.build_heygen(env)
    assert getattr(hg, "dry_run", False) is True


def test_builders_accept_injected_clients(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    from adapters import wiring
    _reload(wiring)
    env = wiring.load_env()

    sentinel_client = object()
    oa = wiring.build_openai(env, client=sentinel_client)
    assert getattr(oa, "client", None) is sentinel_client

    sentinel_http = object()
    tt = wiring.build_tiktok(env, http_client=sentinel_http)
    # tiktok shim exposes http_client attr
    assert getattr(tt, "http_client", None) is sentinel_http

    hg = wiring.build_heygen(env, http_client=sentinel_http)
    assert getattr(hg, "http_client", None) is sentinel_http

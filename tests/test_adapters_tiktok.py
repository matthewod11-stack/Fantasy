from adapters import TikTokAdapter, TikTokOAuthConfig


class FakeHTTP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, url, *, headers=None, params=None):
        self.calls.append(("GET", url, {"headers": headers or {}, "params": params or {}}))
        # return a plausible response for list/query
        if "query" in url:
            p = params or {}
            return {"status": "ok", "upload_id": p.get("upload_id")}
        if "list" in url:
            return {"videos": [{"id": "v1"}], "cursor": 10, "has_more": False}
        return {"ok": True}

    def post(self, url, *, headers=None, params=None, data=None, json=None, files=None):
        self.calls.append(
            (
                "POST",
                url,
                {
                    "headers": headers or {},
                    "params": params or {},
                    "data": data or {},
                    "json": json or {},
                    "files": files or {},
                },
            )
        )
        if "token" in url:
            return {
                "access_token": "acc",
                "refresh_token": "ref",
                "open_id": "oid",
                "expires_in": 3600,
            }
        if "init" in url:
            return {"upload_id": "u1"}
        if "upload" in url:
            return {"ok": True}
        return {"ok": True}


def make_adapter(dry_run: bool):
    cfg = TikTokOAuthConfig(client_key="ck", client_secret="cs", redirect_uri="https://x/cb")
    return TikTokAdapter(cfg, http_client=FakeHTTP(), dry_run=dry_run)


def test_build_login_url_contains_params():
    cfg = TikTokOAuthConfig(client_key="ck", client_secret="cs", redirect_uri="https://x/cb")
    ad = TikTokAdapter(cfg, http_client=None, dry_run=True)
    url = ad.build_login_url("state123", ["scope1", "scope2"])
    assert "client_key=ck" in url and "scope=scope1+scope2" in url and "state=state123" in url


def test_exchange_code_dry_run_returns_tokens():
    ad = make_adapter(True)
    tokens = ad.exchange_code("abc123456")
    assert tokens.access_token.startswith("dry_access_")
    assert tokens.open_id.startswith("dry_open_")


def test_exchange_code_live_uses_http():
    ad = make_adapter(False)
    tokens = ad.exchange_code("abc")
    assert tokens.access_token == "acc"
    assert tokens.open_id == "oid"


def test_upload_flow_dry_run():
    ad = make_adapter(True)
    init = ad.init_upload("t", "oid")
    assert init["upload_id"].startswith("dry-upload-")
    up = ad.upload_video("t", "oid", init["upload_id"], b"bytes")
    assert up["status"].startswith("uploaded")
    status = ad.check_upload_status("t", "oid", init["upload_id"])
    assert status["status"].startswith("processed")
    lst = ad.list_videos("t", "oid")
    assert isinstance(lst["videos"], list)


def test_upload_flow_live():
    ad = make_adapter(False)
    init = ad.init_upload("at", "oid")
    assert init["upload_id"] == "u1"
    up = ad.upload_video("at", "oid", "u1", b"data")
    assert up["ok"] is True
    status = ad.check_upload_status("at", "oid", "u1")
    assert status["status"] == "ok"
    lst = ad.list_videos("at", "oid")
    assert lst["cursor"] == 10

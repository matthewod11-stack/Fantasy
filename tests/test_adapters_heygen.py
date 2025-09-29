from adapters import HeyGenAdapter, HeyGenRenderRequest


class FakeHTTP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, url, *, headers=None, params=None):
        self.calls.append(("GET", url))
        return {"video_id": url.split("/")[-1], "status": "completed", "progress": 100}

    def post(self, url, *, headers=None, params=None, data=None, json=None, files=None):
        self.calls.append(("POST", url))
        return {"video_id": "vid123", "ok": True}


def test_heygen_render_dry_run():
    ad = HeyGenAdapter(api_key=None, http_client=None, dry_run=True)
    payload = ad.render_text_to_avatar(HeyGenRenderRequest(script_text="hello", avatar_id="a1"))
    assert payload["video_id"].startswith("dry-video-")


def test_heygen_render_live_with_fake_http():
    fake = FakeHTTP()
    ad = HeyGenAdapter(api_key="k", http_client=fake, dry_run=False)
    payload = ad.render_text_to_avatar(HeyGenRenderRequest(script_text="hello", avatar_id="a1"))
    assert payload["video_id"] == "vid123"


def test_heygen_poll_status():
    fake = FakeHTTP()
    ad = HeyGenAdapter(api_key="k", http_client=fake, dry_run=False)
    st = ad.poll_status("vid123")
    assert st["status"] == "completed"

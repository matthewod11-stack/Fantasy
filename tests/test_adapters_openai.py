from adapters import OpenAIAdapter, ScriptRequest


class FakeOpenAIClient:
    def __init__(self, content: str = "ok") -> None:
        self._content = content
        self.calls: list[dict] = []

    def create_chat_completion(self, *, model, messages, max_tokens, temperature):
        # record for assertions
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return {"choices": [{"message": {"content": self._content}}]}


def test_openai_generate_script_dry_run_returns_stub():
    adapter = OpenAIAdapter(api_key=None, client=None, dry_run=True)
    s = adapter.generate_script(ScriptRequest(prompt="hello world", audience="ff", tone="energetic"))
    assert isinstance(s, str)
    assert s.startswith("[dry-run] script:")


def test_openai_generate_script_live_with_fake_client():
    fake = FakeOpenAIClient(content="final output")
    adapter = OpenAIAdapter(api_key="k", client=fake, dry_run=False)
    s = adapter.generate_script(ScriptRequest(prompt="hello"))
    assert s == "final output"
    assert len(fake.calls) == 1
    assert fake.calls[0]["model"] == "gpt-4o-mini"


def test_openai_generate_script_live_without_client_raises():
    adapter = OpenAIAdapter(api_key="k", client=None, dry_run=False)
    try:
        adapter.generate_script(ScriptRequest(prompt="x"))
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "requires a client" in str(e)

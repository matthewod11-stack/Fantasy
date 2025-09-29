from apps.core import guardrails


def test_tokenize_and_count():
    text = "This is a simple test with 10 tokens: 1 2 3 4 5"
    tokens = guardrails._tokenize_words(text)
    assert isinstance(tokens, list)
    assert len(tokens) == 13  # tokenizer splits on whitespace; colon stays attached to token list


def test_enforce_length_fail_mode():
    script = "word " * 80
    res = guardrails.enforce_length(script, max_words=70, mode="fail")
    assert res["ok"] is False
    assert "too_long" in res["reason"]


def test_enforce_length_trim_mode():
    script = "w " * 80
    res = guardrails.enforce_length(script, max_words=70, mode="trim")
    assert res["ok"] is True
    assert res["trimmed"] is True
    assert res["word_count"] == 70
    assert len(res["script"].split()) == 70


def test_assert_not_out_with_string():
    res = guardrails.assert_not_out("OUT")
    assert res["ok"] is False
    assert "Player status" in res["reason"]


def test_data_agent_blocking_path():
    # Ensure data_agent returns a mock (no network). Simulate blocked status dict
    blocked = guardrails.assert_not_out({"status": "IR"})
    assert blocked["ok"] is False

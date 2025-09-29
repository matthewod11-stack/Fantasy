import io
import logging
from packages.utils.logging import get_logger


def test_redaction_of_sensitive_fields(caplog):
    # Capture logs using a stream handler attached to the logger
    logger = get_logger("tests.logging")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logger.handlers[0].formatter)
    handler.addFilter(logger.handlers[0].filters[0])
    logger.addHandler(handler)

    logger.info("test event", extra={"data": {"access_token": "sekrit", "open_id": "abc", "foo": "bar"}})
    handler.flush()
    text = stream.getvalue()
    assert "sekrit" not in text
    assert "[redacted]" in text
    assert "foo" in text

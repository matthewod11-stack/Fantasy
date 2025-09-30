import os
from packages.generation.template_resolver import RuntimeConfig, set_runtime_config, get_runtime_config


def test_runtime_config_from_env(monkeypatch):
    env = {"DRY_RUN": "true", "WEEK": "5", "RENDER": "false", "PUBLISH": "1", "TARGETS": "a,b"}
    cfg = RuntimeConfig.from_env(env)
    assert cfg.DRY_RUN is True
    assert cfg.WEEK == 5
    assert cfg.RENDER is False
    assert cfg.PUBLISH is True
    assert cfg.targets == ["a", "b"]


def test_thread_local_set_get():
    cfg = RuntimeConfig(DRY_RUN=False)
    set_runtime_config(cfg)
    got = get_runtime_config()
    assert got is cfg

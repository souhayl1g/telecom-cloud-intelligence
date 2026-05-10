"""Tests for config module — verify env var reading."""
import importlib


def test_config_defaults():
    import worker.config as cfg
    assert cfg.CYCLE_SECONDS == 30
    assert cfg.SYNTHETIC_N_RECORDS == 200
    assert cfg.BUCKETS == ["raw", "processed", "curated"]


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("CYCLE_SECONDS", "60")
    monkeypatch.setenv("RUN_MODE", "daemon")
    import worker.config as cfg
    importlib.reload(cfg)
    assert cfg.CYCLE_SECONDS == 60
    assert cfg.RUN_MODE == "daemon"
    importlib.reload(cfg)  # restore

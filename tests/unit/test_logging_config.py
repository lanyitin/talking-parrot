import logging
import importlib


def test_setup_logging_default_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    from talking_parrot import logging_config

    importlib.reload(logging_config)
    logging_config.setup_logging()
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_respects_log_level_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from talking_parrot import logging_config

    importlib.reload(logging_config)
    logging_config.setup_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_invalid_level_falls_back(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "NOTVALID")
    from talking_parrot import logging_config

    importlib.reload(logging_config)
    logging_config.setup_logging()
    assert logging.getLogger().level == logging.WARNING

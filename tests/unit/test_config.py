from mediscan.config import Settings


def test_defaults_load_without_env_file():
    # Build a Settings that ignores .env, then assert
    # all three fields equal their documented defaults.
    settings = Settings(_env_file=None)

    assert settings.app_name == "MediScan by DipsAI"
    assert settings.debug is False
    assert settings.log_level == "INFO"


def test_env_var_overrides_default(monkeypatch):
    # Use monkeypatch.setenv("MEDISCAN_LOG_LEVEL", "DEBUG"),
    # build a Settings (still ignoring .env),
    # and assert log_level came out as "DEBUG".
    monkeypatch.setenv("MEDISCAN_LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"

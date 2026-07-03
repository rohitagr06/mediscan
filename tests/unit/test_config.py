"""Tests for mediscan.config.

TESTING CONCEPTS USED HERE
    - pytest finds any function named test_* in a file named test_*.py.
      A test passes unless an `assert` inside it fails.
    - ISOLATION: these tests must give the same result on ANY machine.
      Settings(_env_file=None) ignores the developer's local .env file,
      and the `monkeypatch` fixture sets environment variables for the
      duration of one test only, undoing everything afterwards.
    - We test the Settings CLASS (building fresh instances), not the
      shared `settings` instance — that instance was created at import
      time, before a test could control the environment.
"""

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

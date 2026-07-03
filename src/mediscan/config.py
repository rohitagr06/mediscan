"""Application settings, loaded from environment variables.

WHY THIS FILE EXISTS
    Values that change per machine (debug mode, log level, API keys later)
    must never be hardcoded in Python files. Instead they come from
    "environment variables" — named values the operating system passes to
    a program. During development we keep them in a `.env` file, which is
    listed in .gitignore so secrets can never be committed by accident.

HOW IT WORKS
    The `Settings` class below declares every setting with a type and a
    default. pydantic-settings reads the environment (and `.env`), checks
    the types, and refuses to start the app if something is invalid.
    "Fail at startup, not three hours into running" is the goal.

USAGE
    from mediscan.config import settings
    if settings.debug: ...
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All MediScan configuration in one validated object.

    Each class attribute is one setting. The matching environment variable
    is the field name upper-cased with the MEDISCAN_ prefix, for example
    `debug` is set by `MEDISCAN_DEBUG=true`.
    """

    # model_config customises how pydantic-settings behaves for this class:
    #   env_prefix  -> our variables all start with "MEDISCAN_" so they can
    #                  never collide with other software's variables.
    #   env_file    -> also read values from a local ".env" file if present.
    model_config = SettingsConfigDict(
        env_prefix="MEDISCAN_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # "app_name: str" is a TYPE HINT: it tells Pydantic (and readers) that
    # this value must be a string. The "=" part is the default used when
    # the environment does not override it.
    app_name: str = "MediScan by DipsAI"

    # bool: pydantic-settings understands "true"/"false"/"1"/"0" text.
    debug: bool = False

    # Standard logging verbosity: DEBUG, INFO, WARNING or ERROR.
    log_level: str = "INFO"


# A single shared instance, created once when this module is first imported.
# The rest of the codebase does: `from mediscan.config import settings`.
settings = Settings()

"""Application settings, loaded from environment variables.

WHY THIS FILE EXISTS
    Values that change per machine (debug mode, log level, upload limits,
    API keys later) must never be hardcoded in Python files. They come
    from environment variables — during development via a `.env` file,
    which is gitignored so secrets can never be committed by accident.

USAGE
    from mediscan.config import settings
    if settings.debug: ...
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All MediScan configuration in one validated object.

    Each attribute is one setting. The matching environment variable is
    the field name upper-cased with the MEDISCAN_ prefix, for example
    `max_upload_mb` is set by `MEDISCAN_MAX_UPLOAD_MB=50`.
    """

    model_config = SettingsConfigDict(
        env_prefix="MEDISCAN_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "MediScan by DipsAI"

    debug: bool = False

    # Standard logging verbosity: DEBUG, INFO, WARNING or ERROR.
    log_level: str = "INFO"

    # Upload size limit in megabytes. Config rather than hardcoded:
    # a future deployment (e.g. Hugging Face Spaces) may need a
    # different limit without touching code.
    max_upload_mb: int = 20


# A single shared instance, created once at first import.
settings = Settings()

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

    # Upload size limit in megabytes. Config rather than hardcoded: a
    # deployment (e.g. Hugging Face Spaces) may need a different limit
    # without touching code.
    max_upload_mb: int = 20

    # Router judgment knob: a PDF averaging fewer extractable characters
    # per page than this is classified as a scan needing OCR. Tunable
    # because it is a heuristic, not a law — real-world PDFs that
    # misroute are fixed by adjusting this number in .env, not by code.
    router_min_chars_per_page: int = 25
    preprocess_min_width: int = 1000
    render_dpi: int = 200


# A single shared instance, created once at first import.
settings = Settings()

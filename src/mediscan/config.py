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

from typing import Literal

from pydantic import Field
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

    # Standard logging verbosity, restricted to the valid set.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Upload size limit in megabytes. Config rather than hardcoded: a
    # deployment (e.g. Hugging Face Spaces) may need a different limit
    # without touching code.
    max_upload_mb: int = Field(default=20, gt=0, le=100)

    # Router judgment knob: a PDF averaging fewer extractable characters
    # per page than this is classified as a scan needing OCR. Tunable
    # because it is a heuristic, not a law — real-world PDFs that
    # misroute are fixed by adjusting this number in .env, not by code.
    router_min_chars_per_page: int = Field(default=25, ge=0)

    # Preprocessing knob: images narrower than this many pixels get
    # upscaled before OCR (small letters are shapeless smudges to OCR).
    preprocess_min_width: int = Field(default=1000, gt=0, le=10_000)

    # Sharpness (dots per inch) when rendering scanned-PDF pages to
    # images for OCR. Higher = sharper but slower; 200 is a solid
    # default for printed documents (optimization challenge: tune it).
    render_dpi: int = Field(default=200, gt=0, le=600)

    # Hard cap on scanned-PDF pages to OCR: a hostile many-page PDF
    # would otherwise render+OCR thousands of images (resource DoS).
    max_pdf_pages: int = Field(default=50, gt=0, le=500)


# A single shared instance, created once at first import.
settings = Settings()

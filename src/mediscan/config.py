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

from pydantic import Field, SecretStr, model_validator
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

    # ---- AI explanation layer (Sprint 5) ----
    # API keys are SECRETS. SecretStr refuses to print its value, so it
    # cannot leak into a log, error, or repr by accident. They stay None
    # until set in the environment (.env locally, injected in deployment).
    gemini_api_key: SecretStr | None = None
    github_models_token: SecretStr | None = None

    # Which model each rung of the #004 fallback chain uses. Strings so we
    # can swap models without code changes. (Confirm exact IDs at 5.5/5.6.)
    gemini_model: str = "gemini-2.0-flash"
    github_primary_model: str = "openai/gpt-4.1-mini"
    github_fallback_model: str = "microsoft/Phi-4"

    # AI behaviour knobs — bounded, exactly like your Sprint-3 knobs.
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    # Low temperature = faithful, not creative. We want accuracy, not flair.
    llm_temperature: float = Field(default=0.2, ge=0, le=1)

    # Severity banding cutoffs (decision #020). These are the exact
    # numbers the deterministic severity engine bands against, kept in
    # config so a clinician can tune them without touching code.
    #
    # Option A (no sourced critical threshold) — bands by PERCENTAGE
    # deviation from the nearest normal boundary; capped at HIGH:
    #   deviation < pct_mild      -> MILD
    #   deviation < pct_moderate  -> MODERATE
    #   otherwise                 -> HIGH
    severity_pct_mild: float = Field(default=0.15, gt=0, lt=1)
    severity_pct_moderate: float = Field(default=0.30, gt=0, lt=1)
    #
    # Option B (a sourced critical threshold exists) — bands by the
    # FRACTION of the way from the normal boundary toward the critical
    # value (0.0 = at the boundary, 1.0 = at the critical line):
    #   fraction < frac_mild      -> MILD
    #   fraction < frac_moderate  -> MODERATE
    #   otherwise                 -> HIGH (past the line -> CRITICAL)
    severity_frac_mild: float = Field(default=0.33, gt=0, lt=1)
    severity_frac_moderate: float = Field(default=0.66, gt=0, lt=1)

    @model_validator(mode="after")
    def validate_severity_cutoffs(self) -> "Settings":
        """Reject configurations where the severity bands are out of order.

        Each cutoff is individually valid between 0 and 1, but if mild >=
        moderate the bands invert and the engine would report LESS severe
        results for MORE abnormal values. A single mistyped environment
        variable must never be able to do that silently -- better to crash
        at startup with a clear message than to under-report severity.
        """
        if self.severity_pct_mild >= self.severity_pct_moderate:
            raise ValueError(
                "severity_pct_mild must be less than severity_pct_moderate "
                f"(got {self.severity_pct_mild} >= {self.severity_pct_moderate})"
            )
        if self.severity_frac_mild >= self.severity_frac_moderate:
            raise ValueError(
                "severity_frac_mild must be less than severity_frac_moderate "
                f"(got {self.severity_frac_mild} >= {self.severity_frac_moderate})"
            )
        return self


# A single shared instance, created once at first import.
settings = Settings()

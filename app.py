"""Hugging Face Spaces entry point for MediScan.

HF runs this file with `python app.py`: it builds the Gradio app and launches
it. Three things are set up here — at the public entry point — BEFORE any
`mediscan` module is imported:

  1. src/ layout on the path. The package lives in `src/mediscan/`, and the
     Space's `requirements.txt` installs only third-party deps (not this
     package, whose uv build backend pip can't run). Putting `<root>/src` on
     `sys.path` makes `mediscan` importable straight from source — the KB JSON
     and all package data come along for free.
  2. MEDISCAN_DEMO_MODE=1 — the public Space is deterministic: no AI providers,
     no keys, no per-click cost or abuse surface (decision #036). `setdefault`
     only fills it when UNSET, so a PRIVATE keyed Space can override it to 0.
  3. MEDISCAN_RAG_INDEX_CACHE_DIR — a guaranteed-writable cache path under the
     system temp dir (#034); the index also auto-falls-back to a temp dir if
     this is unwritable, so this is belt-and-suspenders.

Everything else is configured via MEDISCAN_* env vars in the Space settings,
never hard-coded here (docs/17-deploy-config.md).
"""

import os
import sys
import tempfile

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# MUST precede the mediscan import: pydantic-settings reads the environment at
# import time, so setting these defaults afterwards would be too late. The
# cache path is built via gettempdir() (not a hard-coded "/tmp") so it is
# portable and satisfies the security linter.
os.environ.setdefault("MEDISCAN_DEMO_MODE", "1")
os.environ.setdefault(
    "MEDISCAN_RAG_INDEX_CACHE_DIR",
    os.path.join(tempfile.gettempdir(), "mediscan_rag_index"),
)

from mediscan.ui import build_app  # noqa: E402 - path + env must be set first

# HF's Gradio SDK looks for a module-level Blocks object; `demo` is the
# conventional name. Running `python app.py` also launches it via the guard.
demo = build_app()

if __name__ == "__main__":
    # Bind to all interfaces on the platform-provided $PORT so the host
    # (Render, etc.) can route to it; falls back to Gradio's default
    # locally. 0.0.0.0 is required for the container to be reachable.
    demo.launch(
        server_name="0.0.0.0",  # noqa: S104 - a web server must bind publicly
        server_port=int(os.environ.get("PORT", "7860")),
    )

"""MediScan by DipsAI — a safety-first medical lab-report analyzer.

Top-level package. Subpackages own one stage each of the pipeline:
ingestion, ocr, extraction, medical (the deterministic engine), rag, ai
(explanation layer), safety (guardrail), observability (logging), and
schemas (the shared Pydantic contracts). See docs/01-architecture.md.
"""

__version__ = "0.1.0"

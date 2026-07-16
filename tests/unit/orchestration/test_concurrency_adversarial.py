"""Adversarial tests for the async explanation concurrency (Sprint 7.7).

These try to break the guarantees of assemble_report_explanations_async:
  * a per-output TIMEOUT degrades that output to its deterministic template;
  * one failing output NEVER sinks the others (independent fallback);
  * the four outputs really run CONCURRENTLY (wall-clock << sum of parts);
  * a totally failing provider still yields a complete deterministic report.

All offline: fake providers, a no-op retriever, and llm_max_retries pinned to
0 so the chain's backoff sleeps don't slow the suite.
"""

import asyncio
import time

from fixtures.full_panel import MALE_REPORT
from mediscan.ai.base import LLMClient
from mediscan.ai.exceptions import LLMError
from mediscan.config import settings
from mediscan.orchestration import analyze_text_async
from mediscan.schemas import LLMResponse


def _no_retrieve(_query):
    return []


def _resp(text, name, model):
    return LLMResponse(
        text=text, provider_name=name, model=model, temperature=0.2, latency_ms=0.0
    )


class _OkTextLLM(LLMClient):
    """Returns {"text": "ok"} — valid for the two summary schemas, but not for
    the two LIST schemas (dietary/specialist), which need a JSON array."""

    provider_name = "ok"
    model = "ok-1"

    def complete(self, request):
        return _resp('{"text": "ok"}', "ok", "ok-1")


class _SlowOkLLM(LLMClient):
    provider_name = "slow"
    model = "slow-1"

    def __init__(self, delay):
        self._delay = delay

    def complete(self, request):
        time.sleep(self._delay)
        return _resp('{"text": "ok"}', "slow", "slow-1")


class _SlowFailLLM(LLMClient):
    provider_name = "slowfail"
    model = "sf-1"

    def __init__(self, delay):
        self._delay = delay

    def complete(self, request):
        time.sleep(self._delay)
        raise LLMError("boom after sleeping")


class _FailLLM(LLMClient):
    provider_name = "boom"
    model = "boom-1"

    def complete(self, request):
        raise LLMError("nope")


def _run(providers, **kw):
    return asyncio.run(
        analyze_text_async(
            MALE_REPORT, providers=providers, retrieve_fn=_no_retrieve, **kw
        )
    )


def test_per_output_timeout_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    # each output would take 0.1s, but the timeout fires at 0.01s -> all five
    # degrade to deterministic templates, and the report is still complete.
    report = _run([_SlowOkLLM(0.1)], timeout=0.01)
    assert report.metadata.fallback_count == 5
    assert report.patient_summary is not None
    assert report.urgency is not None


def test_one_set_fails_while_the_other_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    # patient + doctor validate ("ok"); dietary + lifestyle + specialist need
    # a LIST and fail -> exactly three fall back; successes are unaffected.
    report = _run([_OkTextLLM()])
    assert report.metadata.fallback_count == 3
    assert report.patient_summary.text == "ok"
    assert report.doctor_summary.text == "ok"
    assert "ok-1" in report.metadata.models_used


def test_outputs_run_concurrently_not_sequentially(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    delay = 0.15
    start = time.perf_counter()
    report = _run([_SlowFailLLM(delay)])
    elapsed = time.perf_counter() - start

    assert report.metadata.fallback_count == 5  # all failed -> deterministic
    # five × delay run concurrently should finish in ~one delay, well under the
    # sequential sum (5 × delay). A generous bound keeps it non-flaky.
    assert elapsed < 5 * delay * 0.75


def test_total_provider_failure_still_completes_deterministically(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    report = _run([_FailLLM()])
    assert report.metadata.fallback_count == 5
    assert report.metadata.models_used == []
    assert report.patient_summary is not None  # deterministic, never blank

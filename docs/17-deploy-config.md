# Deploy configuration (Sprint 8.7)

RC1 ships to **Hugging Face Spaces**. All deploy-time behaviour is driven by
environment variables (prefix `MEDISCAN_`) — never code changes. The actual
Space files (`app.py`, `requirements`, `packages.txt`) are built in task 8.10;
this doc is the env-var contract they rely on.

## Public Space (the safe default)

| Env var | Value | Why |
|---|---|---|
| `MEDISCAN_DEMO_MODE` | `1` | Forces deterministic demo mode: **no** AI providers are ever used, whatever keys exist. The UI demo toggle is shown ON and locked. No keys, no per-click cost, no abuse surface — still a complete deterministic report (#036). |
| `MEDISCAN_RAG_INDEX_CACHE_DIR` | `/tmp/mediscan_rag_index` | A **writable** path for the persisted RAG index (#034). If unset or unwritable, the app auto-falls back to a temp dir (`_resolve_cache_root`), so it never crashes on a read-only FS. |

**Never put API keys on the public Space.**

## Private / local keyed run (AI explanations ON)

| Env var | Value |
|---|---|
| `MEDISCAN_DEMO_MODE` | `0` (or unset) |
| `MEDISCAN_GEMINI_API_KEY` | your Gemini key |
| `MEDISCAN_GITHUB_MODELS_TOKEN` | your GitHub Models token |

Locally these live in `.env` (gitignored). On a private Space they go in
**Settings → Secrets**, never the repo — the gitleaks hook + CI job are the
backstop.

## macOS note

WeasyPrint needs the Homebrew libraries on the loader path — see
`docs/05-environment-setup.md` (`DYLD_FALLBACK_LIBRARY_PATH`). On the Linux
Space this is handled by `packages.txt` (task 8.10); no `DYLD_*` needed there.

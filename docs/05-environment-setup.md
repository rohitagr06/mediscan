# Development Environment Setup

*From a blank machine to running MediScan's tests. Written during Sprint 0, when these
steps were performed for real. If a step fails for you, check Troubleshooting at the
bottom — and if you hit something new, add it there for the next person.*

## Prerequisites

- macOS or Linux (Windows users: use WSL2)
- **Git** — check with `git --version` (macOS offers to install developer tools if missing)
- A **GitHub account** (to clone, and to contribute)
- An internet connection for the first setup (~5 minutes of downloads)

You do **not** need to install Python yourself — uv manages the correct Python version
for this project automatically (pinned in `.python-version`).

## 1. Install uv

uv is the package and environment manager this project uses for everything.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Important:** close your terminal and open a new one afterwards — the installer updates
your PATH, and only new terminal sessions pick that up. Then verify:

```bash
uv --version
```

Any version ≥ 0.8 is fine.

## 2. Clone the repository

```bash
git clone https://github.com/rohitagr06/mediscan.git
cd mediscan
```

## 3. Install dependencies

```bash
uv sync --all-groups
```

This single command: installs the pinned Python version if needed, creates the project's
private virtual environment in `.venv/`, and installs every dependency at the *exact*
versions recorded in `uv.lock` — including dev tools (`--all-groups` is what pulls those in).

You never need to "activate" the environment: prefix commands with `uv run` instead.

## 4. Create your local configuration

```bash
cp .env.example .env
```

`.env` holds machine-local settings (and, in later sprints, your API keys). It is
**gitignored — never commit it**. The `.env.example` file documents every variable
that exists; edit `.env` if you want non-default values.

## 5. Install the git hooks

```bash
uv run pre-commit install
```

**Do not skip this step.** It arms the pre-commit hooks that run Ruff and Black on every
commit. Hooks are not cloned with the repository — every fresh clone must run this once,
and it's the step everyone forgets.

## 6. Verify everything works

```bash
uv run pytest -v          # all tests should pass
uv run ruff check .       # should print: All checks passed!
uv run black --check .    # should report all files unchanged
```

If all three are clean, your environment matches CI exactly and you're ready to develop.

## Everyday commands

| Command | What it does |
|---|---|
| `uv run pytest -v` | Run the test suite |
| `uv run ruff check .` | Lint |
| `uv run black .` | Format (fixes files in place) |
| `uv add <package>` | Add a runtime dependency |
| `uv add --dev <package>` | Add a development-only dependency |
| `uv sync --all-groups` | Re-sync environment after pulling changes |
| `uv run pre-commit run --all-files` | Run all hooks against the whole repo |

## Troubleshooting

**`uv: command not found` right after installing.**
You're in the same terminal session you installed from. Close it, open a new one.

**Pre-commit rejected my commit and modified files.**
Working as intended: a hook fixed formatting/whitespace. Review with `git diff`, then
`git add -A` and commit again.

**`[ERROR] Your pre-commit configuration is unstaged.`**
A hook (or you) edited `.pre-commit-config.yaml` itself. Run
`git add .pre-commit-config.yaml` and commit again.

**Tests pass locally but fail in CI (or vice versa).**
Usually environment leakage. Our tests isolate themselves from `.env` via
`Settings(_env_file=None)` and pytest's `monkeypatch` — keep that pattern for any new
test that touches configuration.

**First `pre-commit` run is very slow.**
It downloads and caches each hook's tooling once. Subsequent runs take a second or two.

## PDF export (WeasyPrint) — system libraries

Sprint 8 added a downloadable PDF report, rendered by **WeasyPrint**. WeasyPrint
is a Python package (installed by `uv sync`), but it wraps C libraries
(**pango**, **cairo**) that are NOT Python and must be installed at the OS level.

**macOS (Homebrew):**

```bash
brew install pango
```

On Apple Silicon, Homebrew installs libraries under `/opt/homebrew/lib`, which
macOS's dynamic loader does not search by default — so WeasyPrint fails to find
`libgobject`/`libpango` even after `brew install`. Point the loader at it once,
permanently, by adding this line to your `~/.zshrc`:

```bash
echo 'export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib' >> ~/.zshrc
source ~/.zshrc
```

After this, every new terminal can render PDFs; `uv run pytest tests/unit/reports/`
should show all tests passing (0 skipped). Without the libraries the PDF tests
SKIP (they never fail the suite) and the app still shows the on-screen analysis —
only the PDF download is withheld.

**Linux / Hugging Face Spaces:** the libraries install to standard system paths
the loader already searches, so no `DYLD_*` variable is needed. On the deployed
Space they come from `packages.txt` (see the Sprint 8 deploy task).

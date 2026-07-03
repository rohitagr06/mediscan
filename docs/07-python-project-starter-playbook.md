# Python Project Starter Playbook

*A reusable, step-by-step pipeline for starting ANY new Python project the
production-grade way — with uv, quality gates, tests, and CI from day one.
Written from the real Sprint 0 experience of MediScan. Follow it top to bottom;
nothing here assumes prior knowledge.*

---

## Phase 0 — One-time machine setup (do once per computer)

### 0.1 Prerequisites

| Tool | Check with | If missing |
|---|---|---|
| A terminal | macOS: Terminal app / Windows: PowerShell | Built in |
| Git | `git --version` | macOS: accept the developer-tools popup. Windows: install from https://git-scm.com (accept defaults) |
| A GitHub account | log in at github.com | Sign up free |
| A code editor | Cursor / VS Code | Download and install |

> You do **not** install Python yourself. uv downloads and manages Python
> versions for you — this avoids the classic "wrong Python" mess entirely.

### 0.2 Install uv — macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 0.2 Install uv — Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 0.3 Restart the terminal, then verify

Close the terminal window completely and open a new one (the installer
edits your PATH — the list of folders the shell searches for commands — and
only NEW terminal sessions see the change). Then:

```bash
uv --version
```

Any version number = success. `command not found` = you're still in the old
terminal session, or PATH didn't update (see Troubleshooting at the end).

### 0.4 Tell git who you are (once)

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

---

## Phase 1 — Create the project (5 minutes)

### 1.1 Create the project folder and initialize uv

```bash
mkdir myproject
cd myproject
uv init --lib --name myproject --python 3.12
```

Flag meanings:

- `--lib` → installable package with the `src/` layout (recommended for
  anything with tests). For a quick script-style project, omit it.
- `--name` → explicit package name (lowercase, no spaces/hyphens).
- `--python 3.12` → pins the Python version; uv downloads it if needed.

This creates:

| File | What it is |
|---|---|
| `pyproject.toml` | The project's identity card: name, version, Python requirement, dependencies, tool configs |
| `.python-version` | One line pinning the Python version for every machine |
| `src/myproject/__init__.py` | Your package. An `__init__.py` is what makes a folder importable |
| `src/myproject/py.typed` | Marker: "this package has type hints" |
| `README.md` | Stub — you'll rewrite it in Phase 4 |

### 1.2 Create the environment and lockfile

```bash
uv sync
```

Creates `.venv/` (the project's PRIVATE library folder — its own kitchen,
so projects never fight over versions) and `uv.lock` (the exact versions
installed, down to the decimal — commit this file; it makes every machine
build identically).

From now on, run everything through the environment with the `uv run` prefix:

```bash
uv run python -c "print('hello from the venv')"
```

No "activating" needed, ever.

### 1.3 Sanity-check the layout

```
myproject/
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── src/
│   └── myproject/
│       ├── __init__.py
│       └── py.typed
└── (tests/ — you add this in Phase 3)
```

---

## Phase 2 — Version control from minute one

### 2.1 `.gitignore` BEFORE the first commit

Create a file named `.gitignore` at the project root:

```gitignore
# Secrets — NEVER commit these
.env

# Virtual environment (regenerable via `uv sync`)
.venv/

# Python caches (regenerable junk)
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/

# Build artifacts
dist/
build/
*.egg-info/

# OS junk
.DS_Store        # macOS
Thumbs.db        # Windows

# Scratch
playground.py
tmp/
*.log
```

Why first: the deadliest mistake in public repos is committing an API key.
The `.env` line must exist BEFORE `.env` ever does.

### 2.2 Environment-variable convention

Create `.env.example` (committed — documents which variables exist, with
FAKE values) and later copy it to `.env` (ignored — holds real values):

```bash
# .env.example — copy to .env and fill in real values
MYPROJECT_DEBUG=false
MYPROJECT_API_KEY=put-real-key-in-.env-not-here
```

### 2.3 License

Add a `LICENSE` file (MIT is the common permissive default — grab the text
from https://choosealicense.com/licenses/mit/ and put your name in the
copyright line). Code without a license is legally unusable by others.

### 2.4 First commit + GitHub

On github.com: **New repository** → name it → **leave all "initialize with"
checkboxes UNCHECKED** (your files already exist locally). Then:

```bash
git init
git add .
git commit -m "chore: initialize project with uv"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/myproject.git
git push -u origin main
```

> Windows note: if git asks for a password, it wants a Personal Access
> Token (GitHub → Settings → Developer settings → Tokens), not your
> account password. macOS typically triggers a browser login instead.

---

## Phase 3 — Quality gates (the production difference)

### 3.1 Dev dependencies

```bash
uv add --dev ruff black pytest pre-commit
```

`--dev` puts these in a separate `[dependency-groups]` section: tools YOU
need while developing, which users of your package don't. Runtime
dependencies (things the code imports) are added WITHOUT the flag:
`uv add requests`.

### 3.2 Tool configuration — append to `pyproject.toml`

```toml
[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S"]
# E=style, F=real bugs, I=import order, B=subtle traps,
# UP=outdated syntax, S=SECURITY (flags eval/exec/hardcoded secrets)

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]   # pytest tests are BUILT on assert; allow it there

[tool.black]
line-length = 88
target-version = ["py312"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 3.3 Tests folder + first test

```bash
mkdir -p tests/unit
```

Write one trivial test in `tests/unit/test_smoke.py`:

```python
def test_package_imports():
    import myproject  # noqa: F401  (imported to prove it's installable)
```

Run everything and expect green:

```bash
uv run ruff check .
uv run black .
uv run pytest -v
```

### 3.4 Pre-commit hooks (the local gatekeeper)

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0        # pin latest with: uv run pre-commit autoupdate
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-added-large-files
```

Arm it (must be repeated on every fresh clone — the step everyone forgets):

```bash
uv run pre-commit autoupdate
uv run pre-commit install
uv run pre-commit run --all-files
```

From now on every `git commit` is checked automatically; bad formatting is
fixed and the commit rejected so you can review and re-stage (`git add -A`,
commit again).

### 3.5 CI — the cloud gatekeeper

Create `.github/workflows/ci.yml` (path must be exact):

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Install uv
        uses: astral-sh/setup-uv@v6
      - name: Sync dependencies
        run: uv sync --all-groups
      - name: Lint (ruff)
        run: uv run ruff check .
      - name: Format check (black)
        run: uv run black --check .
      - name: Tests (pytest)
        run: uv run pytest -v
```

Note `black --check`: in CI we REPORT problems, never auto-fix (nobody is
there to review a robot's edits). Commit, push, then watch the **Actions**
tab on GitHub turn green. Pre-commit guards your machine; CI guards the
shared repo — belt and braces.

### 3.6 README + CI badge

Rewrite `README.md`: what the project is (2-3 sentences), how to set it up
(point at this playbook's Phase 5), how to run tests, license. Add the live
status badge near the top:

```markdown
![CI](https://github.com/YOUR-USERNAME/myproject/actions/workflows/ci.yml/badge.svg)
```

---

## Phase 4 — The daily development loop

```bash
# start of a work session
git pull
uv sync --all-groups        # in case dependencies changed

# ... edit code ...

uv run pytest -v            # tests green?
uv run ruff check .         # lint clean?
uv run black .              # format

git add <files>
git commit -m "feat: describe the change"   # hooks run automatically here
git push                                     # CI runs automatically here
```

Commit-message convention (helps humans and tools read history):
`feat:` new feature · `fix:` bug fix · `test:` tests only ·
`docs:` documentation · `chore:` maintenance · `refactor:` no behavior change

---

## Phase 5 — Joining an EXISTING project (fresh clone / new teammate)

```bash
git clone https://github.com/OWNER/project.git
cd project
uv sync --all-groups         # installs pinned Python + exact locked deps
cp .env.example .env         # then fill in real values
uv run pre-commit install    # arm the hooks — DON'T SKIP
uv run pytest                # verify everything works before touching code
```

Five commands from blank machine to contributing. That's the payoff of
everything in Phases 1-3.

---

## Command cheat sheet

| Command | What it does |
|---|---|
| `uv sync --all-groups` | Create/refresh `.venv` from the lockfile (incl. dev tools) |
| `uv add <pkg>` | Add a runtime dependency |
| `uv add --dev <pkg>` | Add a development-only dependency |
| `uv remove <pkg>` | Remove a dependency |
| `uv run <cmd>` | Run any command inside the project environment |
| `uv run python` | Interactive Python inside the environment |
| `uv lock --upgrade` | Update the lockfile to newest allowed versions |
| `uv python list` | Show Pythons uv knows about |
| `uv run pre-commit run --all-files` | Run all hooks on the whole repo |

## Troubleshooting

**`uv: command not found` after installing** — you're in the pre-install
terminal session. Close it, open a new one. Windows: if it persists, log
out/in, or check that `%USERPROFILE%\.local\bin` is in PATH.

**PowerShell blocks the install script** — the `-ExecutionPolicy ByPass`
in the official command handles this; run PowerShell as a normal user
(admin not required).

**Pre-commit rejected my commit and changed files** — working as designed:
review with `git diff`, then `git add -A` and commit again.

**`[ERROR] Your pre-commit configuration is unstaged`** — a hook edited
`.pre-commit-config.yaml` itself; `git add .pre-commit-config.yaml`, retry.

**Tests pass locally, fail in CI (or vice versa)** — almost always
environment leakage: a test silently depends on your `.env` or shell
variables. Isolate tests from local config (in Pydantic projects:
`Settings(_env_file=None)` + pytest's `monkeypatch`).

**Git push asks for credentials on Windows** — use a Personal Access Token
as the password, or install GitHub CLI (`gh auth login`) and let it manage
credentials.

**Corporate proxy / firewall blocks installs** — set `HTTPS_PROXY`
environment variable, or download the uv installer manually from GitHub
releases.

---

## The philosophy in one paragraph

Every step above exists to make the project **boring to run**: any machine,
any teammate, any month of the year — same Python, same dependency versions
(lockfile), same style (Black), same standards (Ruff), same proof it works
(pytest + CI), same protection against accidents (.gitignore, hooks,
security lint). Production engineering is mostly the discipline of removing
surprises before they happen.

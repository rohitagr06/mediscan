"""Built-wheel packaging tests (Sprint 8.2, #019).

WHY THIS FILE EXISTS
    Until now MediScan has only ever run from the source tree, where the
    knowledge-base JSON files just happen to sit next to the code. A DEPLOYED
    app runs from an installed wheel — and a wheel contains only what the
    build backend chooses to ship. If the KB JSON were ever dropped from the
    wheel, the deployed app would boot with an EMPTY knowledge base: no
    fallback ranges, no grounding snippets — a silent safety regression.

    Our backend (uv_build) ships every file inside the module by default, so
    today this "just works". These tests exist so it KEEPS working: if anyone
    switches build backends, adds a careless `wheel-exclude`, or moves the KB
    outside the package, CI fails loudly instead of production failing
    quietly.

    Two guarantees:
      1. Every KB JSON in the source tree is inside the built wheel.
      2. A simulated fresh install (the wheel's contents, NOT the source
         tree) can actually load ranges + snippets.

    Needs the `uv` executable, and network access the first time (to fetch
    the build backend); skipped where either is unavailable (the cloud
    sandbox). Runs for real on the Mac and in CI.
"""

# ruff: noqa: S603, S607 - this file intentionally shells out to `uv build`
# and a python probe with FIXED, non-user-controlled arguments (no shell,
# list-form subprocess). Scoped here so pyproject's rules stay untouched.

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

# parents[2] = tests/packaging/this_file -> tests/packaging -> tests -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = REPO_ROOT / "src" / "mediscan" / "knowledge_base"

# If `uv build` fails and its output contains one of these, the cause is "no
# package index reachable" (the cloud sandbox), not a packaging bug -> skip.
_OFFLINE_MARKERS = ("403", "Forbidden", "could not be queried", "Connection")


@pytest.fixture(scope="module")
def wheel_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel ONCE for this module; every test reuses it."""
    if shutil.which("uv") is None:
        pytest.skip("uv executable not available")
    out_dir = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        output = result.stdout + result.stderr
        if any(marker in output for marker in _OFFLINE_MARKERS):
            pytest.skip("no package-index access to fetch the build backend")
        pytest.fail(f"uv build failed:\n{output}")
    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got: {wheels}"
    return wheels[0]


def test_wheel_contains_every_kb_file(wheel_path: Path) -> None:
    """Guarantee 1: no KB JSON on disk is missing from the built wheel."""
    source_kb = sorted(
        p.relative_to(REPO_ROOT / "src").as_posix() for p in KB_DIR.rglob("*.json")
    )
    # If this glob found nothing, the comparison below would pass VACUOUSLY
    # (nothing to miss). Guard the guard.
    assert source_kb, "source KB glob found no files — test itself is broken"

    with zipfile.ZipFile(wheel_path) as whl:
        shipped = set(whl.namelist())
    missing = [name for name in source_kb if name not in shipped]
    assert not missing, f"KB files missing from the built wheel: {missing}"


def test_fresh_install_can_load_kb(wheel_path: Path, tmp_path: Path) -> None:
    """Guarantee 2: the wheel's own files can load ranges + snippets.

    `pip install` is essentially "unzip the wheel into site-packages", so we
    simulate a fresh install by extracting the wheel to an empty directory
    and importing mediscan FROM THERE (PYTHONPATH wins over the editable
    install; cwd is moved off the repo root so `src/` can't leak in).
    """
    site = tmp_path / "site"
    with zipfile.ZipFile(wheel_path) as whl:
        whl.extractall(site)

    probe = (
        "from mediscan.medical.reference_data import load_reference_ranges\n"
        "from mediscan.rag.index import load_snippets\n"
        "ranges = load_reference_ranges()\n"
        "snippets = load_snippets()\n"
        "assert ranges, 'installed package loaded ZERO reference ranges'\n"
        "assert snippets, 'installed package loaded ZERO KB snippets'\n"
        "print(f'{len(ranges)} ranges, {len(snippets)} snippets')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,  # NOT the repo root: the source tree must not be visible
        env={**os.environ, "PYTHONPATH": str(site)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert (
        result.returncode == 0
    ), f"fresh-install probe failed:\n{result.stdout}\n{result.stderr}"

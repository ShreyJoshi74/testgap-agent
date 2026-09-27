"""scan — run pytest with coverage and record metrics.

Public API
----------
    main(project, label, src) -> int
"""

from __future__ import annotations

import os
import subprocess as _sp
import sys
from datetime import datetime, timezone
from pathlib import Path

from testgap.common import (
    check_deps,
    load_json,
    reports_dir,
    to_posix,
    update_metrics,
)
from testgap.run_tests import parse_junit, parse_junit_empty


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------

def _dirty_paths(project: Path) -> list[str]:
    """Return a sorted list of posix paths that are dirty in git.

    Uses ``git status --porcelain --untracked-files=all`` so that files
    modified *before* the tool run are not blamed on the tool (FR-12).
    Returns an empty list when git is unavailable or the directory is not a
    git repo.
    """
    try:
        result = _sp.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(project),
        )
        paths = []
        for line in result.stdout.splitlines():
            if line.strip():
                # Format: "XY filename"  (first two chars are status codes)
                paths.append(to_posix(line[3:].strip()))
        return sorted(paths)
    except (_sp.CalledProcessError, FileNotFoundError):
        return []


# ---------------------------------------------------------------------------
# coverage JSON reader
# ---------------------------------------------------------------------------

def _read_coverage_percent(coverage_json: Path) -> float:
    """Extract ``totals.percent_covered`` from a coverage.py JSON report."""
    data = load_json(coverage_json)
    return round(float(data["totals"]["percent_covered"]), 1)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(project: str | Path, label: str, src: str) -> int:
    """Run pytest with coverage on *project* and update reports.

    Args:
        project: Absolute path to the target project folder.
        label:   ``"before"`` or ``"after"``.
        src:     Source sub-directory to measure coverage for (e.g. ``"app"``).

    Returns:
        0 on success or recoverable error (test failures, no tests).
        1 on fatal error (bad pytest usage, missing deps).
    """
    check_deps()

    project = Path(project).resolve()
    rdir = reports_dir()

    # --- (before only) initialise metrics.json and record dirty state -------
    if label == "before":
        dirty = _dirty_paths(project)
        if dirty:
            print(
                f"warning: {len(dirty)} file(s) already modified before the run "
                f"(recorded in metrics.json as dirty_before)."
            )
        update_metrics(
            project=project.name,
            src=src,
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            dirty_before=dirty,
        )

    # --- build pytest arguments ---------------------------------------------
    cov_json = rdir / f"coverage_{label}.json"
    junit_xml = rdir / f"junit_{label}.xml"

    extra_args = [
        f"--cov={src}",
        f"--cov-report=json:{cov_json}",
        f"--junitxml={junit_xml}",
    ]

    # Put .coverage in reports/ so nothing lands in the project tree (FR-12).
    env = os.environ.copy()
    env["COVERAGE_FILE"] = str(rdir / ".coverage")

    # --- run pytest ---------------------------------------------------------
    # run_pytest does not expose an env kwarg; call subprocess.run directly
    # so we can set COVERAGE_FILE without landing .coverage in the project.
    cmd = [
        sys.executable, "-m", "pytest",
        "-p", "no:cacheprovider",
        "--timeout=30",
        *extra_args,
    ]
    proc = _sp.run(cmd, cwd=str(project), timeout=600, env=env)

    rc = proc.returncode

    # --- handle exit codes --------------------------------------------------
    # 0 → all tests passed
    # 1 → some tests failed — continue, record count
    # 5 → no tests collected — treat as 0 tests, 0% coverage
    # 2/3/4 → pytest usage / internal error → stop
    if rc in (2, 3, 4):
        print(
            f"error: pytest exited with code {rc} (usage or internal error). "
            f"Check the output above.",
            flush=True,
        )
        return 1

    # --- read results -------------------------------------------------------
    # Coverage percent
    if cov_json.exists():
        coverage_pct = _read_coverage_percent(cov_json)
    else:
        coverage_pct = 0.0

    # Test counts via JUnit XML
    if junit_xml.exists():
        junit_data = parse_junit(junit_xml)
    else:
        junit_data = parse_junit_empty()

    tests_count = junit_data["passed"] + junit_data["failed"] + junit_data["xfailed"]

    # --- record failing-before count ----------------------------------------
    if label == "before" and rc == 1:
        failing_before = junit_data["failed"] + junit_data["errors"]
        print(
            f"warning: {failing_before} test(s) already failing before test generation."
        )
        update_metrics(existing_tests_failing_before=failing_before)
    elif label == "before":
        update_metrics(existing_tests_failing_before=0)

    # --- update metrics.json ------------------------------------------------
    update_metrics(**{
        f"coverage_{label}": coverage_pct,
        f"tests_{label}": tests_count,
    })

    print(f"Coverage ({label}): {coverage_pct}% — {tests_count} tests")
    return 0

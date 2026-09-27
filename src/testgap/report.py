"""report — build reports/report.md from all JSON artefacts.

Public API
----------
    main(project, minutes_per_test) -> int
    filter_changed_paths(paths, project, src, dirty_before) -> list[str]
"""

from __future__ import annotations

import subprocess as _sp
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from testgap.common import load_json, reports_dir, save_json, to_posix, update_metrics


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------

def _git_dirty_paths(cwd: Path) -> list[str] | None:
    """Return current dirty posix paths, or None when git is unavailable."""
    try:
        result = _sp.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(cwd),
        )
        paths = []
        for line in result.stdout.splitlines():
            if line.strip():
                paths.append(to_posix(line[3:].strip()))
        return paths
    except (_sp.CalledProcessError, FileNotFoundError):
        return None


def filter_changed_paths(
    paths: Sequence[str],
    project: str,
    src: str,
    dirty_before: Sequence[str],
) -> list[str]:
    """Filter *paths* to only those that are unexpected changes.

    Removes:
    - Paths under ``<project>/tests/generated/``
    - Paths under ``reports/``
    - Paths already in *dirty_before* (existed before the run)

    Returns the remaining paths; ``source_files_changed`` are those under
    ``<project>/<src>/``.

    Args:
        paths:        All currently dirty paths (posix, repo-relative).
        project:      The project folder name (e.g. ``"sample_project"``).
        src:          The source subdirectory name (e.g. ``"app"``).
        dirty_before: Paths already dirty before the run (from metrics.json).
    """
    allowed_prefixes = (
        f"{project}/tests/generated/",
        "reports/",
    )
    dirty_set = set(dirty_before)
    result = []
    for p in paths:
        if p in dirty_set:
            continue
        if any(p.startswith(pfx) for pfx in allowed_prefixes):
            continue
        result.append(p)
    return result


# ---------------------------------------------------------------------------
# time helpers
# ---------------------------------------------------------------------------

def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp (with or without timezone)."""
    # Python 3.11+ fromisoformat handles Z; 3.7–3.10 don't — handle both.
    ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def _format_duration(seconds: int) -> str:
    """Format seconds as ``Xh Ym Zs`` / ``Ym Zs`` / ``Zs``."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# report builder
# ---------------------------------------------------------------------------

def _build_report(
    project: str,
    metrics: dict,
    results: dict,
    gaps: dict,
    files_changed: list[str],
    source_files_changed: int,
    git_available: bool,
    finished_at: datetime,
    run_seconds: int,
    minutes_per_test: float,
    minutes_per_test_measured: bool,
) -> str:
    """Return the full markdown string for report.md."""
    lines: list[str] = []

    lines.append(f"# TestGap Report: {project}")
    lines.append("")

    # --- before/after table --------------------------------------------------
    cov_before = metrics.get("coverage_before", 0.0)
    cov_after = metrics.get("coverage_after", "—")
    tests_before = metrics.get("tests_before", 0)
    tests_after = metrics.get("tests_after", "—")

    lines.append("|                    | Before | After |")
    lines.append("|--------------------|--------|-------|")
    after_cov_str = f"{cov_after}%" if isinstance(cov_after, (int, float)) else str(cov_after)
    lines.append(f"| Coverage           | {cov_before}%  | {after_cov_str} |")
    lines.append(f"| Tests              | {tests_before}      | {tests_after}    |")
    lines.append("")

    # --- tests added summary -------------------------------------------------
    gen = results.get("generated", {})
    gen_total = gen.get("total", 0)
    gen_passed = gen.get("passed", 0)
    gen_xfailed = gen.get("xfailed", 0)
    gen_skipped = gen.get("skipped", 0)
    gen_failed = gen.get("failed", 0)
    still_failing = gen_failed + gen.get("errors", 0)

    lines.append(
        f"- Tests added: {gen_total} "
        f"({gen_passed} passing, {gen_xfailed} possible bugs, "
        f"{gen_skipped} could not be fixed, {still_failing} still failing)"
    )

    # --- pass rate -----------------------------------------------------------
    pass_rate = gen.get("pass_rate", 0.0)
    lines.append(f"- Generated pass rate: {round(pass_rate * 100, 1)}%")

    # --- tool run time -------------------------------------------------------
    lines.append(f"- Tool run time: {_format_duration(run_seconds)}")

    # --- estimated time by hand ----------------------------------------------
    estimated_hours = round(gen_total * minutes_per_test / 60, 1)
    measured_note = "from our baseline test" if minutes_per_test_measured else "assumed, not measured"
    lines.append(
        f"- Estimated time by hand: {estimated_hours} hours "
        f"({gen_total} tests × {minutes_per_test:.0f} min, {measured_note})"
    )

    # --- real code changed ---------------------------------------------------
    if not git_available:
        lines.append("- Real code changed: could not check (git not available)")
    elif not files_changed:
        lines.append("- Real code changed: 0 files (checked with git)")
    else:
        lines.append(
            f"- **⚠ Real code changed: {len(files_changed)} file(s)** — "
            "revert with the commands below"
        )

    lines.append("")

    # --- warnings ------------------------------------------------------------
    existing_failing = metrics.get("existing_tests_failing_before", 0)
    if existing_failing:
        lines.append(
            f"> **Warning:** {existing_failing} existing test(s) were already "
            f"failing before test generation."
        )
        lines.append("")

    if files_changed:
        lines.append("## ⚠ Source files changed — revert before submitting")
        lines.append("")
        for f in files_changed:
            lines.append(f"- `{f}` — revert: `git checkout -- {f}`")
        lines.append("")

    # --- possible bugs -------------------------------------------------------
    xfails = results.get("xfails", [])
    if xfails:
        lines.append("## Possible bugs")
        lines.append("")
        for i, xf in enumerate(xfails, start=1):
            reason = xf.get("reason", "")
            test = xf.get("test", "")
            lines.append(f"{i}. `{test}` — {reason}")
        lines.append("")

    # --- could not fix automatically -----------------------------------------
    skips = results.get("skips", [])
    if skips:
        lines.append("## Could not fix automatically")
        lines.append("")
        for i, sk in enumerate(skips, start=1):
            reason = sk.get("reason", "")
            test = sk.get("test", "")
            lines.append(f"{i}. `{test}` — {reason}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(
    project: str | Path,
    minutes_per_test: float | None = None,
) -> int:
    """Build reports/report.md from all JSON artefacts and update metrics.json.

    Args:
        project:          Project name or path (name is used for the report title).
        minutes_per_test: Override per-test time estimate; defaults to 10 if absent.

    Returns:
        0 on success, 1 on fatal error.
    """
    rdir = reports_dir()

    # --- load artefacts ------------------------------------------------------
    metrics_path = rdir / "metrics.json"
    results_path = rdir / "results.json"
    gaps_path = rdir / "gaps.json"

    if not metrics_path.exists():
        print("error: reports/metrics.json not found. Run 'testgap scan' first.")
        return 1

    metrics = load_json(metrics_path)

    results: dict = {}
    if results_path.exists():
        results = load_json(results_path)

    gaps: dict = {}
    if gaps_path.exists():
        gaps = load_json(gaps_path)

    # Resolve project name
    if project:
        project_name = Path(project).name if Path(project).is_absolute() else str(project)
    else:
        project_name = metrics.get("project", "unknown")

    project_path_str = metrics.get("project", project_name)
    src = metrics.get("src", "")

    # --- timing --------------------------------------------------------------
    finished_at = datetime.now(timezone.utc)
    started_at_str: str = metrics.get("started_at", finished_at.isoformat(timespec="seconds"))
    try:
        started_at = _parse_iso(started_at_str)
        # Make both tz-aware for subtraction
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        run_seconds = int((finished_at - started_at).total_seconds())
    except (ValueError, TypeError):
        run_seconds = 0

    # --- minutes per test ----------------------------------------------------
    if minutes_per_test is not None:
        mpt = float(minutes_per_test)
        mpt_measured = True
    else:
        stored = metrics.get("minutes_per_test")
        if stored is not None:
            mpt = float(stored)
            mpt_measured = bool(metrics.get("minutes_per_test_measured", False))
        else:
            mpt = 10.0
            mpt_measured = False

    # --- change check (FR-12) ------------------------------------------------
    dirty_now = _git_dirty_paths(rdir.parent)
    git_available = dirty_now is not None
    dirty_before: list[str] = metrics.get("dirty_before", [])

    if git_available:
        files_changed = filter_changed_paths(
            dirty_now or [],  # type: ignore[arg-type]
            project_path_str,
            src,
            dirty_before,
        )
        source_prefix = f"{project_path_str}/{src}/"
        source_files_changed = sum(1 for f in files_changed if f.startswith(source_prefix))
    else:
        files_changed = []
        source_files_changed = 0

    # --- build markdown ------------------------------------------------------
    gen = results.get("generated", {})
    gen_total = gen.get("total", 0)
    estimated_hours = round(gen_total * mpt / 60, 1)

    report_md = _build_report(
        project=project_name,
        metrics=metrics,
        results=results,
        gaps=gaps,
        files_changed=files_changed,
        source_files_changed=source_files_changed,
        git_available=git_available,
        finished_at=finished_at,
        run_seconds=run_seconds,
        minutes_per_test=mpt,
        minutes_per_test_measured=mpt_measured,
    )

    # --- write report.md -----------------------------------------------------
    report_path = rdir / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    # --- update metrics.json -------------------------------------------------
    update_metrics(
        finished_at=finished_at.isoformat(timespec="seconds"),
        run_seconds=run_seconds,
        minutes_per_test=mpt,
        minutes_per_test_measured=mpt_measured,
        estimated_manual_hours=estimated_hours,
        files_changed=files_changed,
        source_files_changed=source_files_changed,
    )

    print(f"Report written to {report_path}")
    return 0

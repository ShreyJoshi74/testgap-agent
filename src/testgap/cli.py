"""Command dispatcher for testgap.

Usage::

    python -m testgap scan  --project <path> --label <before|after> [--src <dir>]
    python -m testgap gaps  --project <path> [--label before]
    python -m testgap run   --project <path>
    python -m testgap report [--project <path>] [--minutes-per-test <float>]
    python -m testgap clean --project <path>

Exit codes:
    0  Command completed successfully (even if tests failed — Bob reads the JSON).
    1  Tool error: missing deps, bad path, pytest internal/usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from testgap import __version__


# ---------------------------------------------------------------------------
# --src auto-detection
# ---------------------------------------------------------------------------

def detect_src(project: Path) -> str | None:
    """Return the single top-level source folder inside *project*.

    Picks every direct sub-directory that contains an ``__init__.py`` and is
    not named ``tests``.  Returns the folder name when exactly one candidate
    exists, or ``None`` when there are zero or multiple (caller must error).
    """
    candidates = [
        d.name
        for d in project.iterdir()
        if d.is_dir()
        and d.name != "tests"
        and (d / "__init__.py").exists()
    ]
    return candidates[0] if len(candidates) == 1 else None


# ---------------------------------------------------------------------------
# Sub-command implementations (thin shims — real logic lives in each module)
# ---------------------------------------------------------------------------

def _cmd_scan(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        return 1

    src = args.src
    if src is None:
        src = detect_src(project)
        if src is None:
            print(
                "error: could not auto-detect source directory.\n"
                "Pass --src <dir> explicitly (e.g. --src app).",
                file=sys.stderr,
            )
            return 1

    # Import lazily so missing deps produce the right error message via check_deps.
    from testgap import scan as scan_mod  # noqa: PLC0415
    return scan_mod.main(project=project, label=args.label, src=src)


def _cmd_gaps(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        return 1

    from testgap import find_gaps as gaps_mod  # noqa: PLC0415
    return gaps_mod.main(project=project, label=args.label)


def _cmd_run(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        return 1

    from testgap import run_tests as run_mod  # noqa: PLC0415
    return run_mod.main(project=project)


def _cmd_report(args: argparse.Namespace) -> int:
    from testgap.common import load_json, reports_dir  # noqa: PLC0415

    # Resolve --project: use explicit arg, or fall back to metrics.json.
    project_str: str | None = args.project
    if project_str is None:
        metrics_path = reports_dir() / "metrics.json"
        if not metrics_path.exists():
            print(
                "error: --project not given and reports/metrics.json not found.",
                file=sys.stderr,
            )
            return 1
        try:
            project_str = load_json(metrics_path)["project"]
        except KeyError:
            print(
                "error: metrics.json has no 'project' key. Pass --project explicitly.",
                file=sys.stderr,
            )
            return 1

    from testgap import report as report_mod  # noqa: PLC0415
    return report_mod.main(
        project=project_str,
        minutes_per_test=args.minutes_per_test,
    )


def _cmd_clean(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        return 1

    from testgap import clean as clean_mod  # noqa: PLC0415
    return clean_mod.main(project=project)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testgap",
        description="Find untested Python code and write tests with IBM Bob 2.0.",
    )
    parser.add_argument(
        "--version", action="version", version=f"testgap {__version__}"
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # --- scan ---
    p_scan = sub.add_parser("scan", help="Run pytest with coverage and record metrics.")
    p_scan.add_argument(
        "--project", required=True, metavar="PATH",
        help="Path to the target project folder.",
    )
    p_scan.add_argument(
        "--label", required=True, choices=["before", "after"],
        help="Label for the coverage snapshot: 'before' or 'after'.",
    )
    p_scan.add_argument(
        "--src", default=None, metavar="DIR",
        help="Source sub-directory to measure coverage for (auto-detected if omitted).",
    )

    # --- gaps ---
    p_gaps = sub.add_parser("gaps", help="Find and rank untested functions.")
    p_gaps.add_argument(
        "--project", required=True, metavar="PATH",
        help="Path to the target project folder.",
    )
    p_gaps.add_argument(
        "--label", default="before", metavar="LABEL",
        help="Which coverage snapshot to read (default: before).",
    )

    # --- run ---
    p_run = sub.add_parser("run", help="Run all tests and save results.json.")
    p_run.add_argument(
        "--project", required=True, metavar="PATH",
        help="Path to the target project folder.",
    )

    # --- report ---
    p_report = sub.add_parser("report", help="Build reports/report.md.")
    p_report.add_argument(
        "--project", default=None, metavar="PATH",
        help="Project path (defaults to the value stored in metrics.json).",
    )
    p_report.add_argument(
        "--minutes-per-test", type=float, default=None, metavar="FLOAT",
        help="Override the measured minutes-per-test for the time-saved estimate.",
    )

    # --- clean ---
    p_clean = sub.add_parser("clean", help="Delete generated tests and report files.")
    p_clean.add_argument(
        "--project", required=True, metavar="PATH",
        help="Path to the target project folder.",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse *argv* (defaults to sys.argv[1:]) and dispatch to the right command.

    Returns an integer exit code (0 = success, 1 = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "scan":   _cmd_scan,
        "gaps":   _cmd_gaps,
        "run":    _cmd_run,
        "report": _cmd_report,
        "clean":  _cmd_clean,
    }
    return dispatch[args.command](args)

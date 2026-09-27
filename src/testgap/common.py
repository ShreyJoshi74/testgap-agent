"""Shared helpers used by every testgap script."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Return the absolute path to the git repository root.

    Falls back to the current working directory if git is unavailable or the
    directory is not inside a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd().resolve()


def reports_dir() -> Path:
    """Return (and create if missing) <repo_root>/reports/."""
    path = repo_root() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def to_posix(path: str | Path) -> str:
    """Convert any path to a forward-slash string for JSON output."""
    return Path(path).as_posix()


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

_REQUIRED_PACKAGES = {
    "pytest": "pytest",
    "pytest_cov": "pytest-cov",
    "coverage": "coverage",
    "faker": "Faker",
    "pytest_timeout": "pytest-timeout",
}


def check_deps() -> None:
    """Verify all required packages are importable.

    Prints a clear message and exits 1 for each missing package (NFR-06).
    """
    missing = []
    for module_name, install_name in _REQUIRED_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            print(
                f"{install_name} not installed. "
                f"Run: pip install -r requirements.txt"
            )
            missing.append(install_name)
    if missing:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

def run_pytest(
    project: str | Path,
    extra_args: list[str] | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Run pytest inside *project* and return the CompletedProcess.

    Args:
        project:    Absolute path to the target project folder.
        extra_args: Additional arguments appended after the base flags.
        timeout:    Wall-clock timeout in seconds for the whole run (NFR-01).
                    Defaults to 600 s.

    Uses sys.executable so the same virtualenv is always used (NFR-02).
    The ``-p no:cacheprovider`` flag suppresses ``.pytest_cache`` writes so
    the working tree stays clean between runs.
    ``--timeout=30`` is a per-test cap supplied by pytest-timeout.
    """
    cmd = [
        sys.executable, "-m", "pytest",
        "-p", "no:cacheprovider",
        "--timeout=30",
        *(extra_args or []),
    ]
    return subprocess.run(
        cmd,
        cwd=str(Path(project).resolve()),
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_json(path: str | Path) -> dict:
    """Load and return a JSON file as a dict."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str | Path, data: dict) -> None:
    """Save *data* to *path* with sorted keys and 2-space indent (NFR-04)."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True, indent=2)
        fh.write("\n")


def update_metrics(**fields) -> None:
    """Merge *fields* into reports/metrics.json, creating the file if absent."""
    metrics_path = reports_dir() / "metrics.json"
    data: dict = {}
    if metrics_path.exists():
        data = load_json(metrics_path)
    data.update(fields)
    save_json(metrics_path, data)

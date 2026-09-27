"""clean — reset generated tests and report files between runs.

Public API
----------
    main(project) -> int
"""

from __future__ import annotations

from pathlib import Path

from testgap.common import reports_dir


def main(project: str | Path) -> int:
    """Delete generated test files and report artefacts, then return 0.

    Specifically:
    - Deletes ``<project>/tests/generated/test_*.py`` — never touches
      ``__init__.py``, ``conftest.py`` or any other file in that folder.
    - Deletes every file in ``reports/`` except ``.gitkeep``.

    Never touches anything outside those two folders.  Prints each removed path.

    Args:
        project: Absolute path to the target project folder.

    Returns:
        0 always.
    """
    project = Path(project).resolve()
    rdir = reports_dir()

    # --- generated test files ------------------------------------------------
    generated_dir = project / "tests" / "generated"
    if generated_dir.is_dir():
        for path in sorted(generated_dir.glob("test_*.py")):
            path.unlink()
            print(f"removed {path}")

    # --- report artefacts ----------------------------------------------------
    if rdir.is_dir():
        for path in sorted(rdir.iterdir()):
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
                print(f"removed {path}")

    return 0

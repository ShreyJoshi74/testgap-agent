"""Unit tests for testgap.clean (Task 2.6)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from testgap.clean import main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal project + reports layout and return (project, rdir)."""
    project = tmp_path / "myproject"
    gen = project / "tests" / "generated"
    gen.mkdir(parents=True)

    # Files that SHOULD be deleted
    (gen / "test_orders.py").write_text("# generated", encoding="utf-8")
    (gen / "test_users.py").write_text("# generated", encoding="utf-8")

    # Files that must SURVIVE
    (gen / "__init__.py").write_text("", encoding="utf-8")
    (gen / "conftest.py").write_text("# conf", encoding="utf-8")
    (gen / "helper.py").write_text("# helper (not test_*)", encoding="utf-8")

    rdir = tmp_path / "reports"
    rdir.mkdir()

    # Report files that SHOULD be deleted
    (rdir / "gaps.json").write_text("{}", encoding="utf-8")
    (rdir / "metrics.json").write_text("{}", encoding="utf-8")
    (rdir / "report.md").write_text("# r", encoding="utf-8")

    # .gitkeep must SURVIVE
    (rdir / ".gitkeep").write_text("", encoding="utf-8")

    return project, rdir


def _run(project: Path, rdir: Path) -> int:
    with mock.patch("testgap.clean.reports_dir", return_value=rdir):
        return main(project)


# ---------------------------------------------------------------------------
# deletion behaviour
# ---------------------------------------------------------------------------

class TestCleanDeletes:
    def test_deletes_test_star_py(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        gen = project / "tests" / "generated"
        assert not (gen / "test_orders.py").exists()
        assert not (gen / "test_users.py").exists()

    def test_deletes_report_files(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        assert not (rdir / "gaps.json").exists()
        assert not (rdir / "metrics.json").exists()
        assert not (rdir / "report.md").exists()


class TestCleanPreserves:
    def test_keeps_init_py(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        assert (project / "tests" / "generated" / "__init__.py").exists()

    def test_keeps_conftest_py(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        assert (project / "tests" / "generated" / "conftest.py").exists()

    def test_keeps_non_test_py(self, tmp_path):
        """A file named helper.py (not test_*.py) must survive."""
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        assert (project / "tests" / "generated" / "helper.py").exists()

    def test_keeps_gitkeep(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        assert (rdir / ".gitkeep").exists()

    def test_files_outside_folders_survive(self, tmp_path):
        """A source file outside the two managed folders must never be touched."""
        project, rdir = _make_project(tmp_path)
        outside = project / "app" / "orders.py"
        outside.parent.mkdir(parents=True)
        outside.write_text("# source", encoding="utf-8")

        _run(project, rdir)

        assert outside.exists(), "source file outside managed folders was deleted"


class TestCleanEdgeCases:
    def test_no_generated_dir_is_fine(self, tmp_path):
        """If tests/generated/ does not exist, clean should still return 0."""
        project = tmp_path / "proj"
        project.mkdir()
        rdir = tmp_path / "reports"
        rdir.mkdir()
        rc = _run(project, rdir)
        assert rc == 0

    def test_empty_generated_dir_is_fine(self, tmp_path):
        project = tmp_path / "proj"
        (project / "tests" / "generated").mkdir(parents=True)
        rdir = tmp_path / "reports"
        rdir.mkdir()
        rc = _run(project, rdir)
        assert rc == 0

    def test_returns_0(self, tmp_path):
        project, rdir = _make_project(tmp_path)
        assert _run(project, rdir) == 0

    def test_prints_removed_paths(self, tmp_path, capsys):
        project, rdir = _make_project(tmp_path)
        _run(project, rdir)
        out = capsys.readouterr().out
        assert "test_orders.py" in out
        assert "gaps.json" in out

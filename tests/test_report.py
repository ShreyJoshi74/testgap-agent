"""Unit tests for testgap.report (Task 2.7)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from testgap.report import filter_changed_paths, main


# ---------------------------------------------------------------------------
# Fixture JSON data
# ---------------------------------------------------------------------------

_METRICS = {
    "project": "sample_project",
    "src": "app",
    "started_at": "2026-10-02T10:00:05",
    "dirty_before": [],
    "coverage_before": 22.4,
    "coverage_after": 78.9,
    "tests_before": 4,
    "tests_after": 56,
    "existing_tests_failing_before": 0,
    "generated_total": 52,
    "generated_passed": 48,
    "pass_rate": 0.923,
    "possible_bugs": 2,
    "could_not_fix": 1,
}

_RESULTS = {
    "total": 56,
    "passed": 52,
    "failed": 1,
    "errors": 0,
    "xfailed": 2,
    "skipped": 1,
    "generated": {
        "total": 52,
        "passed": 48,
        "failed": 1,
        "errors": 0,
        "xfailed": 2,
        "skipped": 1,
        "pass_rate": 0.923,
    },
    "failures": [
        {
            "test": "tests/generated/test_orders.py::test_apply_discount_over_100_percent",
            "file": "tests/generated/test_orders.py",
            "kind": "failed",
            "message": "AssertionError: expected ValueError",
        }
    ],
    "failures_by_file": {"tests/generated/test_orders.py": 1},
    "xfails": [
        {
            "test": "tests/generated/test_orders.py::test_apply_discount_rejects_over_100",
            "file": "tests/generated/test_orders.py",
            "reason": "Possible bug: README says max discount is 100%, code accepts 150%",
        },
        {
            "test": "tests/generated/test_orders.py::test_apply_discount_rejects_over_50",
            "file": "tests/generated/test_orders.py",
            "reason": "Possible bug: another discount issue",
        },
    ],
    "skips": [
        {
            "test": "tests/generated/test_users.py::test_register_user_duplicate_email",
            "file": "tests/generated/test_users.py",
            "reason": "Could not fix automatically: depends on database state",
        }
    ],
}

_GAPS = {
    "project": "sample_project",
    "src": "app",
    "coverage_label": "before",
    "coverage_percent": 22.4,
    "unattributed_missing_lines": 3,
    "gaps": [
        {
            "id": "G-001",
            "file": "app/orders.py",
            "function": "calculate_total",
            "start_line": 12,
            "end_line": 34,
            "missing_lines": [15, 16, 20, 21, 22, 23, 27, 28, 30],
            "score": 28,
            "priority": "high",
            "reason": "Public function, 9 untested lines, named in README",
        }
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rdir(tmp_path: Path, metrics=None, results=None, gaps=None) -> Path:
    """Write fixture JSON files to a temporary reports dir."""
    rdir = tmp_path / "reports"
    rdir.mkdir()
    m = metrics if metrics is not None else _METRICS
    (rdir / "metrics.json").write_text(json.dumps(m), encoding="utf-8")
    if results is not None:
        (rdir / "results.json").write_text(json.dumps(results), encoding="utf-8")
    if gaps is not None:
        (rdir / "gaps.json").write_text(json.dumps(gaps), encoding="utf-8")
    return rdir


def _run_main(rdir: Path, project="sample_project", minutes_per_test=None,
              git_paths=None) -> tuple[int, str]:
    """Run main() with patched reports_dir / git, return (rc, report_text)."""
    if git_paths is None:
        git_paths = []

    with mock.patch("testgap.report.reports_dir", return_value=rdir):
        with mock.patch("testgap.report._git_dirty_paths", return_value=git_paths):
            with mock.patch("testgap.report.update_metrics"):
                rc = main(project=project, minutes_per_test=minutes_per_test)

    report_path = rdir / "report.md"
    text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    return rc, text


# ---------------------------------------------------------------------------
# filter_changed_paths
# ---------------------------------------------------------------------------

class TestFilterChangedPaths:
    def test_removes_generated_tests(self):
        paths = [
            "sample_project/tests/generated/test_orders.py",
            "sample_project/app/orders.py",
        ]
        result = filter_changed_paths(paths, "sample_project", "app", [])
        assert "sample_project/tests/generated/test_orders.py" not in result
        assert "sample_project/app/orders.py" in result

    def test_removes_reports_folder(self):
        paths = [
            "reports/gaps.json",
            "reports/metrics.json",
            "sample_project/app/orders.py",
        ]
        result = filter_changed_paths(paths, "sample_project", "app", [])
        assert "reports/gaps.json" not in result
        assert "reports/metrics.json" not in result
        assert "sample_project/app/orders.py" in result

    def test_removes_dirty_before_paths(self):
        paths = ["sample_project/app/orders.py", "sample_project/README.md"]
        dirty_before = ["sample_project/README.md"]
        result = filter_changed_paths(paths, "sample_project", "app", dirty_before)
        assert "sample_project/README.md" not in result
        assert "sample_project/app/orders.py" in result

    def test_new_untracked_file_in_app_reported(self):
        """A new file in app/ not in dirty_before must appear in result."""
        paths = ["sample_project/app/new_module.py"]
        result = filter_changed_paths(paths, "sample_project", "app", [])
        assert "sample_project/app/new_module.py" in result

    def test_edited_test_basic_reported(self):
        """An edit to tests/test_basic.py (not in generated/) is reported."""
        paths = ["sample_project/tests/test_basic.py"]
        result = filter_changed_paths(paths, "sample_project", "app", [])
        assert "sample_project/tests/test_basic.py" in result

    def test_empty_paths_returns_empty(self):
        assert filter_changed_paths([], "sample_project", "app", []) == []

    def test_all_allowed_returns_empty(self):
        paths = [
            "sample_project/tests/generated/test_x.py",
            "reports/coverage_before.json",
        ]
        result = filter_changed_paths(paths, "sample_project", "app", [])
        assert result == []


# ---------------------------------------------------------------------------
# main() — report content
# ---------------------------------------------------------------------------

class TestReportContent:
    def test_returns_0(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        rc, _ = _run_main(rdir)
        assert rc == 0

    def test_writes_report_md(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _run_main(rdir)
        assert (rdir / "report.md").exists()

    def test_contains_project_title(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "sample_project" in text

    def test_contains_coverage_before(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "22.4" in text

    def test_contains_coverage_after(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "78.9" in text

    def test_contains_pass_rate(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        # 48/52 = 92.3%
        assert "92.3" in text

    def test_zero_files_changed_clean(self, tmp_path):
        """Clean run → 'Real code changed: 0 files'."""
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir, git_paths=[])
        assert "0 files" in text

    def test_warning_when_source_changed(self, tmp_path):
        """When a source file is dirty, a warning appears in the report."""
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(
            rdir,
            git_paths=["sample_project/app/orders.py"],
        )
        assert "sample_project/app/orders.py" in text
        assert "git checkout" in text

    def test_possible_bugs_listed(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "Possible bugs" in text
        assert "README says max discount is 100%" in text

    def test_could_not_fix_listed(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "Could not fix automatically" in text
        assert "depends on database state" in text

    def test_git_unavailable_message(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        with mock.patch("testgap.report.reports_dir", return_value=rdir):
            with mock.patch("testgap.report._git_dirty_paths", return_value=None):
                with mock.patch("testgap.report.update_metrics"):
                    main(project="sample_project")
        text = (rdir / "report.md").read_text(encoding="utf-8")
        assert "git not available" in text

    def test_existing_tests_failing_warning(self, tmp_path):
        metrics = {**_METRICS, "existing_tests_failing_before": 2}
        rdir = _make_rdir(tmp_path, metrics=metrics, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "2 existing test" in text

    def test_minutes_per_test_explicit(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir, minutes_per_test=15.0)
        assert "15" in text

    def test_minutes_per_test_default_10_assumed(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir, minutes_per_test=None)
        assert "assumed, not measured" in text

    def test_run_time_in_report(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "Tool run time" in text

    def test_missing_metrics_returns_1(self, tmp_path):
        rdir = tmp_path / "reports"
        rdir.mkdir()
        # No metrics.json written
        with mock.patch("testgap.report.reports_dir", return_value=rdir):
            rc = main(project="sample_project")
        assert rc == 1

    def test_no_xfails_no_possible_bugs_section(self, tmp_path):
        results_no_xfails = {**_RESULTS, "xfails": [], "skips": []}
        rdir = _make_rdir(tmp_path, results=results_no_xfails, gaps=_GAPS)
        _, text = _run_main(rdir)
        assert "Possible bugs" not in text
        assert "Could not fix automatically" not in text

    def test_updates_metrics_json(self, tmp_path):
        rdir = _make_rdir(tmp_path, results=_RESULTS, gaps=_GAPS)
        called_with: dict = {}

        def fake_update(**kw):
            called_with.update(kw)

        with mock.patch("testgap.report.reports_dir", return_value=rdir):
            with mock.patch("testgap.report._git_dirty_paths", return_value=[]):
                with mock.patch("testgap.report.update_metrics", side_effect=fake_update):
                    main(project="sample_project")

        assert "finished_at" in called_with
        assert "run_seconds" in called_with
        assert "files_changed" in called_with
        assert "source_files_changed" in called_with

    def test_missing_results_json_still_works(self, tmp_path):
        """report.py should succeed with only metrics.json present."""
        rdir = _make_rdir(tmp_path)  # no results, no gaps
        rc, text = _run_main(rdir)
        assert rc == 0
        assert "sample_project" in text

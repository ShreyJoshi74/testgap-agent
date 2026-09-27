"""Unit tests for testgap.scan."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from testgap.scan import _dirty_paths, _read_coverage_percent, main


# ---------------------------------------------------------------------------
# helpers: minimal fake coverage JSON
# ---------------------------------------------------------------------------

def _write_coverage_json(path: Path, percent: float) -> None:
    data = {
        "meta": {"version": "7.0.0", "timestamp": "2026-01-01"},
        "totals": {
            "covered_lines": 10,
            "num_statements": 20,
            "percent_covered": percent,
            "missing_lines": 10,
        },
        "files": {},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# _dirty_paths
# ---------------------------------------------------------------------------

class TestDirtyPaths:
    def test_returns_empty_when_clean(self, tmp_path):
        with mock.patch("testgap.scan._sp.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="", returncode=0)
            result = _dirty_paths(tmp_path)
        assert result == []

    def test_parses_modified_files(self, tmp_path):
        with mock.patch("testgap.scan._sp.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=" M app/orders.py\n?? reports/gaps.json\n",
                returncode=0,
            )
            result = _dirty_paths(tmp_path)
        assert "app/orders.py" in result
        assert "reports/gaps.json" in result

    def test_returns_empty_on_git_failure(self, tmp_path):
        with mock.patch(
            "testgap.scan._sp.run",
            side_effect=subprocess.CalledProcessError(128, "git"),
        ):
            result = _dirty_paths(tmp_path)
        assert result == []

    def test_returns_empty_when_git_not_found(self, tmp_path):
        with mock.patch("testgap.scan._sp.run", side_effect=FileNotFoundError):
            result = _dirty_paths(tmp_path)
        assert result == []

    def test_converts_backslashes_to_forward(self, tmp_path):
        with mock.patch("testgap.scan._sp.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=" M app\\orders.py\n",
                returncode=0,
            )
            result = _dirty_paths(tmp_path)
        assert "app/orders.py" in result

    def test_result_is_sorted(self, tmp_path):
        with mock.patch("testgap.scan._sp.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=" M z_file.py\n M a_file.py\n",
                returncode=0,
            )
            result = _dirty_paths(tmp_path)
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# _read_coverage_percent
# ---------------------------------------------------------------------------

class TestReadCoveragePercent:
    def test_reads_percent_covered(self, tmp_path):
        cov = tmp_path / "coverage.json"
        _write_coverage_json(cov, 22.4)
        assert _read_coverage_percent(cov) == pytest.approx(22.4)

    def test_rounds_to_one_decimal(self, tmp_path):
        cov = tmp_path / "coverage.json"
        _write_coverage_json(cov, 78.9456)
        result = _read_coverage_percent(cov)
        # round() to 1dp
        assert result == pytest.approx(78.9, abs=0.05)


# ---------------------------------------------------------------------------
# main() — label=before
# ---------------------------------------------------------------------------

class TestScanMainBefore:
    def _run(self, tmp_path, returncode=0, coverage_pct=22.4,
             dirty=None, write_cov=True, write_junit=True):
        """Helper: patch subprocess and filesystem, call main(before)."""
        project = tmp_path / "project"
        project.mkdir()
        rdir = tmp_path / "reports"
        rdir.mkdir()

        cov_json = rdir / "coverage_before.json"
        junit_xml = rdir / "junit_before.xml"

        if write_cov:
            _write_coverage_json(cov_json, coverage_pct)

        if write_junit:
            # Minimal valid JUnit XML
            junit_xml.write_text(
                '<?xml version="1.0"?>'
                '<testsuites><testsuite name="pytest" errors="0" failures="0"'
                ' skipped="0" tests="4" time="1.0">'
                '<testcase classname="tests.test_a" name="test_one" time="0.1"/>'
                '<testcase classname="tests.test_a" name="test_two" time="0.1"/>'
                '<testcase classname="tests.test_a" name="test_three" time="0.1"/>'
                '<testcase classname="tests.test_a" name="test_four" time="0.1"/>'
                '</testsuite></testsuites>',
                encoding="utf-8",
            )

        proc_mock = mock.Mock(returncode=returncode)

        with mock.patch("testgap.scan.check_deps"):
            with mock.patch("testgap.scan.reports_dir", return_value=rdir):
                with mock.patch("testgap.scan._dirty_paths",
                                return_value=dirty or []):
                    with mock.patch("testgap.scan.update_metrics") as m_metrics:
                        with mock.patch("testgap.scan._sp.run",
                                        return_value=proc_mock):
                            rc = main(project, label="before", src="app")

        return rc, rdir, m_metrics

    def test_returns_0_on_success(self, tmp_path):
        rc, _, _ = self._run(tmp_path)
        assert rc == 0

    def test_records_project_and_src(self, tmp_path):
        _, _, m = self._run(tmp_path)
        calls = [c.kwargs for c in m.call_args_list]
        first_call = calls[0]
        assert first_call.get("project") == "project"
        assert first_call.get("src") == "app"

    def test_records_started_at(self, tmp_path):
        _, _, m = self._run(tmp_path)
        calls = [c.kwargs for c in m.call_args_list]
        assert any("started_at" in c for c in calls)

    def test_records_dirty_before(self, tmp_path):
        _, _, m = self._run(tmp_path, dirty=["app/orders.py"])
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("dirty_before") == ["app/orders.py"] for c in calls)

    def test_records_coverage_before(self, tmp_path):
        _, _, m = self._run(tmp_path, coverage_pct=22.4)
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("coverage_before") == pytest.approx(22.4) for c in calls)

    def test_records_tests_before(self, tmp_path):
        _, _, m = self._run(tmp_path)
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("tests_before") == 4 for c in calls)

    def test_records_existing_tests_failing_zero(self, tmp_path):
        _, _, m = self._run(tmp_path, returncode=0)
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("existing_tests_failing_before") == 0 for c in calls)

    def test_records_existing_tests_failing_nonzero(self, tmp_path):
        # rc=1 means some tests already fail
        _, _, m = self._run(tmp_path, returncode=1)
        calls = [c.kwargs for c in m.call_args_list]
        assert any("existing_tests_failing_before" in c for c in calls)
        val = next(
            c["existing_tests_failing_before"]
            for c in calls
            if "existing_tests_failing_before" in c
        )
        assert val >= 0

    def test_returns_1_on_pytest_usage_error(self, tmp_path):
        rc, _, _ = self._run(tmp_path, returncode=2)
        assert rc == 1

    def test_returns_1_on_pytest_internal_error(self, tmp_path):
        rc, _, _ = self._run(tmp_path, returncode=4)
        assert rc == 1

    def test_no_coverage_file_treated_as_zero(self, tmp_path):
        rc, _, m = self._run(tmp_path, returncode=5, write_cov=False)
        assert rc == 0
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("coverage_before") == 0.0 for c in calls)

    def test_no_junit_file_treated_as_zero_tests(self, tmp_path):
        rc, _, m = self._run(tmp_path, returncode=5,
                             write_cov=False, write_junit=False)
        assert rc == 0
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("tests_before") == 0 for c in calls)


# ---------------------------------------------------------------------------
# main() — label=after
# ---------------------------------------------------------------------------

class TestScanMainAfter:
    def _run(self, tmp_path, coverage_pct=78.9):
        project = tmp_path / "project"
        project.mkdir()
        rdir = tmp_path / "reports"
        rdir.mkdir()

        cov_json = rdir / "coverage_after.json"
        _write_coverage_json(cov_json, coverage_pct)

        junit_xml = rdir / "junit_after.xml"
        junit_xml.write_text(
            '<?xml version="1.0"?>'
            '<testsuites><testsuite name="pytest" errors="0" failures="0"'
            ' skipped="0" tests="10" time="1.0">'
            + ''.join(
                f'<testcase classname="tests.test_a" name="t{i}" time="0.1"/>'
                for i in range(10)
            )
            + '</testsuite></testsuites>',
            encoding="utf-8",
        )

        proc_mock = mock.Mock(returncode=0)
        with mock.patch("testgap.scan.check_deps"):
            with mock.patch("testgap.scan.reports_dir", return_value=rdir):
                with mock.patch("testgap.scan.update_metrics") as m_metrics:
                    with mock.patch("testgap.scan._sp.run",
                                    return_value=proc_mock):
                        rc = main(project, label="after", src="app")

        return rc, m_metrics

    def test_returns_0(self, tmp_path):
        rc, _ = self._run(tmp_path)
        assert rc == 0

    def test_does_not_write_dirty_before(self, tmp_path):
        """scan --label after must NOT reset metrics.json."""
        _, m = self._run(tmp_path)
        calls = [c.kwargs for c in m.call_args_list]
        assert not any("dirty_before" in c for c in calls)
        assert not any("started_at" in c for c in calls)

    def test_records_coverage_after(self, tmp_path):
        _, m = self._run(tmp_path, coverage_pct=78.9)
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("coverage_after") == pytest.approx(78.9) for c in calls)

    def test_records_tests_after(self, tmp_path):
        _, m = self._run(tmp_path)
        calls = [c.kwargs for c in m.call_args_list]
        assert any(c.get("tests_after") == 10 for c in calls)


# ---------------------------------------------------------------------------
# subprocess command shape
# ---------------------------------------------------------------------------

class TestScanSubprocessCommand:
    def test_uses_sys_executable(self, tmp_path):
        import sys
        project = tmp_path / "project"
        project.mkdir()
        rdir = tmp_path / "reports"
        rdir.mkdir()
        _write_coverage_json(rdir / "coverage_before.json", 50.0)
        (rdir / "junit_before.xml").write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" time="0">'
            '</testsuite></testsuites>',
            encoding="utf-8",
        )

        proc_mock = mock.Mock(returncode=0)
        with mock.patch("testgap.scan.check_deps"):
            with mock.patch("testgap.scan.reports_dir", return_value=rdir):
                with mock.patch("testgap.scan._dirty_paths", return_value=[]):
                    with mock.patch("testgap.scan.update_metrics"):
                        with mock.patch("testgap.scan._sp.run",
                                        return_value=proc_mock) as mock_run:
                            main(project, label="before", src="app")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "-m" in cmd
        assert "pytest" in cmd

    def test_coverage_file_env_set(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        rdir = tmp_path / "reports"
        rdir.mkdir()
        _write_coverage_json(rdir / "coverage_before.json", 50.0)
        (rdir / "junit_before.xml").write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" time="0">'
            '</testsuite></testsuites>',
            encoding="utf-8",
        )

        proc_mock = mock.Mock(returncode=0)
        with mock.patch("testgap.scan.check_deps"):
            with mock.patch("testgap.scan.reports_dir", return_value=rdir):
                with mock.patch("testgap.scan._dirty_paths", return_value=[]):
                    with mock.patch("testgap.scan.update_metrics"):
                        with mock.patch("testgap.scan._sp.run",
                                        return_value=proc_mock) as mock_run:
                            main(project, label="before", src="app")

        kwargs = mock_run.call_args[1]
        assert "COVERAGE_FILE" in kwargs["env"]
        assert ".coverage" in kwargs["env"]["COVERAGE_FILE"]

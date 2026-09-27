"""Unit tests for testgap.common."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from testgap.common import (
    check_deps,
    load_json,
    repo_root,
    reports_dir,
    run_pytest,
    save_json,
    to_posix,
    update_metrics,
)


# ---------------------------------------------------------------------------
# to_posix
# ---------------------------------------------------------------------------

class TestToPosix:
    def test_string_unchanged_on_posix_input(self):
        assert to_posix("app/orders.py") == "app/orders.py"

    def test_backslashes_converted(self):
        assert to_posix("app\\orders.py") == "app/orders.py"

    def test_accepts_path_object(self):
        assert to_posix(Path("a") / "b" / "c.py") == "a/b/c.py"

    def test_absolute_path(self, tmp_path):
        p = tmp_path / "sub" / "file.py"
        result = to_posix(p)
        assert "\\" not in result


# ---------------------------------------------------------------------------
# repo_root
# ---------------------------------------------------------------------------

class TestRepoRoot:
    def test_returns_path_object(self):
        result = repo_root()
        assert isinstance(result, Path)

    def test_returns_absolute_path(self):
        assert repo_root().is_absolute()

    def test_fallback_to_cwd_when_git_fails(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with mock.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(128, "git"),
        ):
            result = repo_root()
        assert result == tmp_path.resolve()

    def test_fallback_when_git_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            result = repo_root()
        assert result == tmp_path.resolve()


# ---------------------------------------------------------------------------
# reports_dir
# ---------------------------------------------------------------------------

class TestReportsDir:
    def test_returns_path_named_reports(self):
        result = reports_dir()
        assert result.name == "reports"

    def test_directory_is_created(self, tmp_path):
        with mock.patch("testgap.common.repo_root", return_value=tmp_path):
            path = reports_dir()
        assert path.is_dir()

    def test_idempotent_when_dir_already_exists(self, tmp_path):
        (tmp_path / "reports").mkdir()
        with mock.patch("testgap.common.repo_root", return_value=tmp_path):
            path = reports_dir()
        assert path.is_dir()


# ---------------------------------------------------------------------------
# check_deps
# ---------------------------------------------------------------------------

class TestCheckDeps:
    def test_passes_when_all_present(self):
        # All packages are installed in this environment; should not raise or exit.
        with mock.patch("sys.exit") as mock_exit:
            check_deps()
        mock_exit.assert_not_called()

    def test_exits_1_when_package_missing(self, capsys):
        with mock.patch("importlib.util.find_spec", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                check_deps()
        assert exc_info.value.code == 1

    def test_prints_install_hint_on_missing(self, capsys):
        # Make only pytest appear missing.
        original = __import__("importlib").util.find_spec

        def fake_find_spec(name):
            return None if name == "pytest" else original(name)

        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec):
            with pytest.raises(SystemExit):
                check_deps()

        captured = capsys.readouterr()
        assert "pip install -r requirements.txt" in captured.out


# ---------------------------------------------------------------------------
# save_json / load_json
# ---------------------------------------------------------------------------

class TestSaveLoadJson:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "data.json"
        data = {"b": 2, "a": 1}
        save_json(path, data)
        assert load_json(path) == data

    def test_keys_are_sorted(self, tmp_path):
        path = tmp_path / "data.json"
        save_json(path, {"z": 3, "a": 1, "m": 2})
        raw = path.read_text(encoding="utf-8")
        keys = [line.strip().split(":")[0].strip('"') for line in raw.splitlines() if ":" in line]
        assert keys == sorted(keys)

    def test_indent_is_two_spaces(self, tmp_path):
        path = tmp_path / "data.json"
        save_json(path, {"key": "value"})
        raw = path.read_text(encoding="utf-8")
        assert '  "key"' in raw

    def test_file_ends_with_newline(self, tmp_path):
        path = tmp_path / "data.json"
        save_json(path, {"x": 1})
        assert path.read_text(encoding="utf-8").endswith("\n")

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_json(tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# update_metrics
# ---------------------------------------------------------------------------

class TestUpdateMetrics:
    def test_creates_file_when_absent(self, tmp_path):
        with mock.patch("testgap.common.reports_dir", return_value=tmp_path):
            update_metrics(coverage_before=22.4)
        data = load_json(tmp_path / "metrics.json")
        assert data["coverage_before"] == 22.4

    def test_merges_into_existing_file(self, tmp_path):
        metrics = tmp_path / "metrics.json"
        save_json(metrics, {"coverage_before": 22.4})
        with mock.patch("testgap.common.reports_dir", return_value=tmp_path):
            update_metrics(coverage_after=78.9)
        data = load_json(metrics)
        assert data["coverage_before"] == 22.4
        assert data["coverage_after"] == 78.9

    def test_overwrite_existing_field(self, tmp_path):
        metrics = tmp_path / "metrics.json"
        save_json(metrics, {"project": "old"})
        with mock.patch("testgap.common.reports_dir", return_value=tmp_path):
            update_metrics(project="new")
        assert load_json(metrics)["project"] == "new"


# ---------------------------------------------------------------------------
# run_pytest
# ---------------------------------------------------------------------------

class TestRunPytest:
    def test_uses_sys_executable(self, tmp_path):
        """run_pytest must call sys.executable, not a bare 'python'."""
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path)
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable

    def test_includes_no_cacheprovider(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "-p" in cmd
        assert "no:cacheprovider" in cmd

    def test_includes_timeout_flag(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "--timeout=30" in cmd

    def test_extra_args_appended(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path, extra_args=["--cov=app", "-q"])
        cmd = mock_run.call_args[0][0]
        assert "--cov=app" in cmd
        assert "-q" in cmd

    def test_cwd_is_absolute_project_path(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path)
        kwargs = mock_run.call_args[1]
        assert kwargs["cwd"] == str(tmp_path.resolve())

    def test_default_timeout_passed_to_subprocess(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path)
        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 600

    def test_custom_timeout_passed_to_subprocess(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            run_pytest(tmp_path, timeout=120)
        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 120

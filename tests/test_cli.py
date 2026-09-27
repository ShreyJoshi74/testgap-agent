"""Unit tests for testgap.cli."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

from testgap.cli import build_parser, detect_src, main


# ---------------------------------------------------------------------------
# detect_src
# ---------------------------------------------------------------------------

class TestDetectSrc:
    def test_returns_single_package_dir(self, tmp_path):
        app = tmp_path / "app"
        app.mkdir()
        (app / "__init__.py").touch()
        assert detect_src(tmp_path) == "app"

    def test_ignores_tests_directory(self, tmp_path):
        app = tmp_path / "app"
        app.mkdir()
        (app / "__init__.py").touch()
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").touch()
        assert detect_src(tmp_path) == "app"

    def test_returns_none_when_no_candidates(self, tmp_path):
        (tmp_path / "plain_dir").mkdir()
        assert detect_src(tmp_path) is None

    def test_returns_none_when_multiple_candidates(self, tmp_path):
        for name in ("app", "lib"):
            d = tmp_path / name
            d.mkdir()
            (d / "__init__.py").touch()
        assert detect_src(tmp_path) is None

    def test_ignores_dirs_without_init(self, tmp_path):
        # A dir without __init__.py must not be treated as a package.
        (tmp_path / "scripts").mkdir()
        app = tmp_path / "app"
        app.mkdir()
        (app / "__init__.py").touch()
        assert detect_src(tmp_path) == "app"


# ---------------------------------------------------------------------------
# build_parser — structure checks
# ---------------------------------------------------------------------------

class TestBuildParser:
    def setup_method(self):
        self.parser = build_parser()

    def test_subcommands_registered(self):
        # Each sub-command must be parseable without error.
        for cmd, extra in [
            (["scan", "--project", ".", "--label", "before"], None),
            (["gaps", "--project", "."], None),
            (["run", "--project", "."], None),
            (["report"], None),
            (["clean", "--project", "."], None),
        ]:
            args = self.parser.parse_args(cmd)
            assert args.command == cmd[0]

    def test_scan_label_choices(self):
        for label in ("before", "after"):
            args = self.parser.parse_args(["scan", "--project", ".", "--label", label])
            assert args.label == label

    def test_scan_label_rejects_invalid(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["scan", "--project", ".", "--label", "invalid"])

    def test_scan_src_defaults_to_none(self):
        args = self.parser.parse_args(["scan", "--project", ".", "--label", "before"])
        assert args.src is None

    def test_scan_src_explicit(self):
        args = self.parser.parse_args(
            ["scan", "--project", ".", "--label", "before", "--src", "myapp"]
        )
        assert args.src == "myapp"

    def test_gaps_label_defaults_to_before(self):
        args = self.parser.parse_args(["gaps", "--project", "."])
        assert args.label == "before"

    def test_report_project_defaults_to_none(self):
        args = self.parser.parse_args(["report"])
        assert args.project is None

    def test_report_minutes_per_test_parsed_as_float(self):
        args = self.parser.parse_args(["report", "--minutes-per-test", "12.5"])
        assert args.minutes_per_test == pytest.approx(12.5)

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "testgap" in captured.out

    def test_no_subcommand_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args([])
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# main() dispatch — each sub-command forwarded to the right module
# ---------------------------------------------------------------------------

class TestMainDispatch:
    """main() must call the matching module's main() and return its code."""

    def _run(self, argv, module_path, fake_main=None):
        """Patch *module_path* and call cli.main(argv). Returns exit code."""
        if fake_main is None:
            fake_main = mock.Mock(return_value=0)
        with mock.patch(module_path, fake_main):
            return main(argv)

    # -- scan --

    def test_scan_calls_scan_main(self, tmp_path):
        fake = mock.Mock(return_value=0)
        # create a detectable src dir so auto-detect works
        app = tmp_path / "app"
        app.mkdir()
        (app / "__init__.py").touch()
        with mock.patch("testgap.cli._cmd_scan") as mock_cmd:
            mock_cmd.return_value = 0
            rc = main(["scan", "--project", str(tmp_path), "--label", "before"])
        assert rc == 0
        mock_cmd.assert_called_once()

    def test_scan_returns_1_for_missing_project(self, tmp_path):
        rc = main(["scan", "--project", str(tmp_path / "nonexistent"), "--label", "before"])
        assert rc == 1

    def test_scan_returns_1_when_src_undetectable(self, tmp_path):
        # No __init__.py in any subdir → auto-detect fails before import.
        (tmp_path / "scripts").mkdir()
        rc = main(["scan", "--project", str(tmp_path), "--label", "before"])
        assert rc == 1

    # -- gaps --

    def test_gaps_calls_gaps_main(self, tmp_path):
        with mock.patch("testgap.cli._cmd_gaps") as mock_cmd:
            mock_cmd.return_value = 0
            rc = main(["gaps", "--project", str(tmp_path)])
        assert rc == 0

    def test_gaps_returns_1_for_missing_project(self, tmp_path):
        rc = main(["gaps", "--project", str(tmp_path / "nonexistent")])
        assert rc == 1

    # -- run --

    def test_run_calls_run_main(self, tmp_path):
        with mock.patch("testgap.cli._cmd_run") as mock_cmd:
            mock_cmd.return_value = 0
            rc = main(["run", "--project", str(tmp_path)])
        assert rc == 0

    def test_run_returns_1_for_missing_project(self, tmp_path):
        rc = main(["run", "--project", str(tmp_path / "nonexistent")])
        assert rc == 1

    # -- report --

    def test_report_calls_report_main(self, tmp_path):
        with mock.patch("testgap.cli._cmd_report") as mock_cmd:
            mock_cmd.return_value = 0
            rc = main(["report", "--project", str(tmp_path)])
        assert rc == 0

    def test_report_reads_project_from_metrics_json(self, tmp_path):
        """When --project is omitted, project name is read from metrics.json."""
        import json

        metrics = tmp_path / "metrics.json"
        metrics.write_text(json.dumps({"project": "sample_project"}), encoding="utf-8")

        # Patch at the _cmd_report level; report module doesn't exist yet.
        with mock.patch("testgap.common.reports_dir", return_value=tmp_path):
            with mock.patch("testgap.cli._cmd_report", return_value=0) as mock_cmd:
                rc = main(["report"])
        assert rc == 0
        mock_cmd.assert_called_once()

    def test_report_returns_1_when_no_metrics_and_no_project(self, tmp_path):
        # Ensure reports/ doesn't exist or is empty.
        with mock.patch("testgap.common.reports_dir", return_value=tmp_path):
            rc = main(["report"])
        assert rc == 1

    # -- clean --

    def test_clean_calls_clean_main(self, tmp_path):
        with mock.patch("testgap.cli._cmd_clean") as mock_cmd:
            mock_cmd.return_value = 0
            rc = main(["clean", "--project", str(tmp_path)])
        assert rc == 0

    def test_clean_returns_1_for_missing_project(self, tmp_path):
        rc = main(["clean", "--project", str(tmp_path / "nonexistent")])
        assert rc == 1

    # -- exit code propagation --

    def test_propagates_nonzero_exit_code(self, tmp_path):
        with mock.patch("testgap.cli._cmd_run") as mock_cmd:
            mock_cmd.return_value = 1
            rc = main(["run", "--project", str(tmp_path)])
        assert rc == 1

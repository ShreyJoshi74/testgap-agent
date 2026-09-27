"""Integration tests for testgap.find_gaps (Task 2.5)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest import mock

import pytest

from testgap.find_gaps import _collect_functions, _innermost_function, main

# Path to our shared fixtures
FIXTURES = Path(__file__).parent / "fixtures"
TINY_PROJECT = FIXTURES / "tiny_project"
COVERAGE_TINY = FIXTURES / "coverage_tiny.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_env(tmp_path: Path) -> tuple[Path, Path]:
    """Copy tiny_project and coverage_tiny.json into a tmp dir; return (project, rdir)."""
    project = tmp_path / "tiny_project"
    shutil.copytree(TINY_PROJECT, project)

    rdir = tmp_path / "reports"
    rdir.mkdir()
    shutil.copy(COVERAGE_TINY, rdir / "coverage_before.json")

    return project, rdir


def _run_main(project: Path, rdir: Path, label: str = "before") -> dict:
    """Run main() with mocked reports_dir and return the parsed gaps.json."""
    with mock.patch("testgap.find_gaps.reports_dir", return_value=rdir):
        rc = main(project, label=label, src="pkg")
    assert rc == 0
    gaps_path = rdir / "gaps.json"
    assert gaps_path.exists(), "gaps.json was not written"
    return json.loads(gaps_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# _collect_functions
# ---------------------------------------------------------------------------

class TestCollectFunctions:
    def test_finds_top_level_functions(self):
        source = "def foo(): pass\ndef bar(): pass\n"
        funcs = _collect_functions(source)
        names = [f.name for f in funcs]
        assert "foo" in names
        assert "bar" in names

    def test_finds_class_methods(self):
        source = "class A:\n    def m(self): pass\n"
        funcs = _collect_functions(source)
        names = [f.name for f in funcs]
        assert "A.m" in names

    def test_finds_nested_function(self):
        source = "def outer():\n    def inner(): pass\n"
        funcs = _collect_functions(source)
        names = [f.name for f in funcs]
        assert "outer" in names
        assert "outer.inner" in names

    def test_decorator_start_line(self):
        source = "def d(fn): return fn\n\n@d\ndef f(): pass\n"
        funcs = _collect_functions(source)
        f = next(fn for fn in funcs if fn.name == "f")
        # @d is on line 3
        assert f.start_line == 3

    def test_async_function(self):
        source = "async def fetch(): pass\n"
        funcs = _collect_functions(source)
        names = [f.name for f in funcs]
        assert "fetch" in names

    def test_invalid_syntax_returns_empty(self):
        assert _collect_functions("def (broken") == []


class TestInnermostFunction:
    def test_returns_none_for_module_level_line(self):
        source = "x = 1\ndef foo():\n    pass\n"
        funcs = _collect_functions(source)
        assert _innermost_function(1, funcs) is None

    def test_returns_innermost_for_nested(self):
        source = "def outer():\n    def inner():\n        return 1\n    return inner()\n"
        funcs = _collect_functions(source)
        # line 3 is inside both outer and inner → should return inner
        result = _innermost_function(3, funcs)
        assert result is not None
        assert result.name == "outer.inner"

    def test_returns_outer_for_non_nested_line(self):
        source = "def outer():\n    def inner():\n        return 1\n    return inner()\n"
        funcs = _collect_functions(source)
        # line 4 is in outer but not inner
        result = _innermost_function(4, funcs)
        assert result is not None
        assert result.name == "outer"


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

class TestFindGapsMain:
    def test_gaps_json_written(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        assert "gaps" in data

    def test_gap_count(self, tmp_path):
        """Should find gaps in calculate_total, _helper, decorated_func,
        MyClass.method_one, and MyClass.outer.inner — 5 total."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        assert len(data["gaps"]) == 5

    def test_top_gap_is_calculate_total(self, tmp_path):
        """calculate_total has score=18 (4 missing × 2 public + 10 in docs)."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        assert data["gaps"][0]["function"] == "calculate_total"

    def test_g001_is_highest_score(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        g001 = data["gaps"][0]
        assert g001["id"] == "G-001"
        assert all(g001["score"] >= g["score"] for g in data["gaps"])

    def test_class_method_naming(self, tmp_path):
        """Methods should be named ClassName.method."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        functions = [g["function"] for g in data["gaps"]]
        assert "MyClass.method_one" in functions

    def test_innermost_function_attribution(self, tmp_path):
        """Line 44 (inside inner()) must be attributed to MyClass.outer.inner."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        functions = [g["function"] for g in data["gaps"]]
        assert "MyClass.outer.inner" in functions
        # outer itself must NOT appear with line 44
        outer_gap = next((g for g in data["gaps"] if g["function"] == "MyClass.outer"), None)
        if outer_gap is not None:
            assert 44 not in outer_gap["missing_lines"]

    def test_decorator_line_attributed(self, tmp_path):
        """decorated_func starts at its decorator line (24)."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        dec_gap = next(
            (g for g in data["gaps"] if g["function"] == "decorated_func"), None
        )
        assert dec_gap is not None
        assert dec_gap["start_line"] == 24

    def test_unattributed_missing_lines(self, tmp_path):
        """Line 4 (MODULE_CONSTANT) is module-level → unattributed."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        assert data["unattributed_missing_lines"] >= 1

    def test_windows_backslash_normalised(self, tmp_path):
        """Coverage JSON uses backslash key — files should still be found."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        # All file paths in gaps.json should use forward slashes
        for gap in data["gaps"]:
            assert "\\" not in gap["file"]

    def test_scores_and_priorities(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        gap = data["gaps"][0]  # calculate_total
        # 4 missing × 2 (public) + 10 (in README) = 18 → medium
        assert gap["score"] == 18
        assert gap["priority"] == "medium"

    def test_private_helper_score(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        helper = next(g for g in data["gaps"] if g["function"] == "_helper")
        # 1 missing × 1 (private) + 0 = 1 → low
        assert helper["score"] == 1
        assert helper["priority"] == "low"

    def test_ids_are_sequential(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        for i, gap in enumerate(data["gaps"], start=1):
            assert gap["id"] == f"G-{i:03d}"

    def test_tie_break_order(self, tmp_path):
        """Among equal-score gaps, order must be file asc then start_line asc."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        gaps = data["gaps"]
        # Check every adjacent pair that has the same score
        for a, b in zip(gaps, gaps[1:]):
            if a["score"] != b["score"]:
                continue
            if a["file"] == b["file"]:
                assert a["start_line"] <= b["start_line"], (
                    f"{a['function']} start={a['start_line']} should come before "
                    f"{b['function']} start={b['start_line']}"
                )
            else:
                assert a["file"] <= b["file"]

    def test_gap_has_required_fields(self, tmp_path):
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        required = {"id", "file", "function", "start_line", "end_line",
                    "missing_lines", "score", "priority", "reason"}
        for gap in data["gaps"]:
            assert required.issubset(gap.keys()), (
                f"Gap {gap.get('id')} missing fields: {required - gap.keys()}"
            )

    def test_two_runs_give_identical_output(self, tmp_path):
        """Determinism: two runs must produce byte-identical gaps.json (NFR-04)."""
        project, rdir = _make_env(tmp_path)
        data1 = _run_main(project, rdir)

        # Re-copy coverage JSON (main doesn't modify it)
        shutil.copy(COVERAGE_TINY, rdir / "coverage_before.json")
        data2 = _run_main(project, rdir)

        assert data1 == data2

    def test_no_gaps_writes_empty_list(self, tmp_path):
        """When coverage JSON has no missing lines, gaps list is empty."""
        project = tmp_path / "tiny_project"
        shutil.copytree(TINY_PROJECT, project)
        rdir = tmp_path / "reports"
        rdir.mkdir()

        # Write a coverage JSON with no missing lines
        empty_cov = {
            "meta": {"version": "7.0.0"},
            "totals": {
                "covered_lines": 10,
                "missing_lines": 0,
                "num_statements": 10,
                "percent_covered": 100.0,
            },
            "files": {
                "pkg/tiny_module.py": {
                    "executed_lines": list(range(1, 11)),
                    "missing_lines": [],
                    "summary": {
                        "covered_lines": 10,
                        "missing_lines": 0,
                        "num_statements": 10,
                        "percent_covered": 100.0,
                    },
                }
            },
        }
        (rdir / "coverage_before.json").write_text(
            json.dumps(empty_cov), encoding="utf-8"
        )

        with mock.patch("testgap.find_gaps.reports_dir", return_value=rdir):
            rc = main(project, label="before", src="pkg")

        assert rc == 0
        data = json.loads((rdir / "gaps.json").read_text(encoding="utf-8"))
        assert data["gaps"] == []

    def test_missing_coverage_json_returns_1(self, tmp_path):
        project = tmp_path / "tiny_project"
        shutil.copytree(TINY_PROJECT, project)
        rdir = tmp_path / "reports"
        rdir.mkdir()
        # Don't write any coverage JSON

        with mock.patch("testgap.find_gaps.reports_dir", return_value=rdir):
            rc = main(project, label="before", src="pkg")

        assert rc == 1

    def test_output_metadata(self, tmp_path):
        """gaps.json top-level fields match Data Contract."""
        project, rdir = _make_env(tmp_path)
        data = _run_main(project, rdir)
        assert data["project"] == "tiny_project"
        assert data["src"] == "pkg"
        assert data["coverage_label"] == "before"
        assert isinstance(data["coverage_percent"], float)
        assert isinstance(data["unattributed_missing_lines"], int)

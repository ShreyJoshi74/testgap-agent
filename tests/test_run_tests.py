"""Unit tests for testgap.run_tests — uses tests/fixtures/junit_sample.xml."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from testgap.run_tests import parse_junit, parse_junit_empty, _classname_to_file, _is_generated

FIXTURE = Path(__file__).parent / "fixtures" / "junit_sample.xml"


# ---------------------------------------------------------------------------
# _classname_to_file
# ---------------------------------------------------------------------------

class TestClassnameToFile:
    def test_simple_module(self):
        assert _classname_to_file("tests.generated.test_orders", "") == \
               "tests/generated/test_orders.py"

    def test_strips_trailing_class(self):
        # "TestInsideClass" starts with uppercase → treated as class, not module
        assert _classname_to_file(
            "tests.fixtures._gen_junit.test_real_cases.TestInsideClass", "test_method_pass"
        ) == "tests/fixtures/_gen_junit/test_real_cases.py"

    def test_empty_classname_uses_name(self):
        # collection error: classname="" and name holds the dotted module path
        result = _classname_to_file(
            "", "tests.fixtures._gen_junit.tests.generated.test_broken_import"
        )
        assert result == "tests/fixtures/_gen_junit/tests/generated/test_broken_import.py"

    def test_no_class_suffix(self):
        assert _classname_to_file("tests.test_cli", "test_something") == \
               "tests/test_cli.py"


# ---------------------------------------------------------------------------
# _is_generated
# ---------------------------------------------------------------------------

class TestIsGenerated:
    def test_generated_path(self):
        assert _is_generated("tests/generated/test_orders.py") is True

    def test_plain_tests_path(self):
        assert _is_generated("tests/test_cli.py") is False

    def test_nested_generated(self):
        assert _is_generated("sample_project/tests/generated/test_foo.py") is True


# ---------------------------------------------------------------------------
# parse_junit — counts from the real fixture
# ---------------------------------------------------------------------------

class TestParseJunitCounts:
    """Verified against the actual pytest run that produced junit_sample.xml."""

    def setup_method(self):
        self.result = parse_junit(FIXTURE)

    # -- top-level totals --

    def test_total(self):
        # 10 test cases collected + 1 collection-error testcase = 11
        assert self.result["total"] == 11

    def test_passed(self):
        # test_plain_pass, TestInsideClass::test_method_pass, test_register_user_ok = 3
        assert self.result["passed"] == 3

    def test_failed(self):
        # test_plain_fail, test_plain_error, test_apply_discount_over_100_percent = 3
        assert self.result["failed"] == 3

    def test_errors(self):
        # test_broken_import collection error = 1
        assert self.result["errors"] == 1

    def test_xfailed(self):
        # test_plain_xfail, test_apply_discount_rejects_over_100 = 2
        assert self.result["xfailed"] == 2

    def test_skipped(self):
        # test_plain_skip, test_register_user_duplicate_email = 2
        assert self.result["skipped"] == 2

    # -- generated sub-block --

    def test_generated_total(self):
        # test_broken_import(error) + test_apply_discount×2 + test_register_user×2 = 5
        assert self.result["generated"]["total"] == 5

    def test_generated_passed(self):
        # only test_register_user_ok
        assert self.result["generated"]["passed"] == 1

    def test_generated_failed(self):
        # test_apply_discount_over_100_percent
        assert self.result["generated"]["failed"] == 1

    def test_generated_errors(self):
        # test_broken_import collection error
        assert self.result["generated"]["errors"] == 1

    def test_generated_xfailed(self):
        # test_apply_discount_rejects_over_100
        assert self.result["generated"]["xfailed"] == 1

    def test_generated_skipped(self):
        # test_register_user_duplicate_email
        assert self.result["generated"]["skipped"] == 1

    def test_pass_rate(self):
        # 1 passed out of 5 generated = 0.2
        assert self.result["generated"]["pass_rate"] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# parse_junit — failures list
# ---------------------------------------------------------------------------

class TestParseJunitFailures:
    def setup_method(self):
        self.result = parse_junit(FIXTURE)

    def test_failures_have_required_keys(self):
        for entry in self.result["failures"]:
            assert "test" in entry
            assert "file" in entry
            assert "kind" in entry
            assert "message" in entry

    def test_failures_count(self):
        # 3 failures + 1 error = 4 entries
        assert len(self.result["failures"]) == 4

    def test_generated_failure_present(self):
        tests = [e["test"] for e in self.result["failures"]]
        assert any("test_apply_discount_over_100_percent" in t for t in tests)

    def test_collection_error_kind(self):
        errors = [e for e in self.result["failures"] if e["kind"] == "error"]
        assert len(errors) == 1
        assert "test_broken_import" in errors[0]["file"]

    def test_failures_by_file_populated(self):
        fbf = self.result["failures_by_file"]
        assert isinstance(fbf, dict)
        assert len(fbf) > 0
        # All values are positive integers
        for v in fbf.values():
            assert isinstance(v, int) and v > 0


# ---------------------------------------------------------------------------
# parse_junit — xfails list
# ---------------------------------------------------------------------------

class TestParseJunitXfails:
    def setup_method(self):
        self.result = parse_junit(FIXTURE)

    def test_xfails_count(self):
        assert len(self.result["xfails"]) == 2

    def test_xfails_have_required_keys(self):
        for entry in self.result["xfails"]:
            assert "test" in entry
            assert "file" in entry
            assert "reason" in entry

    def test_xfail_reason_preserved(self):
        reasons = [e["reason"] for e in self.result["xfails"]]
        assert any("Possible bug" in r for r in reasons)

    def test_generated_xfail_present(self):
        files = [e["file"] for e in self.result["xfails"]]
        assert any("tests/generated" in f for f in files)


# ---------------------------------------------------------------------------
# parse_junit — skips list
# ---------------------------------------------------------------------------

class TestParseJunitSkips:
    def setup_method(self):
        self.result = parse_junit(FIXTURE)

    def test_skips_count(self):
        assert len(self.result["skips"]) == 2

    def test_skips_have_required_keys(self):
        for entry in self.result["skips"]:
            assert "test" in entry
            assert "file" in entry
            assert "reason" in entry

    def test_generated_skip_present(self):
        files = [e["file"] for e in self.result["skips"]]
        assert any("tests/generated" in f for f in files)


# ---------------------------------------------------------------------------
# parse_junit_empty
# ---------------------------------------------------------------------------

class TestParseJunitEmpty:
    def setup_method(self):
        self.result = parse_junit_empty()

    def test_all_zeros(self):
        for key in ("total", "passed", "failed", "errors", "xfailed", "skipped"):
            assert self.result[key] == 0

    def test_generated_all_zeros(self):
        g = self.result["generated"]
        for key in ("total", "passed", "failed", "errors", "xfailed", "skipped"):
            assert g[key] == 0

    def test_pass_rate_zero(self):
        assert self.result["generated"]["pass_rate"] == 0.0

    def test_lists_empty(self):
        assert self.result["failures"] == []
        assert self.result["xfails"] == []
        assert self.result["skips"] == []


# ---------------------------------------------------------------------------
# main() — wiring (no real subprocess)
# ---------------------------------------------------------------------------

class TestRunTestsMain:
    def test_writes_results_json(self, tmp_path):
        from testgap.run_tests import main

        with mock.patch("testgap.run_tests.check_deps"):
            with mock.patch("testgap.run_tests.run_pytest"):
                with mock.patch("testgap.run_tests.reports_dir", return_value=tmp_path):
                    # Copy fixture XML as the junit output
                    import shutil
                    shutil.copy(FIXTURE, tmp_path / "junit.xml")
                    with mock.patch("testgap.run_tests.update_metrics"):
                        rc = main(tmp_path)

        assert rc == 0
        assert (tmp_path / "results.json").exists()

    def test_returns_0_even_when_tests_fail(self, tmp_path):
        """Exit code 0 means the tool ran; Bob reads the JSON to decide next steps."""
        from testgap.run_tests import main
        import shutil

        with mock.patch("testgap.run_tests.check_deps"):
            with mock.patch("testgap.run_tests.run_pytest"):
                with mock.patch("testgap.run_tests.reports_dir", return_value=tmp_path):
                    shutil.copy(FIXTURE, tmp_path / "junit.xml")
                    with mock.patch("testgap.run_tests.update_metrics"):
                        rc = main(tmp_path)

        assert rc == 0

    def test_handles_missing_junit_xml(self, tmp_path):
        """When pytest collects nothing, junit.xml may not be written."""
        from testgap.run_tests import main

        with mock.patch("testgap.run_tests.check_deps"):
            with mock.patch("testgap.run_tests.run_pytest"):
                with mock.patch("testgap.run_tests.reports_dir", return_value=tmp_path):
                    with mock.patch("testgap.run_tests.update_metrics"):
                        rc = main(tmp_path)

        assert rc == 0
        data = __import__("json").loads((tmp_path / "results.json").read_text())
        assert data["total"] == 0

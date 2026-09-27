"""run_tests — run all tests and produce reports/results.json.

Public API
----------
    main(project) -> int
    parse_junit(xml_path) -> dict
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from testgap.common import (
    check_deps,
    reports_dir,
    run_pytest,
    save_json,
    to_posix,
    update_metrics,
)


# ---------------------------------------------------------------------------
# JUnit XML parser
# ---------------------------------------------------------------------------

def _classname_to_file(classname: str, test_name: str) -> str:
    """Derive a posix-style file path from a pytest classname attribute.

    pytest's xunit2 format stores the dotted module path (and optionally a
    class name) in ``classname``.  Examples::

        "tests.generated.test_orders"              → "tests/generated/test_orders.py"
        "tests.generated.test_orders.TestOrders"   → "tests/generated/test_orders.py"
        ""  (collection error)                     → derive from test_name instead

    For a collection error ``classname`` is empty and pytest puts the dotted
    module path in ``name``.
    """
    source = classname if classname.strip() else test_name

    # Strip a trailing class segment: if the last part starts with an
    # uppercase letter it is a class name, not a module name.
    parts = source.split(".")
    if len(parts) > 1 and parts[-1][:1].isupper():
        parts = parts[:-1]

    return "/".join(parts) + ".py"


def _is_generated(file_path: str) -> bool:
    """Return True when the file lives under ``tests/generated/``."""
    return "tests/generated/" in file_path


def parse_junit(xml_path: str | Path) -> dict:
    """Parse a pytest JUnit XML file and return the results dict.

    Handles:
    - passed (no child element, classname non-empty)
    - failed  (<failure> child)
    - errors  (<error> child, typically collection errors — classname is "")
    - xfailed (<skipped type="pytest.xfail"> child)
    - skipped (<skipped> child with any other type)

    Returns a dict matching the ``results.json`` Data Contract.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Support both <testsuites><testsuite>…</testsuite></testsuites>
    # and a bare <testsuite>…</testsuite> root.
    if root.tag == "testsuites":
        suites = list(root)
    else:
        suites = [root]

    totals: dict[str, int] = {
        "total": 0, "passed": 0, "failed": 0,
        "errors": 0, "xfailed": 0, "skipped": 0,
    }
    gen: dict[str, int] = {
        "total": 0, "passed": 0, "failed": 0,
        "errors": 0, "xfailed": 0, "skipped": 0,
    }
    failures: list[dict] = []
    failures_by_file: dict[str, int] = {}
    xfails: list[dict] = []
    skips: list[dict] = []

    for suite in suites:
        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            file_path = _classname_to_file(classname, name)

            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")

            is_gen = _is_generated(file_path)
            totals["total"] += 1
            if is_gen:
                gen["total"] += 1

            # Determine the full qualified test id
            if classname.strip():
                test_id = f"{file_path}::{name}"
            else:
                # collection error — no "::" separator makes sense
                test_id = name

            if error_el is not None:
                # Collection error: classname is "" and name holds the module path
                kind = "errors"
                msg = error_el.get("message", "")
                totals["errors"] += 1
                if is_gen:
                    gen["errors"] += 1
                failures.append({
                    "test": test_id,
                    "file": to_posix(file_path),
                    "kind": "error",
                    "message": msg,
                })
                failures_by_file[to_posix(file_path)] = (
                    failures_by_file.get(to_posix(file_path), 0) + 1
                )

            elif failure_el is not None:
                msg = failure_el.get("message", "")
                totals["failed"] += 1
                if is_gen:
                    gen["failed"] += 1
                failures.append({
                    "test": test_id,
                    "file": to_posix(file_path),
                    "kind": "failed",
                    "message": msg,
                })
                failures_by_file[to_posix(file_path)] = (
                    failures_by_file.get(to_posix(file_path), 0) + 1
                )

            elif skipped_el is not None:
                skip_type = skipped_el.get("type", "")
                msg = skipped_el.get("message", "")

                if skip_type == "pytest.xfail":
                    totals["xfailed"] += 1
                    if is_gen:
                        gen["xfailed"] += 1
                    xfails.append({
                        "test": test_id,
                        "file": to_posix(file_path),
                        "reason": msg,
                    })
                else:
                    totals["skipped"] += 1
                    if is_gen:
                        gen["skipped"] += 1
                    skips.append({
                        "test": test_id,
                        "file": to_posix(file_path),
                        "reason": msg,
                    })

            else:
                # Passed
                totals["passed"] += 1
                if is_gen:
                    gen["passed"] += 1

    # pass_rate = generated.passed / generated.total  (0 when no generated tests)
    pass_rate = round(gen["passed"] / gen["total"], 3) if gen["total"] > 0 else 0.0

    return {
        "total": totals["total"],
        "passed": totals["passed"],
        "failed": totals["failed"],
        "errors": totals["errors"],
        "xfailed": totals["xfailed"],
        "skipped": totals["skipped"],
        "generated": {
            "total": gen["total"],
            "passed": gen["passed"],
            "failed": gen["failed"],
            "errors": gen["errors"],
            "xfailed": gen["xfailed"],
            "skipped": gen["skipped"],
            "pass_rate": pass_rate,
        },
        "failures": failures,
        "failures_by_file": failures_by_file,
        "xfails": xfails,
        "skips": skips,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(project: str | Path) -> int:
    """Run all tests in *project* and write results.json / update metrics.json.

    Returns 0 always (test failures are not a tool error — Bob reads the JSON).
    """
    check_deps()

    project = Path(project).resolve()
    rdir = reports_dir()
    junit_path = rdir / "junit.xml"

    run_pytest(project, [f"--junitxml={junit_path}"])

    if not junit_path.exists():
        # pytest exit code 5 = no tests collected; write empty results.
        results = parse_junit_empty()
    else:
        results = parse_junit(junit_path)

    save_json(rdir / "results.json", results)

    g = results["generated"]
    update_metrics(
        generated_total=g["total"],
        generated_passed=g["passed"],
        pass_rate=g["pass_rate"],
        possible_bugs=g["xfailed"],
        could_not_fix=g["skipped"],
    )

    rate_pct = round(g["pass_rate"] * 100, 1)
    print(
        f"{results['passed']} passed, {results['failed']} failed, "
        f"{results['xfailed']} xfailed, {results['skipped']} skipped"
        f" — generated pass rate {rate_pct}%"
    )
    return 0


def parse_junit_empty() -> dict:
    """Return an all-zero results dict for the case where no tests were collected."""
    return {
        "total": 0, "passed": 0, "failed": 0,
        "errors": 0, "xfailed": 0, "skipped": 0,
        "generated": {
            "total": 0, "passed": 0, "failed": 0,
            "errors": 0, "xfailed": 0, "skipped": 0,
            "pass_rate": 0.0,
        },
        "failures": [],
        "failures_by_file": {},
        "xfails": [],
        "skips": [],
    }

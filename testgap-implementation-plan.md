# TestGap Agent: Implementation Plan

## Overview

**Goal:** Build TestGap Agent — a tool that automatically finds untested Python code, writes tests for it using IBM Bob 2.0, runs and fixes the tests, and produces a before/after coverage report.

**Approach:** Two parts work together:
- A `testgap` Python package (deterministic scripts: scan, gaps, run, report, clean, CLI)
- IBM Bob 2.0 in Agent mode following a playbook (reads docs, writes tests via subagents, fixes failures)

**Scope:** Python + pytest projects only. No web UI, no CI integration, no language other than Python.

**Key constraint:** The tool must never edit files outside `<project>/tests/generated/` and `reports/`. This is enforced by the playbook rules (and by a Bob mode restriction if Bob supports one — see Task 1.5) and verified at report time with `git status` over the whole repo.

**Source documents:** `01_project_overview.md`, `02_BRD_TRD.md`, `03_architecture.md` (moved to `docs/` in Task 1.1)

---

## How to work through this plan

- **One Bob task per milestone.** Build each milestone inside its own Bob task (BRD § A11). At the end of the milestone, screenshot the Bob session and save it as `bob_sessions/task<N>_<name>.png`. Do this *while building* — screenshots cannot be recreated honestly at the end.
- **Every team member** must contribute at least one screenshot (`01_project_overview.md § 9`).
- **"Must" requirements first.** If time runs short, drop "Should"/"Could" items (BR-07 to BR-10), never "Must" items.
- **Tests alongside code.** Each script in Milestone 2 ships with its unit tests (TRD § B9) in the same task.

### Owners and dates

Fill in once the open questions in `02_BRD_TRD.md § B12` (deadline, team size) are answered.

| Milestone | Owner | Target date | Depends on |
|---|---|---|---|
| 1 — Scaffold, config & Bob spike | TBD | TBD | — |
| 2 — Core scripts + unit tests | TBD | TBD | 1 |
| 3 — Sample project & baseline | TBD | TBD | 1, 2.3 (`scan`) |
| 4 — Bob playbook | TBD | TBD | 1.5, 2, 3 |
| 5 — End-to-end run & demo | TBD | TBD | 1–4 |

---

## Data Contracts

All scripts talk through JSON files in `reports/` at the **repo root**. These contracts are fixed first so the scripts, the playbook and the unit tests all agree. They extend the examples in `03_architecture.md § 6`.

**Pass rate (KPI "90%+ of new tests pass")** is defined as:

```
pass_rate = generated.passed / generated.total
```

where `generated.*` counts only tests under `<project>/tests/generated/`. `xfailed`, `skipped`, `failed` and `errors` all count as *not passing*. (Matches the architecture example: 48 passing of 52 added = 92%.)

**`gaps.json`**

```json
{
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
      "reason": "Public function, 9 untested lines, named in README"
    }
  ]
}
```

- `file` always uses `/` separators, relative to the project folder (coverage.py writes `\` on Windows).
- Methods are named `ClassName.method`.

**`results.json`**

```json
{
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
    "pass_rate": 0.923
  },
  "failures": [
    {
      "test": "tests/generated/test_orders.py::test_apply_discount_over_100_percent",
      "file": "tests/generated/test_orders.py",
      "kind": "failed",
      "message": "AssertionError: expected ValueError"
    }
  ],
  "failures_by_file": { "tests/generated/test_orders.py": 1 },
  "xfails": [
    {
      "test": "tests/generated/test_orders.py::test_apply_discount_rejects_over_100",
      "file": "tests/generated/test_orders.py",
      "reason": "Possible bug: README says max discount is 100%, code accepts 150%"
    }
  ],
  "skips": [
    {
      "test": "tests/generated/test_users.py::test_register_user_duplicate_email",
      "file": "tests/generated/test_users.py",
      "reason": "Could not fix automatically: depends on database state"
    }
  ]
}
```

**`metrics.json`**

```json
{
  "project": "sample_project",
  "src": "app",
  "started_at": "2026-10-02T10:00:05",
  "finished_at": "2026-10-02T10:09:41",
  "run_seconds": 576,
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
  "minutes_per_test": 10,
  "minutes_per_test_measured": true,
  "estimated_manual_hours": 8.7,
  "files_changed": [],
  "source_files_changed": 0
}
```

| Field | Written by |
|---|---|
| `project`, `src`, `started_at`, `dirty_before`, `coverage_before`, `tests_before`, `existing_tests_failing_before` | `scan --label before` (resets the file — a new run starts here) |
| `coverage_after`, `tests_after` | `scan --label after` |
| `generated_*`, `pass_rate`, `possible_bugs`, `could_not_fix` | `run` |
| `finished_at`, `run_seconds`, `minutes_per_test*`, `estimated_manual_hours`, `files_changed`, `source_files_changed` | `report` |

---

## Milestones and Sub-Tasks

---

### Milestone 1 — Project Scaffold, Config & Bob Spike

**Intent:** Lay down the repo structure, packaging and pytest configuration, and — before anything else is built on it — find out exactly how Bob 2.0 runs subagents.

**Expected Outcomes:**
- `pip install -e .` works and `python -m testgap --help` resolves without error
- All directories from `03_architecture.md § 7` exist; docs live in `docs/`
- `pytest` at the repo root only collects the tool's own tests
- `pytest` inside `sample_project/` can import `app.*`
- `playbook/BOB_NOTES.md` records how Bob subagents and parallel tasks actually work

---

#### Task 1.1 — Create folder structure and move docs

- **Status:** `[ ] pending`
- **Intent:** Create every directory listed in `03_architecture.md § 7` so subsequent tasks have known paths.
- **Steps:**
  1. Create `src/testgap/`
  2. Create `playbook/`
  3. Create `sample_project/app/`, `sample_project/docs/`, `sample_project/tests/generated/`
  4. Create `reports/` (output dir; add `.gitkeep`)
  5. Create `tests/` and `tests/fixtures/` (tests for the `testgap` tool itself)
  6. Create `bob_sessions/` (screenshots; add `.gitkeep`)
  7. Create `docs/` and `git mv` the three source documents into it.
- **Relevant context:** `03_architecture.md § 7` (folder tree)

---

#### Task 1.2 — Create `pyproject.toml` and `requirements.txt`

- **Status:** `[ ] pending`
- **Intent:** Make the `testgap` package installable with `pip install -e .` and define all dependencies in one place.
- **Steps:**
  1. Write `pyproject.toml`:
     - `[build-system]` using `setuptools>=61`.
     - `[project]` with `name = "testgap"`, `requires-python = ">=3.11"`, and `dependencies = ["pytest", "pytest-cov>=4", "coverage>=7", "Faker", "pytest-timeout"]`.
     - `[tool.setuptools.packages.find] where = ["src"]` (src layout).
     - *Optional:* `[project.scripts] testgap = "testgap.cli:main"` for a `testgap` shell command. `python -m testgap` needs no entry here — it works through `__main__.py`.
     - `[tool.pytest.ini_options] testpaths = ["tests"]` so a root-level `pytest` never collects `sample_project/`.
  2. Write `requirements.txt` listing the same packages (for users who don't install the package).
  3. Verify in a fresh venv: `pip install -r requirements.txt && pip install -e .` installs cleanly on Windows and one of macOS/Linux (NFR-02).
- **Relevant context:** `02_BRD_TRD.md § B1` (tech stack), `02_BRD_TRD.md § B10` (setup commands)

---

#### Task 1.3 — Create `src/testgap/__init__.py` and `src/testgap/__main__.py`

- **Status:** `[ ] pending`
- **Intent:** Make `python -m testgap` work as the entry point by wiring `__main__.py` to `cli.py`.
- **Steps:**
  1. Create `src/testgap/__init__.py` with `__version__`.
  2. Create `src/testgap/__main__.py` that calls `cli.main()` and exits with its return code.
- **Relevant context:** `03_architecture.md § 3` (component table), `02_BRD_TRD.md § B5` (CLI usage)

---

#### Task 1.4 — Sample project pytest config, generated-tests scaffolding, `.gitignore`

- **Status:** `[ ] pending`
- **Intent:** Make generated tests importable and deterministic, and stop test tooling from leaving files that would show up as "changed" in the FR-12 check.
- **Steps:**
  1. Create `sample_project/pytest.ini`:
     ```ini
     [pytest]
     testpaths = tests
     pythonpath = .
     ```
  2. Create `sample_project/tests/__init__.py` and `sample_project/tests/generated/__init__.py` (both packages, so test module names never clash).
  3. Create `sample_project/tests/generated/conftest.py` with a fixed Faker seed for the Faker pytest plugin's `faker` fixture (FR-07). This reseeds per test, so data is identical regardless of test order or which files run:
     ```python
     import pytest

     @pytest.fixture
     def faker_seed():
         return 1234
     ```
  4. Append to the project-specific section of `.gitignore`: `.coverage`, `.coverage.*`, `coverage.json`, `.pytest_cache/`, `htmlcov/`.
  5. Commit these files. `clean` (Task 2.6) must never delete `__init__.py` or `conftest.py` in `tests/generated/`.
- **Relevant context:** `02_BRD_TRD.md § FR-07, FR-12`, `03_architecture.md § 9` (no flaky tests)

---

#### Task 1.5 — Spike: how Bob 2.0 runs subagents (highest-risk unknown)

- **Status:** `[ ] pending`
- **Intent:** Answer `02_BRD_TRD.md § B12` question 4 *now*, because the whole demo depends on it.
- **Steps:**
  1. In Bob 2.0 docs and a throwaway Bob task, find out:
     - How the main agent starts a subagent, and what context it can pass (file contents, paths, instructions).
     - Whether subagents run in parallel, and the maximum number at once.
     - Whether the playbook can be saved as a custom mode or rules file.
     - Whether a mode can restrict file edits to a path pattern (e.g. only `tests/generated/`). If yes, FR-12 becomes enforced, not just requested.
  2. Try it: ask Bob to start 2 subagents that each write a one-line file in a scratch folder. Screenshot the parallel run.
  3. Record the answers and exact instructions in `playbook/BOB_NOTES.md`.
  4. **Fallback decision:** if parallel subagents are unavailable, run one subagent per file in sequence. BR-09 (parallel) is a "Should", so the demo still meets every "Must".
- **Acceptance check:** `BOB_NOTES.md` exists with a working recipe; a screenshot shows 2+ subagents.
- **Relevant context:** `02_BRD_TRD.md § B7, B12`, `03_architecture.md § 5`

---

### Milestone 2 — `testgap` Core Scripts (with unit tests)

**Intent:** Build the deterministic scripts and the CLI dispatcher. These produce the JSON artefacts in the Data Contracts section that Bob reads, and the final `report.md`. Each task includes its unit tests (TRD § B9). Keep the logic in small pure functions (`score_gap`, `priority_label`, `parse_junit`, `filter_changed_paths`, …) so they can be tested without running pytest or git.

---

#### Task 2.1 — `common.py` — shared helpers

- **Status:** `[ ] pending`
- **Intent:** Avoid duplicating path, subprocess and JSON logic across four scripts.
- **Steps:**
  1. Create `src/testgap/common.py` with:
     - `repo_root()` (via `git rev-parse --show-toplevel`, falling back to the current directory) and `reports_dir()` → `<repo_root>/reports`, created if missing. All paths passed to subprocesses are **absolute**.
     - `run_pytest(project, extra_args, timeout)` → runs `[sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--timeout=30", *extra_args]` with `cwd=project`. Using `sys.executable` guarantees the same venv on every OS (NFR-02). A whole-run subprocess timeout (default 600 s) stops a hung run (NFR-01).
     - `check_deps()` → uses `importlib.util.find_spec` for `pytest`, `pytest_cov`, `coverage`, `faker`, `pytest_timeout`; on failure prints `"<name> not installed. Run: pip install -r requirements.txt"` and exits 1 (NFR-06).
     - `load_json` / `save_json` (sorted keys, 2-space indent — deterministic output, NFR-04) and `update_metrics(**fields)`.
     - `to_posix(path)` for all paths written to JSON.
- **Relevant context:** `02_BRD_TRD.md § B4`

---

#### Task 2.2 — `cli.py` — command dispatcher

- **Status:** `[ ] pending`
- **Intent:** Provide `python -m testgap <scan|gaps|run|report|clean> [args]`.
- **Steps:**
  1. Create `src/testgap/cli.py` using `argparse` with five sub-commands:
     - `scan --project <path> --label <before|after> [--src <dir>]`
     - `gaps --project <path> [--label before]` (which coverage file to read; default `before`)
     - `run --project <path>`
     - `report [--project <path>] [--minutes-per-test <float>]` (project defaults to the `project` value in `metrics.json`)
     - `clean --project <path>`
  2. Each sub-command calls the matching module's `main(args)` and returns its exit code.
  3. Exit codes: `0` = command completed (even if tests failed — Bob reads the JSON), `1` = tool error (missing deps, bad path, pytest internal/usage error).
  4. `--src` auto-detection (in `scan`): if omitted, pick the single top-level folder in the project containing `__init__.py` that isn't `tests`; if there are zero or several, stop and ask for `--src`.
- **Relevant context:** `02_BRD_TRD.md § B5`

---

#### Task 2.3 — `run_tests.py` — test runner and JUnit parser

- **Status:** `[ ] pending`
- **Intent:** Run all tests (including generated ones) and produce `results.json` as defined in Data Contracts. Built before `scan.py` because `scan` reuses the parser to count tests.
- **Steps:**
  1. Create `src/testgap/run_tests.py`.
  2. Run `run_pytest(project, ["--junitxml=<abs reports/junit.xml>"])`.
  3. `parse_junit(xml_path) -> dict` using `xml.etree.ElementTree`. For each `<testcase>`:
     - no child → `passed`
     - `<failure>` → `failed`; else `<error>` → `errors`
     - `<skipped type="pytest.xfail">` → `xfailed` (the `message` attribute is the xfail reason)
     - any other `<skipped>` → `skipped` (the `message` is the skip reason)
     - pytest's default `xunit2` format has **no `file` attribute**; derive the file from `classname` (e.g. `tests.generated.test_orders[.TestClass]` → `tests/generated/test_orders.py`). For collection errors the module path may be in `name` instead — confirm against a real broken file and handle it.
  4. Split counts into `generated` (file under `tests/generated/`) and compute `pass_rate`.
  5. Build `failures[]`, `failures_by_file`, `xfails[]`, `skips[]`.
  6. Write `reports/results.json`; update `metrics.json` with `generated_total`, `generated_passed`, `pass_rate`, `possible_bugs` (= generated xfails), `could_not_fix` (= generated skips).
  7. Print a summary: `N passed, M failed, X xfailed, S skipped — generated pass rate P%`.
- **Unit tests (`tests/test_run_tests.py`):**
  1. `tests/fixtures/junit_sample.xml` — captured from a **real** pytest run (not hand-written) containing a pass, fail, error, xfail, skip, a test inside a class, and a collection error, some under `tests/generated/`.
  2. Assert all counts, the `generated` block, `pass_rate`, and that every `failures[]` / `xfails[]` / `skips[]` entry has `test`, `file` and `message`/`reason`.
- **Acceptance check (FR-08):** `results.json` lists failures with test name and message, and xfail/skip reasons.
- **Relevant context:** `02_BRD_TRD.md § FR-08, B9`, Data Contracts

---

#### Task 2.4 — `scan.py` — coverage scanner

- **Status:** `[ ] pending`
- **Intent:** Run pytest with coverage on the target project and save the results so Bob can read them.
- **Steps:**
  1. Create `src/testgap/scan.py`. Call `check_deps()` first.
  2. Resolve `src` (flag or auto-detect, see Task 2.2).
  3. If `--label before`: start a new `metrics.json` with `project`, `src`, `started_at`, and `dirty_before` = paths from `git status --porcelain --untracked-files=all` (so files already modified before the run are not blamed on the tool). Warn if `dirty_before` is non-empty.
  4. Run `run_pytest(project, ["--cov=<src>", "--cov-report=json:<abs reports/coverage_<label>.json>", "--junitxml=<abs reports/junit_<label>.xml>"])` with the environment variable `COVERAGE_FILE=<abs reports/.coverage>` so no `.coverage` file lands in the project.
  5. Handle pytest exit codes:
     - `0` → OK. `1` → some existing tests fail: print a warning, record the count in `existing_tests_failing_before` (only for `before`), **continue** (`03_architecture.md § 10`).
     - `5` → no tests collected: `tests_<label> = 0`; if no coverage file was written, treat coverage as 0%.
     - `2`, `3`, `4` → stop with pytest's stderr and exit 1.
  6. Read `totals.percent_covered` from the coverage JSON; count tests with `parse_junit()` from Task 2.3.
  7. Update `metrics.json` with `coverage_<label>` and `tests_<label>`.
  8. Print: `Coverage (<label>): 22.4% — 4 tests`.
- **Acceptance check (FR-01, FR-02):** `reports/coverage_before.json` exists with a total %; `metrics.json` is updated; `sample_project/` has no new untracked files after a scan.
- **Relevant context:** `02_BRD_TRD.md § FR-01, FR-02`, `03_architecture.md § 10`, Data Contracts

---

#### Task 2.5 — `find_gaps.py` — gap finder and ranker

- **Status:** `[ ] pending`
- **Intent:** Parse the coverage JSON, map missing lines to functions using `ast`, score them, and save `gaps.json`.
- **Steps:**
  1. Create `src/testgap/find_gaps.py`. Read `reports/coverage_<label>.json` (default label `before`).
  2. For each file with missing lines (convert keys to `/` separators; resolve against the project folder), parse the source with `ast` and collect every `FunctionDef` / `AsyncFunctionDef`, including methods (named `Class.method`) and nested functions.
     - A function's range starts at its **first decorator** line (coverage.py counts decorator lines) and ends at `end_lineno`.
     - Each missing line belongs to the **innermost** function containing it.
     - Missing lines outside any function (module level) are counted in `unattributed_missing_lines`, not ranked.
  3. Compute the score (`02_BRD_TRD.md § B6`):
     - `score = len(missing_lines) × (2 if public else 1) + (10 if mentioned_in_docs else 0)`
     - **Public** = name doesn't start with `_`, **or** is a dunder (`__init__`, `__eq__`, …).
     - **Mentioned in docs** = whole-word match (`\bname\b`) in `<project>/README.md` or any `<project>/docs/**/*.md`. For methods, match the method name. Whole-word matching stops short names like `get` or `total` from matching everything.
     - `priority`: `high` ≥ 20, `medium` 8–19, `low` < 8.
     - Build the `reason` text (e.g. "Public function, 9 untested lines, named in README").
  4. Sort by `score` desc, then `file` asc, then `start_line` asc (stable, deterministic — NFR-04).
  5. **After sorting**, assign IDs `G-001`, `G-002`, … so `G-001` is always the top gap.
  6. Write `reports/gaps.json` per Data Contracts.
  7. If there are no gaps: write `gaps.json` with an empty `gaps` list, print `"Coverage is already high — no gaps found."` and exit 0 (the playbook then skips to the report).
  8. Otherwise print: `N gaps found (H high, M medium, L low)` and the top 3.
- **Unit tests:**
  - `tests/test_priority_score.py` (pure functions `score_gap` and `priority_label`):
    1. Public, 9 missing, in README → 28, `high`.
    2. Private `_helper`, 3 missing, not in docs → 3, `low`.
    3. Public, 5 missing, in README → 20, `high` (boundary).
    4. Public, 4 missing, in README → 18, `medium` (boundary).
    5. Public, 4 missing, not in docs → 8, `medium` (boundary).
    6. Private, 7 missing, not in docs → 7, `low` (boundary).
    7. `__init__` counts as public.
    8. Whole-word match: `total` is **not** found in a README that only mentions `calculate_total`.
  - `tests/test_find_gaps.py`:
    1. `tests/fixtures/tiny_project/` with `pkg/tiny_module.py` (a public function, a private function, a decorated function, a class method, a nested function, and a module-level statement) and a `README.md` naming one function.
    2. `tests/fixtures/coverage_tiny.json` — a minimal coverage.py JSON for that one file with known missing lines (include one Windows-style `\` key to test normalisation).
    3. Assert gap count, `Class.method` naming, innermost-function attribution, decorator lines attributed, `unattributed_missing_lines`, scores, tie-break order and that `G-001` is the highest score.
- **Acceptance check (FR-03, FR-04):** Each gap has `id`, `file`, `function`, `start_line`, `end_line`, `missing_lines`, `score`, `priority`, `reason`; highest score is first; two runs give byte-identical output.
- **Relevant context:** `02_BRD_TRD.md § B6, B9`, Data Contracts

---

#### Task 2.6 — `clean.py` — reset between runs

- **Status:** `[ ] pending`
- **Intent:** Let the team rehearse the demo repeatedly and start the final run from a known state.
- **Steps:**
  1. Create `src/testgap/clean.py`.
  2. Delete `<project>/tests/generated/test_*.py` (keep `__init__.py` and `conftest.py`) and everything in `reports/` except `.gitkeep`.
  3. Never delete anything outside those two folders. Print each removed path.
- **Unit test:** `tests/test_clean.py` using `tmp_path` — asserts protected files and files outside the two folders survive.
- **Relevant context:** `02_BRD_TRD.md § A10` (rehearsal, backup run)

---

#### Task 2.7 — `report.py` — final report builder and change check

- **Status:** `[ ] pending`
- **Intent:** Combine all JSON artefacts into `reports/report.md` and prove no real code was modified.
- **Steps:**
  1. Create `src/testgap/report.py`. Read `metrics.json`, `results.json`, `gaps.json`; project defaults to `metrics.project`.
  2. **Change check (FR-12):**
     - Run `git status --porcelain --untracked-files=all` at the repo root (catches edited, staged **and new** files — `git diff` alone misses new files).
     - `filter_changed_paths(paths, allowed, dirty_before)` removes paths under `<project>/tests/generated/` and `reports/`, and paths already listed in `dirty_before`. Whatever remains is `files_changed`; `source_files_changed` = those under `<project>/<src>/`.
     - If git is not installed or this isn't a repo, show "Real code changed: could not check (git not available)" — never a silent 0.
  3. Time: `finished_at` = now; `run_seconds` = `finished_at − started_at`.
  4. Manual-time estimate (BR-10): `generated_total × minutes_per_test`. Use `--minutes-per-test` (the measured baseline from Task 3.5). If it isn't given, use 10 and label the line "assumed, not measured".
  5. Write `reports/report.md` (layout from `03_architecture.md § 6`):
     - Before/after table (coverage %, test count)
     - Tests added, with passed / possible bugs / could not fix / still failing
     - Generated pass rate
     - Tool run time
     - Estimated time by hand (+ the per-test minutes and whether it was measured)
     - Real code changed: `0 files` — or a **warning** listing each file with `git checkout -- <file>` to revert it (`03_architecture.md § 10`)
     - Warning if existing tests were failing before the run
     - **Possible bugs** section (from `results.xfails`, with reasons)
     - **Could not fix automatically** section (from `results.skips`, with reasons)
  6. Update `metrics.json` with the fields in the Data Contracts table. Print the report path.
- **Unit tests (`tests/test_report.py`):**
  1. `filter_changed_paths`: allowed folders removed, `dirty_before` removed, a new untracked file in `app/` reported, an edited `tests/test_basic.py` reported.
  2. Build a report from fixture JSONs and assert the key lines (coverage, pass rate, "0 files", possible bugs listed).
- **Acceptance check (FR-11, FR-12):** `report.md` renders on GitHub; shows "Real code changed: 0 files" on a clean run and a warning when a source file is touched.
- **Relevant context:** `02_BRD_TRD.md § FR-11, FR-12, BR-10`, `03_architecture.md § 6, 10`

---

### Milestone 3 — Sample Project & Baseline

**Intent:** Build the demo Python app TestGap Agent is shown on. It must start at low coverage (~20%) and be rich enough for Bob's subagents to produce 40+ meaningful tests.

---

#### Task 3.1 — Design and implement the sample project app

- **Status:** `[ ] pending`
- **Intent:** Create a realistic but small Python app covering orders, users, payments, inventory and utilities.
- **Steps:**
  1. Create `sample_project/app/__init__.py`.
  2. Create 5 source files: `orders.py`, `users.py`, `payments.py`, `inventory.py`, `utils.py`.
  3. Give each file 3–6 functions (15–30 in total — enough for 40+ tests at 2–3 tests each), with docstrings that state expected behaviour, edge cases and errors raised.
  4. Include at least one private helper (`_…`) and one class with methods so all scoring paths show up in `gaps.json`.
  5. Deliberately include **one** function whose behaviour disagrees with its docs (e.g. `apply_discount` accepts > 100% while the README says the max is 100%) to trigger the "Possible bug" xfail path.
  6. Keep functions pure (no network, no real clock, no global state) so generated tests are stable.
  7. **File and folder names must not contain** `token`, `secret`, `password`, `credential`, `apikey`, `api_key` or `api-key`, and there must be no `config.json` — the security `.gitignore` would silently exclude them and the judges' clone would break.
  8. Keep total source under ~300 lines so a demo run fits in the time limit.
- **Relevant context:** `02_BRD_TRD.md § A8`, `03_architecture.md § 8` (playbook rules)

---

#### Task 3.2 — Create sample project docs and README

- **Status:** `[ ] pending`
- **Intent:** Provide the README and docs Bob reads for document understanding, and that the priority scorer searches.
- **Steps:**
  1. Write `sample_project/README.md` describing what the app does and naming the key functions (e.g. `calculate_total`, `apply_discount`) — these names get the +10 score boost.
  2. Create `sample_project/docs/business_rules.md` stating the rules the code must follow (e.g. "a discount can never exceed 100%"), including the rule the buggy function breaks.
- **Relevant context:** `02_BRD_TRD.md § B6` (+10 if the name appears in README/docs)

---

#### Task 3.3 — Add minimal existing tests

- **Status:** `[ ] pending`
- **Intent:** Give the sample project its "before" state.
- **Steps:**
  1. Create `sample_project/tests/test_basic.py` with 2–4 simple tests covering only trivial functions.
  2. Run `python -m testgap scan --project sample_project --label before`.
  3. Tune `test_basic.py` until coverage is between 15% and 25%. Note: with `--cov=app`, modules that are never imported count as 0%, while `def` and import lines of imported modules count as covered.
- **Relevant context:** `01_project_overview.md § 5` (demo story), `02_BRD_TRD.md § A7`

---

#### Task 3.4 — Commit the baseline

- **Status:** `[ ] pending`
- **Intent:** The FR-12 change check compares against git, so the sample project must be committed before any run.
- **Steps:**
  1. Run `python -m testgap clean --project sample_project`.
  2. Commit `sample_project/` (code, docs, `pytest.ini`, `test_basic.py`, `tests/generated/__init__.py` and `conftest.py`).
  3. Confirm `git status` is clean.
- **Relevant context:** `02_BRD_TRD.md § FR-12`

---

#### Task 3.5 — Measure the manual-writing baseline

- **Status:** `[ ] pending`
- **Intent:** Produce the real "time by hand" number required by BRD § A7 instead of guessing.
- **Steps:**
  1. One team member writes 5 tests by hand for sample-project functions (with Faker data, same quality bar as the playbook rules) and times each one.
  2. Record the times and the average minutes per test in `docs/baseline_timing.md`.
  3. Write those tests in a scratch folder outside `sample_project/tests/` and delete them afterwards, so they don't change the baseline coverage.
  4. This average is the value passed to `report --minutes-per-test`.
- **Relevant context:** `02_BRD_TRD.md § A7`, `01_project_overview.md § 6`

---

### Milestone 4 — Bob Playbook

**Intent:** Write the instruction file Bob follows in Agent mode — the "brain" side of the split. It tells Bob exactly which CLI commands to run, how to hand gaps to subagents, and the rules for writing tests.

---

#### Task 4.1 — Write `playbook/TESTGAP_PLAYBOOK.md`

- **Status:** `[ ] pending`
- **Intent:** Turn the draft in `03_architecture.md § 8` into a complete, working playbook that uses the recipe from `playbook/BOB_NOTES.md`.
- **Steps:**
  1. Create `playbook/TESTGAP_PLAYBOOK.md` with these steps:
     0. `python -m testgap clean --project <PROJECT>`
     1. `python -m testgap scan --project <PROJECT> --label before`
     2. `python -m testgap gaps --project <PROJECT>` — if it reports no gaps, go straight to step 8.
     3. Read `reports/gaps.json`, `<PROJECT>/README.md` and `<PROJECT>/docs/`.
     4. Group gaps by source file. Start one subagent per file, max 3 at once (or the limit found in Task 1.5), using the exact method in `BOB_NOTES.md`. Give each subagent: the source file, its gaps, the related docs, the existing tests (for style), and the Rules below. Output file: `<PROJECT>/tests/generated/test_<module>.py`.
     5. When all subagents finish: `python -m testgap run --project <PROJECT>`.
     6. **Fix loop (FR-09):** read `failures_by_file` in `reports/results.json`. For each file with failures, fix the **test**, then re-run step 5. Keep a table of tries per file. A collection error counts as a try. After 3 tries, mark each test still failing `@pytest.mark.skip(reason="Could not fix automatically: <short why>")`.
     7. `python -m testgap scan --project <PROJECT> --label after`
     8. `python -m testgap report --minutes-per-test <N>` (N from `docs/baseline_timing.md`)
     9. Show `reports/report.md`.
  2. **Context to read before writing tests** section: source file, its gaps, README, docs, existing tests' style.
  3. **Rules for writing tests** section:
     - Only create or edit `test_*.py` files in `<PROJECT>/tests/generated/`. Never edit source code, `conftest.py`, `__init__.py`, `pytest.ini` or existing tests.
     - Import code as `from app.<module> import …`.
     - Use pytest. One idea per test. Name tests `test_<function>_<situation>`. Add a one-line comment saying what the test checks (NFR-03).
     - Use the `faker` fixture for test data (it is seeded in `conftest.py`). Do not call `Faker.seed()` or create `Faker()` instances at module level.
     - Test normal cases, edge cases (empty, zero, negative, very large) and error cases.
     - Every test must assert something meaningful about the result or the raised error — no `assert True` and no tests that only call a function.
     - Check what the docs say the code SHOULD do. If the code clearly disagrees with the docs, do NOT change the test to match the code: mark it `@pytest.mark.xfail(reason="Possible bug: <what the docs say vs what the code does>")`. Use xfail **only** for a documented rule — never to hide a test you couldn't fix.
     - No real time, network, file-system writes, sleeps or unseeded randomness.
     - Never put real secrets or real personal data in tests.
  4. Check that every CLI command matches `02_BRD_TRD.md § B5` and Task 2.2 exactly.
- **Relevant context:** `03_architecture.md § 8`, `02_BRD_TRD.md § B7, FR-05 to FR-10`

---

#### Task 4.2 — Install the playbook in Bob

- **Status:** `[ ] pending`
- **Intent:** Make "Run the TestGap playbook on sample_project" a single instruction.
- **Steps:**
  1. Following `BOB_NOTES.md`, save the playbook as a Bob custom mode or rules file (or document how to reference it in the instruction if Bob has neither).
  2. If Bob supports restricting edits by path, limit this mode to `<PROJECT>/tests/generated/` and `reports/`.
- **Relevant context:** `02_BRD_TRD.md § B7`

---

#### Task 4.3 — Sync the architecture doc

- **Status:** `[ ] pending`
- **Intent:** Keep `docs/03_architecture.md` true to what was built.
- **Steps:** Update it for the changes listed under "Changes from the architecture draft" below (data contracts, `common.py`, `clean`, Faker fixture, the `git status` check, the final playbook).

---

### Milestone 5 — End-to-End Validation & Demo

**Intent:** Rehearse the full workflow, capture a backup, do the final run from one instruction, and produce the hackathon deliverables.

---

#### Task 5.1 — Dry runs

- **Status:** `[ ] pending`
- **Intent:** Find and fix problems before the recorded run.
- **Steps:**
  1. Confirm `git status` is clean.
  2. Give Bob the single instruction: **"Run the TestGap playbook on sample_project."** Do not run any `testgap` command by hand — the playbook does all steps, including `clean` and both scans.
  3. Check the Definition of Done (below). Note the run time, pass rate and anything Bob got wrong.
  4. Fix the playbook, scripts or sample project, commit, and repeat until the DoD passes twice in a row.
- **Relevant context:** `02_BRD_TRD.md § B11`

---

#### Task 5.2 — Record a backup run

- **Status:** `[ ] pending`
- **Intent:** Mitigate "Bob run too slow for a live demo" (`02_BRD_TRD.md § A10`).
- **Steps:** Screen-record one complete successful run from the single instruction to `report.md`, and keep it next to the demo materials.

---

#### Task 5.3 — Final run and commit

- **Status:** `[ ] pending`
- **Intent:** Produce the numbers shown to judges.
- **Steps:**
  1. Clean `git status`, then the single instruction to Bob.
  2. Verify the Definition of Done. `git status` must list only paths under `sample_project/tests/generated/` and `reports/`.
  3. Commit the generated tests and `reports/` so judges can see the real output.
- **Acceptance check (B11):** All six Definition of Done items pass.
- **Relevant context:** `02_BRD_TRD.md § B11`

---

#### Task 5.4 — Update project README

- **Status:** `[ ] pending`
- **Intent:** Replace the hackathon template README with the project's own README.
- **Steps:**
  1. Rewrite `README.md` (root) to cover: problem, solution (the 5-step workflow, linking to `docs/`), how Bob is used (Agent mode, subagents, parallel tasks, document understanding — with the real recipe from `BOB_NOTES.md`), setup (`02_BRD_TRD.md § B10`), and how to run the demo.
  2. Add a "Before vs After" table with the real numbers from Task 5.3 and the measured baseline from Task 3.5.
  3. Keep the security checklist section.
- **Relevant context:** `01_project_overview.md`, `02_BRD_TRD.md § B11`

---

#### Task 5.5 — Record demo video

- **Status:** `[ ] pending`
- **Intent:** Produce the 3–5 minute demo video telling the before/after story.
- **Steps:**
  1. Script it: low coverage → one Bob instruction → subagents writing in parallel → a failing test being fixed → the "Possible bug" found → final report with numbers.
  2. Record the screen (live or from the Task 5.2 backup) with narration.
  3. Confirm the video is between 3 and 5 minutes.
- **Relevant context:** `01_project_overview.md § 5, 9`

---

#### Task 5.6 — Final submission checks

- **Status:** `[ ] pending`
- **Intent:** Make sure nothing blocks the submission.
- **Steps:**
  1. `bob_sessions/` has a screenshot for every milestone, from every team member, and at least one shows subagents running in parallel.
  2. `git check-ignore -v .env` prints a match.
  3. Scan the full git history for secrets (`git log -p` search for key patterns, or a scanner such as gitleaks) before setting the repo to Public.
- **Relevant context:** `02_BRD_TRD.md § B8`, `01_project_overview.md § 9`

---

## Definition of Done Checklist

Sourced from `02_BRD_TRD.md § B11`:

- [ ] One instruction to Bob runs all 5 steps end to end (no manual `testgap` commands)
- [ ] Coverage goes up by ≥ 40 percentage points on the sample project
- [ ] ≥ 90% of generated tests pass (`pass_rate` as defined in Data Contracts)
- [ ] Zero changes to real code (`report.md` shows "Real code changed: 0 files"; `git status` lists only `tests/generated/` and `reports/`)
- [ ] `reports/report.md` shows all the numbers
- [ ] README explains problem, solution, Bob usage and setup

KPI targets also checked on the final run (`02_BRD_TRD.md § A7`): 40+ tests added, run time under 15 minutes.

Hackathon deliverables (`01_project_overview.md § 9`):

- [ ] Video demo (3–5 min) with before/after numbers
- [ ] Problem & solution statement in README
- [ ] "How we used IBM Bob" write-up in README
- [ ] Code repo with a good README
- [ ] Repo set to Public (no secrets in history)
- [ ] `bob_sessions/` folder with PNG screenshots from every team member

---

## Data Flow Summary

```
clean               →  empties <project>/tests/generated/test_*.py and reports/

scan (before)       →  reports/coverage_before.json, reports/junit_before.xml
                        reports/metrics.json (new run: project, src, started_at,
                        dirty_before, coverage_before, tests_before)

find_gaps           →  reports/gaps.json
                        (ranked by score; Bob reads this)

[Bob subagents]     →  sample_project/tests/generated/test_*.py

run_tests           →  reports/junit.xml, reports/results.json
                        reports/metrics.json (generated counts, pass_rate)
                        (Bob reads failures_by_file; fix loop ≤ 3 tries per file)

scan (after)        →  reports/coverage_after.json, reports/junit_after.xml
                        reports/metrics.json (coverage_after, tests_after)

report              →  reports/report.md
                        reports/metrics.json (finished_at, run time, manual estimate,
                        files_changed from git status)
```

---

## Changes from the architecture draft

These refine `03_architecture.md`; Task 4.3 brings the doc in line.

| Area | Draft | This plan | Why |
|---|---|---|---|
| Modules | 4 scripts + `cli.py` | Adds `common.py` and `clean.py` | Shared subprocess/path logic; repeatable rehearsals |
| `results.json` | Counts + `failures[]` | Adds `skipped`, `generated` block, `failures_by_file`, `xfails[]`, `skips[]` | Report needs bug/skip reasons and the pass rate of *new* tests |
| `metrics.json` | Basic fields | Adds `src`, `dirty_before`, generated counts, `pass_rate`, manual estimate, `files_changed` | Every report number has a source |
| Change check | `git diff` on source | `git status --porcelain` on whole repo, allowlist + `dirty_before` | Catches new files and edits outside `app/` |
| Faker seed | `Faker.seed(1234)` per file | `faker_seed` fixture in `tests/generated/conftest.py` | Same data regardless of test order |
| `finished_at` | Set by `scan after` | Set by `report` | Run time covers the whole workflow |
| CLI | `report` has no args | `report [--project] [--minutes-per-test]`, `scan [--src]`, `clean` | Report needs the project path and measured baseline |
| Hung tests | Not handled | `pytest-timeout` + subprocess timeout | Protects the 15-minute limit |

---

## Security Reminders

- Helper scripts must never require API keys (NFR-05)
- Generated tests use Faker only — no real personal data (FR-07, B8)
- `.env` stays in `.gitignore`; verify with `git check-ignore -v .env` before every commit
- Review `git diff` before every commit; scan the full git history before making the repo public
- Don't name files with `token`, `secret`, `password` or `credential` — `.gitignore` silently excludes them
- `report.py` checks `git status` and lists any file changed outside the allowed folders; any non-zero count is a warning

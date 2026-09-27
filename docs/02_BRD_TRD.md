# TestGap Agent: BRD and TRD

This file has two parts:

- **Part A: BRD (Business Requirements Document)** explains *why* we are building this and *what* it must achieve.
- **Part B: TRD (Technical Requirements Document)** explains *how* it will work technically.

**Status:** Draft v1 · **Workflow:** Testing · **Language:** Python

---

# Part A: Business Requirements (BRD)

## A1. Background

Tests protect code from bugs. But in many projects, a large part of the code has no tests. Developers know tests matter, but writing them is slow, and it is hard to even know which code is untested.

This hackathon asks for a tool that makes one developer workflow faster using IBM Bob 2.0. We picked **testing**.

## A2. Problem statement

Developers spend hours finding untested code and writing tests by hand, including fake test data. Because it is slow, they often skip it. This leads to low coverage, more bugs reaching users, and fear of changing code.

## A3. Goals

| ID | Goal |
|---|---|
| G1 | Show clearly which code has no tests |
| G2 | Write working tests for that code automatically |
| G3 | Cut the time to add tests from hours to minutes |
| G4 | Prove the impact with real numbers |
| G5 | Never break or change the real code |

## A4. Users and stakeholders

| Who | What they want |
|---|---|
| Developer | Tests written for them, quickly |
| Team lead | Higher coverage without slowing the team |
| New team member | Readable tests that explain what the code does |
| Hackathon judges | A clear problem, a working prototype, measurable impact, strong use of Bob |

## A5. Scope

**In scope**
- Python projects that use pytest
- Measuring coverage before and after
- Finding and ranking untested functions
- Writing unit tests with realistic fake data
- Running tests and fixing broken generated tests
- Flagging possible bugs in the real code
- A before-vs-after report

**Out of scope (for now)**
- Flaky test detection
- Other languages (JavaScript, Java, etc.)
- A web dashboard
- Changing or fixing the real code
- Running in CI such as GitHub Actions (future idea)

## A6. Business requirements

Priority: **Must** = needed for the demo · **Should** = important · **Could** = nice to have

| ID | Requirement | Priority |
|---|---|---|
| BR-01 | The tool must show the coverage % before it starts | Must |
| BR-02 | The tool must list untested functions, most important first | Must |
| BR-03 | The tool must write new tests without a human typing them | Must |
| BR-04 | New tests must run, and most must pass | Must |
| BR-05 | The tool must show a before-vs-after report with numbers | Must |
| BR-06 | The tool must not change any real (non-test) code | Must |
| BR-07 | Tests should use realistic fake data | Should |
| BR-08 | The tool should flag possible bugs found by the tests | Should |
| BR-09 | Test writing should run in parallel to save time | Should |
| BR-10 | The report could estimate the hours saved | Could |

## A7. Success metrics (KPIs)

| KPI | Target | How we measure |
|---|---|---|
| Coverage increase | from ~20% to 70%+ | coverage.py before and after |
| Tests added | 40+ | Count in the report |
| Pass rate of new tests | 90%+ | pytest results |
| Time for one tool run | under 15 minutes | Timestamps in `metrics.json` |
| Time saved vs writing by hand | 80%+ less time | Baseline test (below) |
| Real code changed | 0 lines | `git diff` on the source folder |

**Baseline test (how we get the "by hand" number):** one team member writes 5 tests by hand for the sample project and times it. *Average time per test × number of tests the tool wrote* = estimated manual time.

## A8. Assumptions

- The target project is written in Python and runs with pytest.
- The project installs and runs on a normal laptop.
- IBM Bob 2.0 can run commands, read files and use subagents in Agent mode.
- The sample project has some docs (README or docstrings) that describe what the code should do.

## A9. Constraints

- Hackathon time is limited, so the scope must stay small.
- No API keys or passwords may ever be committed (risk of IBM Cloud account suspension).
- The repo must follow the hackathon template (`bob_sessions/`, `.env.example`, `.gitignore`, `.bobignore`).
- The demo video is only 3–5 minutes.

## A10. Risks and how we handle them

| Risk | Impact | What we do |
|---|---|---|
| Many generated tests fail | Weak demo | Run-and-fix loop (max 3 tries); start with a small, clean sample project |
| Tests are wrong but pass (they test the bug, not the correct behavior) | False confidence | Bob reads the docs first; possible bugs are flagged, not hidden |
| Tool changes real code by mistake | Breaks the project | Subagents may only write in `tests/generated/`; the report checks `git diff` |
| Bob run is too slow for a live demo | Demo runs over time | Keep the sample project small; pre-record a backup run |
| Secrets leak into the repo | Account suspended | `.env` in `.gitignore`, `.bobignore`, check `git diff` before every commit |
| Scope creep | Not finished in time | Finish the "Must" list first |

## A11. Timeline (phases)

Adjust these to your hackathon deadline.

| Phase | Work | Bob task |
|---|---|---|
| 1 | Set up repo and sample project, measure baseline coverage | Task 1: Planning |
| 2 | Scanner and gap finder scripts | Task 2: Scanner |
| 3 | Test-writing playbook with subagents | Task 3: Test writer |
| 4 | Run-and-fix loop | Task 4: Run and fix |
| 5 | Report and metrics | Task 5: Report |
| 6 | README, docs, screenshots, demo video | Task 6: Docs |

---

# Part B: Technical Requirements (TRD)

## B1. Tech stack

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Beginner-friendly, great testing tools |
| Test runner | pytest | The most common Python test tool |
| Coverage | coverage.py via pytest-cov | Gives a JSON list of tested and untested lines |
| Fake data | Faker | Realistic names, emails, dates, prices |
| Code parsing | Python `ast` (built in) | Maps untested lines to function names |
| Test results | pytest JUnit XML + `xml.etree` (built in) | Easy pass/fail per test |
| Command line | `argparse` (built in) | No extra install |
| AI | IBM Bob 2.0 | Agent mode, subagents, parallel tasks, document understanding |

## B2. System overview

Two parts work together:

- **Helper scripts (Python package `testgap`)** do the exact, repeatable work: measure coverage, find gaps, run tests, build the report. There is no AI inside them.
- **Bob** does the smart work: reads docs, writes tests, fixes broken tests, decides the next step. Bob follows a written playbook (`playbook/TESTGAP_PLAYBOOK.md`).

See `03_architecture.md` for diagrams.

## B3. Functional requirements

| ID | Requirement | Acceptance check |
|---|---|---|
| FR-01 | `scan` runs pytest with coverage on the target project and saves `reports/coverage_<label>.json` | File exists and contains the total % |
| FR-02 | `scan` records the test count and time in `reports/metrics.json` | Metrics file is updated |
| FR-03 | `gaps` reads the coverage JSON, finds functions with untested lines using `ast`, and saves `reports/gaps.json` | Each gap has file, function, lines and priority |
| FR-04 | `gaps` ranks gaps by priority score (see B6) | Highest score comes first |
| FR-05 | Bob groups gaps by source file and starts one subagent per file | Several subagents visible in Bob at once |
| FR-06 | Each subagent writes `tests/generated/test_<module>.py` | File exists and runs with pytest |
| FR-07 | Generated tests use Faker with a fixed seed | Same data on every run |
| FR-08 | `run` runs all tests and saves `reports/results.json` (pass/fail per test) | File lists failures with messages |
| FR-09 | Bob fixes failing generated tests, max 3 tries per file | Loop stops after 3 tries |
| FR-10 | If the code clearly disagrees with the docs, the test is marked `xfail` with reason "Possible bug: …" and listed in the report | Shown under "Possible bugs" |
| FR-11 | `report` builds `reports/report.md` with before/after coverage, tests added, pass rate, time and possible bugs | Report displays correctly on GitHub |
| FR-12 | The tool never edits files outside `tests/generated/` and `reports/`; `report` checks this with `git diff` | Report shows "Real code changed: 0 files" |

## B4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | A full run on a small project (30 files or fewer) finishes in under 15 minutes |
| NFR-02 | Works on Windows, macOS and Linux |
| NFR-03 | Generated tests are readable: clear names, one idea per test, a short comment |
| NFR-04 | Helper scripts give the same result every time for the same input |
| NFR-05 | Helper scripts need no secrets or API keys |
| NFR-06 | Clear error messages, e.g. "pytest not installed. Run: pip install -r requirements.txt" |

## B5. Command-line interface

```bash
# 1. Measure "before"
python -m testgap scan --project sample_project --label before

# 2. Find and rank the gaps
python -m testgap gaps --project sample_project

# 3. (Bob subagents write tests into sample_project/tests/generated/)

# 4. Run all tests
python -m testgap run --project sample_project

# 5. Measure "after"
python -m testgap scan --project sample_project --label after

# 6. Build the report
python -m testgap report
```

## B6. Data files

All output goes in `reports/`:

| File | Made by | Contents |
|---|---|---|
| `coverage_before.json` | scan | coverage.py JSON (tested and missing lines per file) |
| `coverage_after.json` | scan | Same, after the new tests |
| `gaps.json` | gaps | Ranked list of untested functions |
| `junit.xml` | run | Raw pytest results |
| `results.json` | run | Simple pass/fail list |
| `metrics.json` | scan, run, report | Coverage %, test counts, timestamps |
| `report.md` | report | Final human-readable report |

**Priority score for a gap:**

```
score = missing_lines × (2 if public function, else 1)
        + 10 if the function name appears in the README or docs

high: score ≥ 20   ·   medium: 8–19   ·   low: below 8
```

A *public function* is one whose name does not start with `_`.

## B7. How Bob is used (technical)

| Bob feature | Technical use |
|---|---|
| Agent mode | The main agent follows the playbook: runs CLI commands, reads the JSON output, decides the next step |
| Document understanding | Reads the README, docs folder and docstrings before tests are written |
| Subagents | One per source file. Input: that file's gaps, its source code and related docs |
| Parallel tasks | Subagents run at the same time (start with 3–4) |
| Tasks | Each build phase is a separate Bob task (for the `bob_sessions/` screenshots) |

> Check the Bob 2.0 docs for the exact way to start subagents and parallel tasks, and whether the playbook can be saved as a custom mode or rules file.

## B8. Security and secrets

- The helper scripts need no API keys.
- `.env` stays in `.gitignore`. Confirm with `git check-ignore -v .env`.
- `.bobignore` stops Bob from logging secrets.
- Check `git diff` before every commit, and scan the full commit history before making the repo public.
- Generated tests must never contain real personal data. Use Faker only.

## B9. Testing the tool itself

- Unit tests for `find_gaps.py` using a tiny fake coverage JSON file.
- Unit tests for the priority score.
- Unit tests for JUnit XML parsing in `run_tests.py`, using a saved sample file.
- One full end-to-end run on the sample project before the demo.

## B10. Setup

```bash
git clone <your-repo-url>
cd <your-repo>
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # pytest, pytest-cov, coverage, faker
pip install -e .                   # makes "python -m testgap" work
cp .env.example .env               # only if you add keys later
git check-ignore -v .env           # must print a match
```

## B11. Definition of done (for the demo)

- [ ] One instruction to Bob runs all 5 steps end to end
- [ ] Coverage goes up by at least 40 percentage points on the sample project
- [ ] 90% or more of the generated tests pass
- [ ] `git diff` shows zero changes to real code
- [ ] `reports/report.md` shows all the numbers
- [ ] README explains the problem, the solution, Bob usage and setup

## B12. Open questions

1. What is the hackathon deadline? (to fix the timeline)
2. How many team members? (to split the Bob tasks)
3. Which sample project? (our own small app, or a small open-source one)
4. What are the exact Bob 2.0 steps for subagents, parallel tasks and saving the playbook?

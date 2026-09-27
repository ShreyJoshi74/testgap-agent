# TestGap Playbook

**For IBM Bob 2.0 — Agent mode**

Goal: raise the test coverage of `<PROJECT>` without changing any real code.

Replace `<PROJECT>` with the project folder path (e.g. `sample_project`) in every command below.
`<SRC>` is the source package inside it; read it from the `src` field of `reports/gaps.json`
(for `sample_project` it is `app`).

**Run every command from the repository root.** All reports are written to `reports/` there.

**If a `testgap` command exits with code 1** (a tool error: missing package, bad path,
pytest usage error), stop the run and show the error to the user. Do not try to fix the
`testgap` tool or any file outside `<PROJECT>/tests/generated/`.

---

## Steps

### Step 0 — Clean

```bash
python -m testgap clean --project <PROJECT>
```

This removes any previously generated test files and report files so the run
starts from a clean state.

---

### Step 1 — Measure coverage before

```bash
python -m testgap scan --project <PROJECT> --label before
```

This runs pytest with coverage and saves `reports/coverage_before.json`.
It also records the test count and timing in `reports/metrics.json`.

If it warns that existing tests are failing, note it and **continue**. The report
shows the warning. Never edit existing tests to make them pass.

---

### Step 2 — Find the gaps

```bash
python -m testgap gaps --project <PROJECT>
```

This reads the coverage snapshot, finds untested functions using the AST,
ranks them by priority score, and saves `reports/gaps.json`.

**If `gaps.json` reports no gaps** (all functions are already covered), skip
directly to Step 8.

---

### Step 3 — Read the project

Read the following files before writing any tests:

- `reports/gaps.json` — the ranked list of untested functions
- `<PROJECT>/README.md` — high-level description and key function list
- Every file in `<PROJECT>/docs/` — detailed business rules

Understanding what the code is *supposed* to do is essential: if a test
disagrees with the docs, it is a possible bug — not a broken test.

---

### Step 4 — Write tests (parallel subagents)

Group the gaps by source file (the `file` field in `gaps.json`).

Start **one subagent per source file**, all in the same turn (they run in
parallel). Spawn at most 3–4 subagents at once. If more source files exist,
process them in batches of 3–4.

Use `spawn_subagent` with `name="general"`. Each subagent's `description`
must be fully self-contained (subagents start with no parent context). Include:

1. The full contents of the source file (paste inline, or give the path and
   tell the subagent to read it).
2. The rows from `gaps.json` for that file (function name, missing lines,
   priority score, reason).
3. The relevant section of `<PROJECT>/README.md` and `<PROJECT>/docs/`.
4. The existing tests in `<PROJECT>/tests/` outside `generated/` (e.g. `test_basic.py`),
   as the style to follow.
5. The **Rules for writing tests** section below (copy it verbatim).
6. The output path: `<PROJECT>/tests/generated/test_<module>.py`
   (replace `<module>` with the source file stem, e.g. `orders` → `test_orders.py`).
7. These instructions for the subagent itself:
   - Write **only** that one output file. Do not touch any other file, including other
     subagents' test files.
   - Do **not** run any `python -m testgap` command. The main agent runs those.
   - Aim to execute every line in each gap's `missing_lines`: usually 2–4 tests per
     function (normal case, edge cases, each error it raises).
   - A gap named `ClassName.method` is a method: create an instance of the class in
     the test and call the method on it.
   - Before finishing, self-check the file once from inside `<PROJECT>`:
     `python -m pytest tests/generated/test_<module>.py -q -p no:cacheprovider`.
     Fix mistakes in the **test** (typos, wrong imports, wrong expected values worked
     out from the docs). A failure where the code breaks a documented rule is not a
     mistake: mark it `xfail` as described in the rules.
   - When done, reply with the file path and the number of tests written.

**Example** (`sample_project`, first batch): three `spawn_subagent` calls in the same turn,
one each for `app/payments.py`, `app/inventory.py` and `app/users.py`. When all three finish,
a second batch covers `app/orders.py` and `app/utils.py`.

---

### Step 5 — Run all tests

When every subagent from Step 4 has finished:

```bash
python -m testgap run --project <PROJECT>
```

This runs all tests (existing + generated) and saves `reports/results.json`
with a pass/fail result for every test.

---

### Step 6 — Fix loop (FR-09)

Read `reports/results.json`. Look at `failures_by_file` (paths are relative to
`<PROJECT>`) and the matching entries in `failures` for each message.

Only fix files under `tests/generated/`. If an existing test fails, leave it alone:
it was already failing before the run.

Keep a table of tries per file (start each at 0). Then repeat this round:

1. For **every** generated file with failures, read the messages and fix the **test**
   (never the source code). Add 1 to that file's try counter.
2. Re-run Step 5 once for the whole round.
3. Stop when `failures_by_file` has no generated files, or every file left has used 3 tries.

**A collection error (syntax error, import error) also counts as one try.**

How to decide on each failure:

| The failure shows… | Do this |
|---|---|
| A mistake in the test (typo, wrong import, wrong fixture, wrong expected value) | Fix the test |
| The code breaks a rule written in README / docs | Mark `xfail` with a "Possible bug" reason (see the rules) |
| Still failing after 3 tries | Mark that test `skip` (below) |

Never "fix" a test by deleting it, removing its assertions, or changing the expected
value to whatever the code returns when the docs say otherwise.

After **3 tries**, for any test in that file that is still failing, add:

```python
@pytest.mark.skip(reason="Could not fix automatically: <short explanation>")
```

If the file still cannot even be collected after 3 tries, rewrite the broken part so
the file imports, and mark the affected tests `skip` the same way.

Continue to Step 7 once every generated test passes, is `xfail`, or is `skip`.

---

### Step 7 — Measure coverage after

```bash
python -m testgap scan --project <PROJECT> --label after
```

This saves `reports/coverage_after.json` and updates `reports/metrics.json`
with the final coverage percentage and test count.

---

### Step 8 — Build the report

Use the `--minutes-per-test` value from `docs/baseline_timing.md` (currently 27):

```bash
python -m testgap report --minutes-per-test 27
```

This reads all the JSON files in `reports/` and writes `reports/report.md`.

---

### Step 9 — Show the report

Read and display the full contents of `reports/report.md`, followed by the
fix-loop tries table from Step 6.

Do not commit anything. The user reviews and commits the results.

---

## Context to read before writing tests

Each subagent must read (or receive inline) before writing a single test:

| What | Where |
|---|---|
| Source file | `<PROJECT>/<SRC>/<module>.py` (e.g. `sample_project/app/orders.py`) |
| Gaps for this file | Rows from `reports/gaps.json` where `file` matches |
| Business rules | `<PROJECT>/README.md` + every file in `<PROJECT>/docs/` |
| Existing test style | Existing tests in `<PROJECT>/tests/` (not `generated/`) |

---

## Rules for writing tests

These rules apply to every test written by every subagent.

### Where to write

- **Only** create or edit `test_*.py` files in `<PROJECT>/tests/generated/`.
- Never edit source code, `conftest.py`, `__init__.py`, `pytest.ini`, or any
  existing test file outside `tests/generated/`.

### Imports

- Import code as `from <SRC>.<module> import …` (for `sample_project`: `from app.orders import …`).
- Use `import pytest` at the top of every file.

### Style

- Use pytest. **One idea per test.**
- Name each test `test_<function>_<situation>` (e.g.
  `test_calculate_tax_negative_rate_raises`).
- Add a one-line comment above each test stating what it checks (NFR-03):
  ```python
  # calculate_tax should raise ValueError for a negative rate (rule O5)
  def test_calculate_tax_negative_rate_raises():
      with pytest.raises(ValueError):
          calculate_tax(100.0, rate=-0.1)
  ```

### Test data

- Use the `faker` fixture for all realistic test data (names, emails, prices,
  etc.): add `faker` as a test argument, e.g. `def test_x(faker):`. The fixture
  comes from the pytest plugin built into the `Faker` package and is seeded via
  the `faker_seed` fixture in `tests/generated/conftest.py` (seed = 1234), so
  data is identical on every run.
- Fixed literal values are fine where the exact number matters (boundaries such
  as 14 vs 15 days, or 50.00 for free shipping).
- **Do not** call `Faker.seed()` anywhere.
- **Do not** create `Faker()` instances at module level.

### Coverage

- Cover normal cases, edge cases (empty, zero, negative, very large) and error
  cases (expected exceptions).
- Every test must assert something meaningful about the result or the raised
  error — no `assert True` and no tests that only call a function without
  checking anything.

### Possible bugs

- Check what the docs say the code *should* do.
- If the code clearly disagrees with the docs, do **not** change the test to
  match the code. Mark it:
  ```python
  @pytest.mark.xfail(reason="Possible bug: <what the docs say vs what the code does>")
  ```
- Use `xfail` **only** for a documented rule — never to hide a test you could
  not fix. `xfail` tests count as *not passing* in the pass rate, so each one must
  point at a real conflict between docs and code.
- Example (`sample_project`, rule O3 in `docs/business_rules.md`):
  ```python
  # apply_discount should reject a discount over 100% (rule O3)
  @pytest.mark.xfail(reason="Possible bug: docs say a discount over 100% must raise ValueError, code returns a negative price")
  def test_apply_discount_over_100_percent_raises():
      with pytest.raises(ValueError):
          apply_discount(100.0, 150)
  ```

### Prohibited patterns

- No real clock (`datetime.now()`, `time.time()`, etc.).
- No network calls.
- No file-system writes.
- No `time.sleep()`.
- No unseeded randomness (`random.random()`, etc.).
- Never put real secrets or real personal data in tests.

---

## Quick-reference command list

| Step | Command |
|---|---|
| 0 · Clean | `python -m testgap clean --project <PROJECT>` |
| 1 · Scan before | `python -m testgap scan --project <PROJECT> --label before` |
| 2 · Find gaps | `python -m testgap gaps --project <PROJECT>` |
| 5 · Run tests | `python -m testgap run --project <PROJECT>` |
| 7 · Scan after | `python -m testgap scan --project <PROJECT> --label after` |
| 8 · Report | `python -m testgap report --minutes-per-test 27` |

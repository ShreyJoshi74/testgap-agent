# Manual Test-Writing Baseline

Real "time by hand" number for the report (BRD § A7, plan Task 3.5).

## How it was measured

- One team member wrote 5 pytest tests by hand for `sample_project/app/` functions.
- Same quality bar as the playbook rules: Faker data, one idea per test, a meaningful assertion,
  normal / edge / error cases.
- Tests were written in a scratch folder **outside** `sample_project/tests/` and deleted
  afterwards, so the baseline coverage (21.5%) is unchanged.
- Each test was timed from reading the function to the test passing.

## Results

Measured by: _TBD_ · Date: _TBD_

| # | Function tested | Test name | Minutes |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

**Average minutes per test:** _TBD_

This average is the value passed to:

```bash
python -m testgap report --minutes-per-test <average>
```

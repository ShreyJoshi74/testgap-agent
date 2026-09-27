# TestGap Report: sample_project

|                    | Before | After |
|--------------------|--------|-------|
| Coverage           | 21.5%  | 100.0% |
| Tests              | 4      | 165    |

- Tests added: 161 (160 passing, 1 possible bugs, 0 could not be fixed, 0 still failing)
- Generated pass rate: 99.4%
- Tool run time: 5m 41s
- Estimated time by hand: 72.5 hours (161 tests × 27 min, from our baseline test)
- Real code changed: 0 files (checked with git)

## Possible bugs

1. `tests/generated/test_orders.py::test_apply_discount_over_100_raises` — Possible bug: docs say a discount over 100% must raise ValueError, code returns a negative price

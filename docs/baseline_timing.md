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

Measured by: Shrey · Date: 2026-09-27

| # | Function tested | Test name | Minutes |
|---|---|---|---|
| 1 | `orders.calculate_total` | `test_calculate_total_small_order_adds_shipping_and_tax` | 45 |
| 2 | `users.register_user` | `test_register_user_rejects_duplicate_email_case_insensitive` | 30 |
| 3 | `payments.split_bill` | `test_split_bill_shares_add_up_to_total` | 25 |
| 4 | `payments.refund_amount` | `test_refund_amount_half_refund_on_day_15` | 15 |
| 5 | `inventory.Inventory.remove_stock` | `test_inventory_remove_stock_over_available_raises_and_keeps_count` | 20 |

**Total:** 135 minutes for 5 tests

**Average minutes per test:** 27

This average is the value passed to:

```bash
python -m testgap report --minutes-per-test 27
```

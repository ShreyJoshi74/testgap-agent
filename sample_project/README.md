# ShopLite

ShopLite is a small online-shop backend. It is the demo project for TestGap Agent,
so it starts with very few tests.

All code lives in the `app/` package and is pure Python (no database, network or clock).

## Modules

| Module | What it does | Key functions |
|---|---|---|
| `app/orders.py` | Prices an order | `calculate_subtotal`, `apply_discount`, `shipping_cost`, `calculate_tax`, `calculate_total` |
| `app/users.py` | User accounts | `normalize_email`, `is_valid_email`, `validate_username`, `is_adult`, `register_user` |
| `app/payments.py` | Card payments and refunds | `luhn_check`, `mask_card`, `processing_fee`, `split_bill`, `refund_amount` |
| `app/inventory.py` | Stock per SKU | `Inventory` (`add_stock`, `remove_stock`, `count`, `low_stock`, `total_value`), `OutOfStockError` |
| `app/utils.py` | Shared helpers | `round_money`, `clamp`, `slugify`, `format_name` |

## How an order total is worked out

`calculate_total` does these steps in order:

1. `calculate_subtotal`: sum of price × quantity for every line.
2. `apply_discount`: take off a percentage discount. **The discount can be 0% to 100%, never more.**
3. `shipping_cost`: free at 50.00 or more, otherwise 5.99.
4. `calculate_tax`: 8% tax on the discounted amount (shipping is not taxed).

All money values are rounded half-up to cents with `round_money`.

The full rules are in [docs/business_rules.md](docs/business_rules.md).

## Running the tests

```bash
cd sample_project
python -m pytest
```

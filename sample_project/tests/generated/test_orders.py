import pytest

from app.orders import (
    _validate_line,
    apply_discount,
    calculate_subtotal,
    calculate_tax,
    calculate_total,
    shipping_cost,
)


# ---------------------------------------------------------------------------
# _validate_line (G-024)
# ---------------------------------------------------------------------------

# _validate_line should accept a valid line with positive price and quantity (rule O1)
def test_validate_line_valid():
    _validate_line({"price": 9.99, "quantity": 2})  # must not raise


# _validate_line should accept a zero price (rule O1: price >= 0)
def test_validate_line_zero_price_valid():
    _validate_line({"price": 0.0, "quantity": 1})  # must not raise


# _validate_line should raise ValueError for a negative price (rule O1)
def test_validate_line_negative_price_raises():
    with pytest.raises(ValueError, match="price"):
        _validate_line({"price": -1.0, "quantity": 1})


# _validate_line should raise ValueError when quantity is zero (rule O1)
def test_validate_line_zero_quantity_raises():
    with pytest.raises(ValueError, match="quantity"):
        _validate_line({"price": 5.0, "quantity": 0})


# _validate_line should raise ValueError when quantity is a float (rule O1)
def test_validate_line_float_quantity_raises():
    with pytest.raises(ValueError, match="quantity"):
        _validate_line({"price": 5.0, "quantity": 1.5})


# _validate_line should raise ValueError when quantity is negative (rule O1)
def test_validate_line_negative_quantity_raises():
    with pytest.raises(ValueError, match="quantity"):
        _validate_line({"price": 5.0, "quantity": -3})


# ---------------------------------------------------------------------------
# calculate_subtotal (G-008)
# ---------------------------------------------------------------------------

# calculate_subtotal should return 0.0 for an empty list of lines (rule O2)
def test_calculate_subtotal_empty_order():
    assert calculate_subtotal([]) == 0.0


# calculate_subtotal should return price x quantity for a single line (rule O1)
def test_calculate_subtotal_single_line():
    assert calculate_subtotal([{"price": 10.0, "quantity": 3}]) == 30.0


# calculate_subtotal should sum all lines correctly (rule O1)
def test_calculate_subtotal_multiple_lines():
    lines = [
        {"price": 5.0, "quantity": 2},   # 10.00
        {"price": 3.50, "quantity": 4},  # 14.00
    ]
    assert calculate_subtotal(lines) == 24.0


# calculate_subtotal should apply half-up rounding to the result (rule M1)
def test_calculate_subtotal_rounding():
    # 1.005 * 1 = 1.005 -> rounds half-up to 1.01
    assert calculate_subtotal([{"price": 1.005, "quantity": 1}]) == 1.01


# calculate_subtotal should raise ValueError when a line has a negative price (rule O1)
def test_calculate_subtotal_negative_price_raises():
    with pytest.raises(ValueError, match="price"):
        calculate_subtotal([{"price": -5.0, "quantity": 1}])


# calculate_subtotal should raise ValueError when a line has an invalid quantity (rule O1)
def test_calculate_subtotal_invalid_quantity_raises():
    with pytest.raises(ValueError, match="quantity"):
        calculate_subtotal([{"price": 5.0, "quantity": 0}])


# ---------------------------------------------------------------------------
# apply_discount (G-012)
# ---------------------------------------------------------------------------

# apply_discount should return original amount when discount is 0% (rule O3)
def test_apply_discount_zero_percent():
    assert apply_discount(100.0, 0) == 100.0


# apply_discount should return 0.00 when discount is exactly 100% (rule O3)
def test_apply_discount_full_discount():
    assert apply_discount(100.0, 100) == 0.0


# apply_discount should correctly reduce the amount by the given percent (rule O3)
def test_apply_discount_twenty_percent():
    assert apply_discount(100.0, 20) == 80.0


# apply_discount should round the result to 2 decimal places (rule M1)
def test_apply_discount_rounding():
    # 10.00 * (1 - 33/100) = 10.00 * 0.67 = 6.70
    assert apply_discount(10.0, 33) == 6.70


# apply_discount should raise ValueError for a negative discount percent (rule O3)
def test_apply_discount_negative_percent_raises():
    with pytest.raises(ValueError, match="negative"):
        apply_discount(100.0, -1)


# A discount over 100% is invalid per docs but the code does not reject it (rule O3)
@pytest.mark.xfail(
    reason="Possible bug: docs say a discount over 100% must raise ValueError, code returns a negative price"
)
def test_apply_discount_over_100_raises():
    with pytest.raises(ValueError):
        apply_discount(100.0, 101)


# ---------------------------------------------------------------------------
# shipping_cost (G-020)
# ---------------------------------------------------------------------------

# shipping_cost should return 0.0 for an empty order (subtotal == 0) (rule O4)
def test_shipping_cost_zero_subtotal():
    assert shipping_cost(0.0) == 0.0


# shipping_cost should return 0.0 exactly at the free-shipping threshold (rule O4)
def test_shipping_cost_at_threshold():
    assert shipping_cost(50.0) == 0.0


# shipping_cost should return 0.0 for a subtotal above the threshold (rule O4)
def test_shipping_cost_above_threshold():
    assert shipping_cost(99.99) == 0.0


# shipping_cost should return FLAT_SHIPPING (5.99) just below the threshold (rule O4)
def test_shipping_cost_just_below_threshold():
    assert shipping_cost(49.99) == 5.99


# shipping_cost should return FLAT_SHIPPING for a small order (rule O4)
def test_shipping_cost_small_order():
    assert shipping_cost(10.0) == 5.99


# ---------------------------------------------------------------------------
# calculate_tax (G-013)
# ---------------------------------------------------------------------------

# calculate_tax should return 8% of the amount at default rate (rule O5)
def test_calculate_tax_default_rate():
    assert calculate_tax(100.0) == 8.0


# calculate_tax should return 0.0 when the amount is 0 (rule O5)
def test_calculate_tax_zero_amount():
    assert calculate_tax(0.0) == 0.0


# calculate_tax should use a custom rate when provided (rule O5)
def test_calculate_tax_custom_rate():
    assert calculate_tax(200.0, rate=0.10) == 20.0


# calculate_tax should round the result to 2 decimal places (rule M1)
def test_calculate_tax_rounding():
    # 1.005 * 0.08 = 0.0804 -> rounds to 0.08
    assert calculate_tax(1.005, rate=0.08) == 0.08


# calculate_tax should raise ValueError for a negative rate (rule O5)
def test_calculate_tax_negative_rate_raises():
    with pytest.raises(ValueError, match="negative"):
        calculate_tax(100.0, rate=-0.01)


# ---------------------------------------------------------------------------
# calculate_total (G-010)
# ---------------------------------------------------------------------------

# calculate_total on an empty order should return 0.00 (rules O2, O4, O6)
def test_calculate_total_empty_order():
    assert calculate_total([]) == 0.0


# calculate_total should pay flat shipping when discounted subtotal < 50 (rules O4, O6)
def test_calculate_total_with_shipping():
    # subtotal=40.0, discounted=40.0, shipping=5.99, tax=3.20 -> 49.19
    lines = [{"price": 20.0, "quantity": 2}]
    assert calculate_total(lines) == 49.19


# calculate_total should ship free when discounted subtotal >= 50 (rules O4, O6)
def test_calculate_total_free_shipping():
    # subtotal=60.0, discounted=60.0, shipping=0.0, tax=4.80 -> 64.80
    lines = [{"price": 30.0, "quantity": 2}]
    assert calculate_total(lines) == 64.80


# calculate_total should apply discount before computing shipping and tax (rules O3, O5, O6)
def test_calculate_total_with_discount():
    # subtotal=30.0, discounted=15.0, shipping=5.99, tax=1.20 -> 22.19
    lines = [{"price": 10.0, "quantity": 3}]
    assert calculate_total(lines, discount_percent=50) == 22.19


# calculate_total should raise ValueError when a line is invalid (rule O1)
def test_calculate_total_invalid_line_raises():
    with pytest.raises(ValueError):
        calculate_total([{"price": -1.0, "quantity": 1}])


# calculate_total: discount that pushes subtotal below 50 triggers shipping (rules O3, O4, O6)
def test_calculate_total_discount_triggers_shipping():
    # subtotal=100.0, 60% off -> discounted=40.0, shipping=5.99, tax=3.20 -> 49.19
    lines = [{"price": 100.0, "quantity": 1}]
    assert calculate_total(lines, discount_percent=60) == 49.19

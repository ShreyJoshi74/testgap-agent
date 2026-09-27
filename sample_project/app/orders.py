"""Order pricing: subtotals, discounts, shipping, tax and totals."""

from app.utils import round_money

TAX_RATE = 0.08
FREE_SHIPPING_THRESHOLD = 50.0
FLAT_SHIPPING = 5.99


def _validate_line(line):
    """Check one order line has a non-negative price and a positive integer quantity.

    Raises ValueError on a bad line.
    """
    if line["price"] < 0:
        raise ValueError("price must not be negative")
    qty = line["quantity"]
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError("quantity must be a positive integer")


def calculate_subtotal(lines):
    """Return the sum of price x quantity for every line, rounded to cents.

    Each line is a dict with "price" and "quantity". An empty order gives 0.0.
    Raises ValueError if any line is invalid.
    """
    total = 0.0
    for line in lines:
        _validate_line(line)
        total += line["price"] * line["quantity"]
    return round_money(total)


def apply_discount(amount, percent):
    """Apply a percentage discount to an amount.

    percent must be between 0 and 100 inclusive (see docs/business_rules.md);
    anything outside that range raises ValueError. Result is rounded to cents.
    """
    if percent < 0:
        raise ValueError("discount percent must not be negative")
    return round_money(amount * (1 - percent / 100))


def shipping_cost(subtotal):
    """Return the shipping cost for an order subtotal.

    Orders of FREE_SHIPPING_THRESHOLD (50.00) or more ship free; smaller
    orders pay FLAT_SHIPPING (5.99). An empty order (0.00) ships free.
    """
    if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    return FLAT_SHIPPING


def calculate_tax(amount, rate=TAX_RATE):
    """Return tax on amount at the given rate, rounded to cents.

    Raises ValueError if rate is negative.
    """
    if rate < 0:
        raise ValueError("tax rate must not be negative")
    return round_money(amount * rate)


def calculate_total(lines, discount_percent=0):
    """Return the final order total.

    Steps: subtotal -> apply discount -> add shipping (based on the
    discounted amount) -> add tax on the discounted amount (shipping is not
    taxed). Rounded to cents.
    """
    subtotal = calculate_subtotal(lines)
    discounted = apply_discount(subtotal, discount_percent)
    tax = calculate_tax(discounted)
    return round_money(discounted + shipping_cost(discounted) + tax)

"""Payments: card checks, fees, splitting bills and refunds."""

from app.utils import round_money

CARD_FEE_PERCENT = 2.9
CARD_FEE_FIXED = 0.30


def luhn_check(number):
    """Return True if a digit string passes the Luhn checksum.

    Spaces and hyphens are ignored. Returns False for empty input or any
    other non-digit character.
    """
    digits = number.replace(" ", "").replace("-", "")
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def mask_card(number):
    """Hide all but the last 4 digits: "4111111111111111" -> "************1111".

    Spaces and hyphens are removed first. Raises ValueError if fewer than
    4 digits remain.
    """
    digits = number.replace(" ", "").replace("-", "")
    if len(digits) < 4:
        raise ValueError("card number too short")
    return "*" * (len(digits) - 4) + digits[-4:]


def processing_fee(amount):
    """Return the card fee for amount: 2.9% + 0.30, rounded to cents.

    A zero amount has no fee. Raises ValueError for a negative amount.
    """
    if amount < 0:
        raise ValueError("amount must not be negative")
    if amount == 0:
        return 0.0
    return round_money(amount * CARD_FEE_PERCENT / 100 + CARD_FEE_FIXED)


def split_bill(amount, people):
    """Split amount into `people` shares that add up exactly to amount.

    Shares are in cents; any leftover cents go to the first shares, so
    split_bill(10.00, 3) -> [3.34, 3.33, 3.33].
    Raises ValueError if people is less than 1 or amount is negative.
    """
    if people < 1:
        raise ValueError("people must be at least 1")
    if amount < 0:
        raise ValueError("amount must not be negative")
    cents = int(round_money(amount) * 100 + 0.5)
    base, extra = divmod(cents, people)
    return [(base + (1 if i < extra else 0)) / 100 for i in range(people)]


def refund_amount(paid, days_since_purchase):
    """Return how much to refund for a purchase.

    Full refund within 14 days (0-14), 50% refund within 30 days (15-30),
    nothing after that. Raises ValueError for a negative day count.
    """
    if days_since_purchase < 0:
        raise ValueError("days must not be negative")
    if days_since_purchase <= 14:
        return round_money(paid)
    if days_since_purchase <= 30:
        return round_money(paid / 2)
    return 0.0

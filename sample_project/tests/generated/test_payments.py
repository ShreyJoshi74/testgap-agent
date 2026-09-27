import pytest

from app.payments import luhn_check, mask_card, processing_fee, refund_amount, split_bill


# ---------------------------------------------------------------------------
# luhn_check (G-001)
# ---------------------------------------------------------------------------

# luhn_check should return True for a well-known valid Visa test number (rule P1)
def test_luhn_check_valid_card():
    assert luhn_check("4111111111111111") is True


# luhn_check should accept spaces and hyphens as separators (rule P1)
def test_luhn_check_valid_card_with_spaces():
    assert luhn_check("4111 1111 1111 1111") is True


# luhn_check should accept hyphen-separated card numbers (rule P1)
def test_luhn_check_valid_card_with_hyphens():
    assert luhn_check("4111-1111-1111-1111") is True


# luhn_check should return False for a number that fails the checksum (rule P1)
def test_luhn_check_invalid_card():
    assert luhn_check("1234567890123456") is False


# luhn_check should return False for an empty string (rule P1)
def test_luhn_check_empty_string():
    assert luhn_check("") is False


# luhn_check should return False when non-digit characters are present (rule P1)
def test_luhn_check_non_digit_characters():
    assert luhn_check("411111111111111X") is False


# luhn_check should return True for a single valid digit (0 passes the checksum)
def test_luhn_check_single_zero():
    assert luhn_check("0") is True


# luhn_check should handle a doubled digit causing carry reduction (d > 9 path)
def test_luhn_check_carry_reduction():
    # 4532015112830366 is a known valid card exercising d -= 9 branch
    assert luhn_check("4532015112830366") is True


# ---------------------------------------------------------------------------
# mask_card (G-009)
# ---------------------------------------------------------------------------

# mask_card should replace all but last 4 digits with asterisks (rule P2)
def test_mask_card_standard_number():
    assert mask_card("4111111111111111") == "************1111"


# mask_card should strip spaces before masking (rule P2)
def test_mask_card_strips_spaces():
    assert mask_card("4111 1111 1111 1111") == "************1111"


# mask_card should strip hyphens before masking (rule P2)
def test_mask_card_strips_hyphens():
    assert mask_card("4111-1111-1111-1111") == "************1111"


# mask_card with exactly 4 digits should produce no asterisks (rule P2)
def test_mask_card_exactly_four_digits():
    assert mask_card("1234") == "1234"


# mask_card should raise ValueError when fewer than 4 digits remain (rule P2)
def test_mask_card_too_short_raises():
    with pytest.raises(ValueError, match="too short"):
        mask_card("123")


# mask_card should raise ValueError for an empty string (rule P2)
def test_mask_card_empty_raises():
    with pytest.raises(ValueError):
        mask_card("")


# ---------------------------------------------------------------------------
# processing_fee (G-007)
# ---------------------------------------------------------------------------

# processing_fee should return 0.0 for a zero amount (rule P3)
def test_processing_fee_zero_amount():
    assert processing_fee(0) == 0.0
    assert processing_fee(0.0) == 0.0


# processing_fee should calculate 2.9% + 0.30 rounded to cents (rule P3)
def test_processing_fee_ten_dollars():
    # 10.00 * 2.9% + 0.30 = 0.29 + 0.30 = 0.59
    assert processing_fee(10.00) == 0.59


# processing_fee should work correctly for a larger amount (rule P3)
def test_processing_fee_hundred_dollars():
    # 100.00 * 2.9% + 0.30 = 2.90 + 0.30 = 3.20
    assert processing_fee(100.00) == 3.20


# processing_fee should raise ValueError for a negative amount (rule P3)
def test_processing_fee_negative_raises():
    with pytest.raises(ValueError, match="negative"):
        processing_fee(-1.00)


# processing_fee should apply rounding to 2 decimal places (rule M1)
def test_processing_fee_rounding():
    # 1.00 * 2.9% + 0.30 = 0.029 + 0.30 = 0.329 -> rounds to 0.33
    assert processing_fee(1.00) == 0.33


# ---------------------------------------------------------------------------
# split_bill (G-004)
# ---------------------------------------------------------------------------

# split_bill should split evenly when the amount divides exactly (rule P4)
def test_split_bill_even_split():
    result = split_bill(9.00, 3)
    assert result == [3.0, 3.0, 3.0]


# split_bill should distribute leftover cents to first shares (rule P4)
def test_split_bill_leftover_cents():
    # 10.00 / 3 -> [3.34, 3.33, 3.33] as documented
    result = split_bill(10.00, 3)
    assert result == [3.34, 3.33, 3.33]


# split_bill shares must add up exactly to the original amount (rule P4)
def test_split_bill_sum_equals_total():
    result = split_bill(10.00, 3)
    assert round(sum(result), 2) == 10.00


# split_bill with a single person should return the full amount (rule P4)
def test_split_bill_one_person():
    result = split_bill(7.50, 1)
    assert result == [7.50]


# split_bill with zero amount should return all zeros (rule P4)
def test_split_bill_zero_amount():
    result = split_bill(0.0, 3)
    assert result == [0.0, 0.0, 0.0]


# split_bill should raise ValueError when people is 0 (rule P4)
def test_split_bill_zero_people_raises():
    with pytest.raises(ValueError, match="at least 1"):
        split_bill(10.00, 0)


# split_bill should raise ValueError when people is negative (rule P4)
def test_split_bill_negative_people_raises():
    with pytest.raises(ValueError, match="at least 1"):
        split_bill(10.00, -1)


# split_bill should raise ValueError for a negative amount (rule P4)
def test_split_bill_negative_amount_raises():
    with pytest.raises(ValueError, match="negative"):
        split_bill(-5.00, 2)


# ---------------------------------------------------------------------------
# refund_amount (G-005)
# ---------------------------------------------------------------------------

# refund_amount should return full refund on day 0 (rule P5)
def test_refund_amount_day_zero():
    assert refund_amount(100.00, 0) == 100.00


# refund_amount should return full refund on day 14 (boundary, rule P5)
def test_refund_amount_day_14_full_refund():
    assert refund_amount(50.00, 14) == 50.00


# refund_amount should return 50% refund on day 15 (boundary, rule P5)
def test_refund_amount_day_15_half_refund():
    assert refund_amount(50.00, 15) == 25.00


# refund_amount should return 50% refund on day 30 (boundary, rule P5)
def test_refund_amount_day_30_half_refund():
    assert refund_amount(80.00, 30) == 40.00


# refund_amount should return 0.0 after day 30 (rule P5)
def test_refund_amount_day_31_no_refund():
    assert refund_amount(100.00, 31) == 0.0


# refund_amount should return 0.0 for a very large day count (rule P5)
def test_refund_amount_large_day_count():
    assert refund_amount(200.00, 365) == 0.0


# refund_amount should raise ValueError for a negative day count (rule P5)
def test_refund_amount_negative_days_raises():
    with pytest.raises(ValueError, match="negative"):
        refund_amount(100.00, -1)


# refund_amount 50% result should be rounded half-up to 2 decimal places (rule M1)
def test_refund_amount_half_rounding():
    # paid=10.01, half=5.005, should round to 5.01 per half-up rule
    assert refund_amount(10.01, 15) == 5.01

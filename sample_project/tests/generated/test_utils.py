"""Tests for sample_project/app/utils.py — covering G-011, G-016, G-022, G-025."""

import pytest

from app.utils import _collapse_spaces, clamp, format_name, round_money


# ---------------------------------------------------------------------------
# round_money  (G-016 — lines 11,12,13)
# ---------------------------------------------------------------------------

# Positive half-up rounding: 2.675 rounds to 2.68 (rule M1)
def test_round_money_positive_half_up():
    assert round_money(2.675) == 2.68


# 1.005 should round up to 1.01 (rule M1)
def test_round_money_one_point_005():
    assert round_money(1.005) == 1.01


# Negative amounts preserve their sign and round half-up in magnitude (rule M2)
def test_round_money_negative_half_up():
    assert round_money(-1.005) == -1.01


# Zero remains zero
def test_round_money_zero():
    assert round_money(0) == 0.0


# An already-rounded value is unchanged
def test_round_money_already_rounded():
    assert round_money(3.50) == 3.50


# A large positive amount rounds correctly
def test_round_money_large_positive():
    assert round_money(1234567.895) == 1234567.90


# A large negative amount rounds correctly
def test_round_money_large_negative():
    assert round_money(-9999.995) == -10000.00


# ---------------------------------------------------------------------------
# clamp  (G-022 — line 22)
# ---------------------------------------------------------------------------

# Value inside the range is returned unchanged
def test_clamp_value_inside_range():
    assert clamp(5, 0, 10) == 5


# Value below low is clamped to low
def test_clamp_value_below_low():
    assert clamp(-5, 0, 10) == 0


# Value above high is clamped to high
def test_clamp_value_above_high():
    assert clamp(15, 0, 10) == 10


# Value equal to low boundary is returned unchanged
def test_clamp_value_at_low_boundary():
    assert clamp(0, 0, 10) == 0


# Value equal to high boundary is returned unchanged
def test_clamp_value_at_high_boundary():
    assert clamp(10, 0, 10) == 10


# low > high raises ValueError
def test_clamp_invalid_range_raises():
    with pytest.raises(ValueError, match="low must not be greater than high"):
        clamp(5, 10, 0)


# low == high is a valid single-point range
def test_clamp_low_equals_high():
    assert clamp(7, 5, 5) == 5


# ---------------------------------------------------------------------------
# _collapse_spaces  (G-025 — line 39)
# ---------------------------------------------------------------------------

# Multiple interior spaces are collapsed to one
def test_collapse_spaces_internal_spaces():
    assert _collapse_spaces("hello   world") == "hello world"


# Leading and trailing whitespace is stripped
def test_collapse_spaces_strips_ends():
    assert _collapse_spaces("  hello  ") == "hello"


# Mixed tabs and spaces are treated as whitespace
def test_collapse_spaces_tabs_and_spaces():
    assert _collapse_spaces("\t hello \t world \t") == "hello world"


# An empty string stays empty
def test_collapse_spaces_empty_string():
    assert _collapse_spaces("") == ""


# A string that is only whitespace returns empty string
def test_collapse_spaces_only_whitespace():
    assert _collapse_spaces("   ") == ""


# A string with no extra spaces is returned unchanged
def test_collapse_spaces_no_change_needed():
    assert _collapse_spaces("hello world") == "hello world"


# ---------------------------------------------------------------------------
# format_name  (G-011 — lines 47,48,49,50)
# ---------------------------------------------------------------------------

# Normal first + last are title-cased (rule U6)
def test_format_name_title_cases_both_parts(faker):
    assert format_name("ada", "lovelace") == "Ada Lovelace"


# Extra interior spaces are collapsed
def test_format_name_collapses_interior_spaces():
    assert format_name("  ada  ", "  lovelace  ") == "Ada Lovelace"


# Only first name provided, empty last
def test_format_name_last_empty():
    assert format_name("Ada", "") == "Ada"


# Only last name provided, empty first
def test_format_name_first_empty():
    assert format_name("", "Lovelace") == "Lovelace"


# Both parts whitespace-only raises ValueError
def test_format_name_both_empty_raises():
    with pytest.raises(ValueError, match="name must not be empty"):
        format_name("", "")


# Both parts pure-whitespace also raises ValueError
def test_format_name_whitespace_only_raises():
    with pytest.raises(ValueError, match="name must not be empty"):
        format_name("   ", "   ")


# Already title-cased input is handled correctly
def test_format_name_already_title_cased():
    assert format_name("Ada", "Lovelace") == "Ada Lovelace"


# faker-generated first/last names are title-cased in the output (rule U6)
def test_format_name_faker_names_are_title_cased(faker):
    first = faker.first_name().lower()
    last = faker.last_name().lower()
    result = format_name(first, last)
    assert result == result.title()

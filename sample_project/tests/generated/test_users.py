"""Tests for sample_project/app/users.py — covering G-003, G-014, G-015, G-021."""

import pytest

from app.users import (
    is_adult,
    is_valid_email,
    normalize_email,
    register_user,
    validate_username,
)


# ---------------------------------------------------------------------------
# is_valid_email  (G-021 — line 21)
# ---------------------------------------------------------------------------

# A well-formed address should be accepted
def test_is_valid_email_valid(faker):
    assert is_valid_email(faker.email()) is True


# Plain name@domain.tld should be accepted
def test_is_valid_email_simple():
    assert is_valid_email("user@example.com") is True


# Surrounding whitespace is stripped before matching (rule U1)
def test_is_valid_email_ignores_surrounding_spaces():
    assert is_valid_email("  user@example.com  ") is True


# Upper-case letters are folded to lower-case before matching (rule U1)
def test_is_valid_email_case_insensitive():
    assert is_valid_email("User@Example.COM") is True


# A string with no "@" is not a valid e-mail
def test_is_valid_email_missing_at():
    assert is_valid_email("notanemail") is False


# A string with no domain extension is not a valid e-mail
def test_is_valid_email_no_tld():
    assert is_valid_email("user@nodot") is False


# An empty string is not a valid e-mail
def test_is_valid_email_empty_string():
    assert is_valid_email("") is False


# ---------------------------------------------------------------------------
# validate_username  (G-014 — lines 29-31)
# ---------------------------------------------------------------------------

# A valid lower-case-alphanumeric username is returned unchanged
def test_validate_username_valid():
    assert validate_username("ada_99") == "ada_99"


# Minimum length of 3 characters is accepted (rule U4)
def test_validate_username_min_length():
    assert validate_username("abc") == "abc"


# Maximum length of 20 characters is accepted (rule U4)
def test_validate_username_max_length():
    assert validate_username("a" * 20) == "a" * 20


# A username that is too short (< 3 chars) raises ValueError
def test_validate_username_too_short():
    with pytest.raises(ValueError, match="3-20"):
        validate_username("ab")


# A username that is too long (> 20 chars) raises ValueError
def test_validate_username_too_long():
    with pytest.raises(ValueError, match="3-20"):
        validate_username("a" * 21)


# Upper-case letters are not allowed — raises ValueError
def test_validate_username_uppercase_rejected():
    with pytest.raises(ValueError):
        validate_username("Ada_99")


# A username with spaces raises ValueError
def test_validate_username_spaces_rejected():
    with pytest.raises(ValueError):
        validate_username("ada lovelace")


# An empty string raises ValueError
def test_validate_username_empty():
    with pytest.raises(ValueError):
        validate_username("")


# ---------------------------------------------------------------------------
# is_adult  (G-015 — lines 39-41)
# ---------------------------------------------------------------------------

# Exactly 18 is considered an adult (rule U5)
def test_is_adult_exactly_18():
    assert is_adult(18) is True


# 19 is an adult
def test_is_adult_above_18():
    assert is_adult(19) is True


# 17 is not an adult (rule U5)
def test_is_adult_below_18():
    assert is_adult(17) is False


# Age 0 is valid (a newborn) and not an adult
def test_is_adult_zero():
    assert is_adult(0) is False


# A large age is still an adult
def test_is_adult_large_age():
    assert is_adult(100) is True


# A negative age raises ValueError (rule U5)
def test_is_adult_negative_raises():
    with pytest.raises(ValueError, match="negative"):
        is_adult(-1)


# ---------------------------------------------------------------------------
# register_user  (G-003 — lines 53-61)
# ---------------------------------------------------------------------------

# A valid registration returns the expected dict structure
def test_register_user_valid(faker):
    result = register_user(
        existing_emails=[],
        email="ada@example.com",
        username="ada_99",
        first="Ada",
        last="Lovelace",
        age=30,
    )
    assert result["email"] == "ada@example.com"
    assert result["username"] == "ada_99"
    assert result["active"] is True


# The returned name is title-cased (rule U6)
def test_register_user_name_is_title_cased():
    result = register_user(
        existing_emails=[],
        email="ada@example.com",
        username="ada_99",
        first="ada",
        last="lovelace",
        age=30,
    )
    assert result["name"] == "Ada Lovelace"


# The returned e-mail is normalised (stripped and lower-cased)
def test_register_user_email_is_normalised():
    result = register_user(
        existing_emails=[],
        email="  ADA@Example.COM  ",
        username="ada_99",
        first="Ada",
        last="Lovelace",
        age=30,
    )
    assert result["email"] == "ada@example.com"


# A new user is always active (rule U6)
def test_register_user_active_flag_true():
    result = register_user(
        existing_emails=[],
        email="ada@example.com",
        username="ada_99",
        first="Ada",
        last="Lovelace",
        age=18,
    )
    assert result["active"] is True


# An invalid e-mail format raises ValueError
def test_register_user_invalid_email_raises():
    with pytest.raises(ValueError, match="invalid email"):
        register_user(
            existing_emails=[],
            email="not-an-email",
            username="ada_99",
            first="Ada",
            last="Lovelace",
            age=30,
        )


# A duplicate e-mail raises ValueError (rule U3)
def test_register_user_duplicate_email_raises():
    with pytest.raises(ValueError, match="already registered"):
        register_user(
            existing_emails=["ada@example.com"],
            email="ada@example.com",
            username="ada_99",
            first="Ada",
            last="Lovelace",
            age=30,
        )


# Duplicate check is case-insensitive (rule U1/U3)
def test_register_user_duplicate_email_case_insensitive_raises():
    with pytest.raises(ValueError, match="already registered"):
        register_user(
            existing_emails=["ADA@EXAMPLE.COM"],
            email="ada@example.com",
            username="ada_99",
            first="Ada",
            last="Lovelace",
            age=30,
        )


# An invalid username raises ValueError
def test_register_user_invalid_username_raises():
    with pytest.raises(ValueError):
        register_user(
            existing_emails=[],
            email="ada@example.com",
            username="ab",          # too short
            first="Ada",
            last="Lovelace",
            age=30,
        )


# A user who is under 18 raises ValueError (rule U5)
def test_register_user_underage_raises():
    with pytest.raises(ValueError, match="18"):
        register_user(
            existing_emails=[],
            email="ada@example.com",
            username="ada_99",
            first="Ada",
            last="Lovelace",
            age=17,
        )


# A user who is exactly 18 is accepted (boundary — rule U5)
def test_register_user_exactly_18_accepted():
    result = register_user(
        existing_emails=[],
        email="ada@example.com",
        username="ada_99",
        first="Ada",
        last="Lovelace",
        age=18,
    )
    assert result["active"] is True


# existing_emails is not mutated by the function
def test_register_user_does_not_modify_existing_emails():
    existing = ["other@example.com"]
    register_user(
        existing_emails=existing,
        email="ada@example.com",
        username="ada_99",
        first="Ada",
        last="Lovelace",
        age=30,
    )
    assert existing == ["other@example.com"]

"""General helpers shared by the rest of the app."""

import re


def round_money(amount):
    """Round an amount to 2 decimal places using half-up rounding.

    Examples: 2.675 -> 2.68, 1.005 -> 1.01, -1.005 -> -1.01.
    """
    sign = -1 if amount < 0 else 1
    cents = int(abs(amount) * 100 + 0.5 + 1e-9)
    return sign * cents / 100


def clamp(value, low, high):
    """Return value limited to the range [low, high].

    Raises ValueError if low is greater than high.
    """
    if low > high:
        raise ValueError("low must not be greater than high")
    return max(low, min(value, high))


def slugify(text):
    """Turn text into a URL-safe slug.

    Lower-cases the text, replaces every run of non-alphanumeric characters
    with a single hyphen and strips leading/trailing hyphens.
    "Hello, World!" -> "hello-world". Empty or symbol-only text gives "".
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


def _collapse_spaces(text):
    """Replace runs of whitespace with one space and trim both ends."""
    return " ".join(text.split())


def format_name(first, last):
    """Return "First Last" with each part title-cased and extra spaces removed.

    Raises ValueError if both parts are empty after trimming.
    """
    full = _collapse_spaces(f"{first} {last}")
    if not full:
        raise ValueError("name must not be empty")
    return full.title()

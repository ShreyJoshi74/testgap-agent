"""User accounts: e-mail checks, usernames and registration."""

import re

from app.utils import format_name

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")


def normalize_email(email):
    """Trim whitespace and lower-case an e-mail address."""
    return email.strip().lower()


def is_valid_email(email):
    """Return True if email looks like name@domain.tld, else False.

    The address is normalised first, so surrounding spaces and case are ignored.
    """
    return bool(EMAIL_RE.match(normalize_email(email)))


def validate_username(username):
    """Return the username if it is 3-20 chars of lower-case letters, digits or "_".

    Raises ValueError otherwise.
    """
    if not USERNAME_RE.match(username):
        raise ValueError("username must be 3-20 chars: a-z, 0-9 or _")
    return username


def is_adult(age):
    """Return True if age is 18 or more.

    Raises ValueError for a negative age.
    """
    if age < 0:
        raise ValueError("age must not be negative")
    return age >= 18


def register_user(existing_emails, email, username, first, last, age):
    """Create a new user record.

    Rules: the e-mail must be valid and not already used (case-insensitive),
    the username must pass validate_username, and the user must be an adult.
    Raises ValueError on any broken rule. Returns a dict with keys
    "email" (normalised), "username", "name" and "active" (True).
    Does not modify existing_emails.
    """
    email = normalize_email(email)
    if not is_valid_email(email):
        raise ValueError("invalid email")
    if email in {normalize_email(e) for e in existing_emails}:
        raise ValueError("email already registered")
    validate_username(username)
    if not is_adult(age):
        raise ValueError("user must be 18 or older")
    return {
        "email": email,
        "username": username,
        "name": format_name(first, last),
        "active": True,
    }

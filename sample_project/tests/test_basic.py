from app.orders import shipping_cost
from app.users import normalize_email
from app.utils import clamp, slugify


def test_slugify_simple_text():
    assert slugify("Hello, World!") == "hello-world"


def test_clamp_value_inside_range():
    assert clamp(5, 0, 10) == 5


def test_shipping_free_for_large_order():
    assert shipping_cost(80.0) == 0.0


def test_normalize_email_lowercases():
    assert normalize_email("  Ada@Example.COM ") == "ada@example.com"

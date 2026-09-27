"""tiny_module — fixture for TestGap find_gaps tests."""

# Module-level statement (line 3 — will be used as an unattributed missing line)
MODULE_CONSTANT = 42


def calculate_total(items):
    """Public function — named in README."""
    total = 0
    for item in items:
        total += item
    return total


def _helper(x):
    """Private function — not named in docs."""
    return x * 2


def _decorator(fn):
    return fn


@_decorator
def decorated_func(value):
    """Decorated public function."""
    return value + 1


class MyClass:
    """A class with methods."""

    def method_one(self):
        """Public method."""
        return 1

    def _private_method(self):
        """Private method."""
        return 2

    def outer(self):
        """Method containing a nested function."""
        def inner(x):
            return x + 10
        return inner(5)

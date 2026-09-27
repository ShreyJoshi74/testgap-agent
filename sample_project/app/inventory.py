"""Stock tracking for products in a single warehouse."""


class OutOfStockError(Exception):
    """Raised when more units are requested than are in stock."""


class Inventory:
    """Keeps a count of units per SKU.

    SKUs are case-insensitive and stored upper-case. Counts never go below 0.
    """

    def __init__(self, low_stock_level=5):
        """Create an empty inventory.

        low_stock_level is the count at or below which a SKU is "low".
        Raises ValueError if it is negative.
        """
        if low_stock_level < 0:
            raise ValueError("low_stock_level must not be negative")
        self.low_stock_level = low_stock_level
        self._stock = {}

    def add_stock(self, sku, quantity):
        """Add quantity units of sku and return the new count.

        Raises ValueError if quantity is not a positive integer.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        key = sku.upper()
        self._stock[key] = self._stock.get(key, 0) + quantity
        return self._stock[key]

    def remove_stock(self, sku, quantity):
        """Remove quantity units of sku and return the new count.

        Raises ValueError if quantity is not a positive integer, and
        OutOfStockError if fewer than quantity units are available
        (including an unknown SKU).
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        key = sku.upper()
        available = self._stock.get(key, 0)
        if quantity > available:
            raise OutOfStockError(f"{key}: requested {quantity}, have {available}")
        self._stock[key] = available - quantity
        return self._stock[key]

    def count(self, sku):
        """Return the units in stock for sku (0 if unknown)."""
        return self._stock.get(sku.upper(), 0)

    def low_stock(self):
        """Return a sorted list of SKUs whose count is at or below low_stock_level."""
        return sorted(k for k, v in self._stock.items() if v <= self.low_stock_level)

    def total_value(self, prices):
        """Return the value of all stock given a {sku: unit_price} dict.

        SKUs missing from prices raise KeyError. Rounded to 2 decimals.
        """
        return round(sum(n * prices[k] for k, n in self._stock.items()), 2)

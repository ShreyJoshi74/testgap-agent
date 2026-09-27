import pytest

from app.inventory import Inventory, OutOfStockError


# ---------------------------------------------------------------------------
# Inventory.__init__
# ---------------------------------------------------------------------------

# Creating an inventory with the default low_stock_level succeeds
def test_init_default_low_stock_level():
    inv = Inventory()
    assert inv.low_stock_level == 5


# Creating an inventory with a custom low_stock_level stores it
def test_init_custom_low_stock_level():
    inv = Inventory(low_stock_level=10)
    assert inv.low_stock_level == 10


# A fresh inventory is empty (no stock for any SKU)
def test_init_stock_is_empty():
    inv = Inventory()
    assert inv.count("ANYTHING") == 0


# A negative low_stock_level raises ValueError
def test_init_negative_low_stock_level_raises():
    with pytest.raises(ValueError):
        Inventory(low_stock_level=-1)


# Zero is an allowed low_stock_level (boundary)
def test_init_zero_low_stock_level_allowed():
    inv = Inventory(low_stock_level=0)
    assert inv.low_stock_level == 0


# ---------------------------------------------------------------------------
# Inventory.add_stock
# ---------------------------------------------------------------------------

# Adding a valid quantity returns the new total
def test_add_stock_valid(faker):
    inv = Inventory()
    sku = faker.bothify("??-###").upper()
    result = inv.add_stock(sku, 10)
    assert result == 10


# Adding stock twice accumulates correctly
def test_add_stock_accumulates(faker):
    inv = Inventory()
    sku = faker.bothify("??-###").upper()
    inv.add_stock(sku, 5)
    result = inv.add_stock(sku, 3)
    assert result == 8


# SKU is stored upper-case regardless of input case
def test_add_stock_sku_case_insensitive():
    inv = Inventory()
    inv.add_stock("ab-1", 4)
    assert inv.count("AB-1") == 4


# quantity of zero raises ValueError
def test_add_stock_zero_quantity_raises():
    inv = Inventory()
    with pytest.raises(ValueError):
        inv.add_stock("SKU-1", 0)


# Negative quantity raises ValueError
def test_add_stock_negative_quantity_raises():
    inv = Inventory()
    with pytest.raises(ValueError):
        inv.add_stock("SKU-1", -5)


# Float quantity raises ValueError (must be int)
def test_add_stock_float_quantity_raises():
    inv = Inventory()
    with pytest.raises(ValueError):
        inv.add_stock("SKU-1", 1.0)


# ---------------------------------------------------------------------------
# Inventory.remove_stock
# ---------------------------------------------------------------------------

# Removing a valid quantity returns the remaining count
def test_remove_stock_valid():
    inv = Inventory()
    inv.add_stock("SKU-A", 10)
    result = inv.remove_stock("SKU-A", 3)
    assert result == 7


# Removing all units reduces count to zero
def test_remove_stock_all_units():
    inv = Inventory()
    inv.add_stock("SKU-B", 5)
    result = inv.remove_stock("SKU-B", 5)
    assert result == 0


# Removing more than available raises OutOfStockError
def test_remove_stock_more_than_available_raises():
    inv = Inventory()
    inv.add_stock("SKU-C", 2)
    with pytest.raises(OutOfStockError):
        inv.remove_stock("SKU-C", 3)


# Attempting to remove from an unknown SKU raises OutOfStockError
def test_remove_stock_unknown_sku_raises():
    inv = Inventory()
    with pytest.raises(OutOfStockError):
        inv.remove_stock("NOSUCHSKU", 1)


# After a failed remove the count is unchanged (I3)
def test_remove_stock_count_unchanged_after_error():
    inv = Inventory()
    inv.add_stock("SKU-D", 2)
    with pytest.raises(OutOfStockError):
        inv.remove_stock("SKU-D", 5)
    assert inv.count("SKU-D") == 2


# quantity of zero raises ValueError
def test_remove_stock_zero_quantity_raises():
    inv = Inventory()
    inv.add_stock("SKU-E", 5)
    with pytest.raises(ValueError):
        inv.remove_stock("SKU-E", 0)


# Negative quantity raises ValueError
def test_remove_stock_negative_quantity_raises():
    inv = Inventory()
    inv.add_stock("SKU-F", 5)
    with pytest.raises(ValueError):
        inv.remove_stock("SKU-F", -1)


# Float quantity raises ValueError (must be int)
def test_remove_stock_float_quantity_raises():
    inv = Inventory()
    inv.add_stock("SKU-G", 5)
    with pytest.raises(ValueError):
        inv.remove_stock("SKU-G", 2.0)


# SKU lookup is case-insensitive during removal
def test_remove_stock_case_insensitive():
    inv = Inventory()
    inv.add_stock("ab-1", 6)
    result = inv.remove_stock("AB-1", 4)
    assert result == 2


# ---------------------------------------------------------------------------
# Inventory.count
# ---------------------------------------------------------------------------

# count returns 0 for an unknown SKU
def test_count_unknown_sku():
    inv = Inventory()
    assert inv.count("UNKNOWN") == 0


# count reflects added stock
def test_count_after_add():
    inv = Inventory()
    inv.add_stock("SKU-H", 7)
    assert inv.count("SKU-H") == 7


# count is case-insensitive
def test_count_case_insensitive():
    inv = Inventory()
    inv.add_stock("xyz-9", 3)
    assert inv.count("XYZ-9") == 3


# ---------------------------------------------------------------------------
# Inventory.low_stock
# ---------------------------------------------------------------------------

# low_stock returns an empty list when inventory is empty
def test_low_stock_empty_inventory():
    inv = Inventory()
    assert inv.low_stock() == []


# A SKU at exactly the low_stock_level is included (boundary)
def test_low_stock_at_threshold():
    inv = Inventory(low_stock_level=5)
    inv.add_stock("SKU-I", 5)
    assert "SKU-I" in inv.low_stock()


# A SKU one above the low_stock_level is not included
def test_low_stock_just_above_threshold():
    inv = Inventory(low_stock_level=5)
    inv.add_stock("SKU-J", 6)
    assert "SKU-J" not in inv.low_stock()


# low_stock returns a sorted list
def test_low_stock_sorted():
    inv = Inventory(low_stock_level=10)
    inv.add_stock("ZZZ", 1)
    inv.add_stock("AAA", 2)
    inv.add_stock("MMM", 3)
    result = inv.low_stock()
    assert result == sorted(result)


# A SKU well below the threshold appears in low_stock
def test_low_stock_below_threshold():
    inv = Inventory(low_stock_level=5)
    inv.add_stock("SKU-K", 1)
    assert "SKU-K" in inv.low_stock()


# ---------------------------------------------------------------------------
# Inventory.total_value
# ---------------------------------------------------------------------------

# total_value returns 0.0 for an empty inventory
def test_total_value_empty_inventory():
    inv = Inventory()
    assert inv.total_value({}) == 0.0


# total_value computes the correct sum
def test_total_value_correct_sum():
    inv = Inventory()
    inv.add_stock("APPLE", 3)
    inv.add_stock("BANANA", 2)
    result = inv.total_value({"APPLE": 1.50, "BANANA": 0.75})
    assert result == round(3 * 1.50 + 2 * 0.75, 2)


# total_value rounds to 2 decimal places
def test_total_value_rounded():
    inv = Inventory()
    inv.add_stock("ITEM", 3)
    result = inv.total_value({"ITEM": 0.1})
    assert result == round(0.3, 2)


# Missing SKU in prices raises KeyError
def test_total_value_missing_price_raises():
    inv = Inventory()
    inv.add_stock("NOPRICE", 5)
    with pytest.raises(KeyError):
        inv.total_value({})

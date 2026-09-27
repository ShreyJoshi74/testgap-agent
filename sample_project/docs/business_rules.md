# ShopLite Business Rules

The code in `app/` must follow these rules. Tests should check the rules, not just
whatever the code happens to do today.

## Money

- M1. All money amounts are rounded **half-up** to 2 decimal places (2.675 → 2.68).
- M2. Negative amounts keep their sign when rounded (-1.005 → -1.01).

## Orders

- O1. Each order line needs a price of 0 or more and a quantity that is a whole number of at least 1.
- O2. An empty order has a subtotal of 0.00.
- O3. **A discount must be between 0% and 100% (inclusive). A discount over 100% is invalid
  and must be rejected with a `ValueError`.** A negative discount is also invalid.
  A discounted price can therefore never be negative.
- O4. Shipping is free when the discounted subtotal is 50.00 or more, and also for an empty order.
  Otherwise shipping costs a flat 5.99.
- O5. Tax is 8% of the discounted subtotal. Shipping is not taxed. A negative tax rate is invalid.
- O6. Order total = discounted subtotal + shipping + tax.

## Users

- U1. E-mail addresses are compared without surrounding spaces and ignoring case.
- U2. An e-mail must look like `name@domain.tld`.
- U3. The same e-mail cannot be registered twice.
- U4. Usernames are 3–20 characters, using only lower-case letters, digits and `_`.
- U5. Users must be 18 or older. A negative age is invalid.
- U6. A new user is active, and their name is stored title-cased ("ada lovelace" → "Ada Lovelace").

## Payments

- P1. Card numbers must pass the Luhn checksum. Spaces and hyphens are allowed and ignored.
- P2. Only the last 4 digits of a card are ever shown; the rest are replaced with `*`.
- P3. The card processing fee is 2.9% + 0.30. A payment of 0.00 has no fee. Negative amounts are invalid.
- P4. When a bill is split, the shares must add up to exactly the bill. Leftover cents go to the first people.
- P5. Refunds: 100% within 14 days of purchase, 50% from day 15 to day 30, nothing after day 30.

## Inventory

- I1. SKUs are case-insensitive (`ab-1` and `AB-1` are the same product).
- I2. Stock can only be added or removed in whole numbers of at least 1.
- I3. Stock can never go below 0. Removing more than is available raises `OutOfStockError`
  and leaves the count unchanged.
- I4. A SKU is "low stock" when its count is at or below the low-stock level (default 5).

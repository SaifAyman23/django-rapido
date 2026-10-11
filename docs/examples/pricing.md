# REUSE: Tiered Pricing Example

> Copy-paste tiered fee pattern — swap values per project.

```python
from decimal import Decimal

# REUSE: Core fee table — swap values per project
SERVICE_FEE_TABLE = {1: Decimal("30.00"), "2-5": Decimal("50.00"), "else": Decimal("75.00")}

def calculate_service_fee(distinct_item_count: int) -> Decimal:
    """REUSE: Tiered fee by distinct item count."""
    if distinct_item_count == 1:
        return Decimal("30.00")
    if 2 <= distinct_item_count <= 5:
        return Decimal("50.00")
    return Decimal("75.00")
```

For vouchers + auto-discounts, see `recalculate_discount()` — stacked base vs add-on caps:

```python
def calculate_stacked_discount(voucher, discounts, subtotal, fee):
    """REUSE: Apply voucher + auto-discounts, capped by base vs add-on."""
    base_discount = min(calculate_discount(voucher, subtotal, "base"), subtotal)
    addon_discount = min(calculate_discount(voucher, fee, "addon"), fee)
    for d in discounts:
        base_discount += min(calculate_discount(d, subtotal, "base"), subtotal - base_discount)
    return base_discount + addon_discount
```

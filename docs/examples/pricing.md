# REUSE: Tiered Pricing Example

From ras-elbar-go `orders/services/pricing.py`.

```python
from decimal import Decimal

# REUSE: Core fee table — swap values per project
DELIVERY_FEE_TABLE = {1: Decimal("30.00"), "2-5": Decimal("50.00"), "else": Decimal("75.00")}

def calculate_delivery_fee(distinct_category_count: int) -> Decimal:
    """REUSE: Tiered fee by distinct categories."""
    if distinct_category_count == 1:
        return Decimal("30.00")
    if 2 <= distinct_category_count <= 5:
        return Decimal("50.00")
    return Decimal("75.00")
```

For coupons + auto-discounts, see `recalculate_discount()` — stacked product vs delivery caps:

```python
def calculate_stacked_discount(coupon, discounts, subtotal, fee):
    """REUSE: Apply coupon + auto-discounts, capped by product vs delivery."""
    product_discount = min(calculate_discount(coupon, subtotal, "products"), subtotal)
    delivery_discount = min(calculate_discount(coupon, fee, "delivery"), fee)
    for d in discounts:
        product_discount += min(calculate_discount(d, subtotal, "products"), subtotal - product_discount)
    return product_discount + delivery_discount
```

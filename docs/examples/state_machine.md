# REUSE: Generic State Machine Pattern

From ras-elbar-go `orders/services/lifecycle.py` + `AGENTS.md:15.2`.

Use when your model has status transitions that must be atomic, audited,
and role-scoped. Example: Order `submitted→prepared→arrived→complete`.

## Model

```python
from common.models import UUIDModel, TimestampedModel

class OrderStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    PREPARED = "prepared", "Prepared"
    ARRIVED = "arrived", "Arrived"
    COMPLETE = "complete", "Complete"

class Order(TimestampedModel, UUIDModel):
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.SUBMITTED, db_index=True)
```

## Helpers (app/services/lifecycle.py)

```python
# REUSE: Small helpers — no business logic, just guard + log
def is_cancellable(order) -> bool:
    return order.status == OrderStatus.SUBMITTED

def log_status_event(order, status, changed_by: str):
    return OrderStatusEvent.objects.create(order=order, status=status, changed_by=changed_by)

def release_driver(order):  # abstracted: decrement + availability conditional
    User.objects.filter(id=order.driver_id, active_order_count__gt=0).update(active_order_count=F("active_order_count")-1)
    User.objects.filter(id=order.driver_id, active_order_count=0, availability_status="unavailable").update(availability_status="offline")
    User.objects.filter(id=order.driver_id, active_order_count=0, availability_status="on_duty").update(availability_status="available")
```

## View — role-scoped, transaction + row lock

```python
from django.db import transaction
from rest_framework.decorators import action

class OrderViewSet(BaseViewSet):
    @action(detail=True, methods=["post"], permission_classes=[IsDeliveryman])
    @transaction.atomic
    def mark_prepared(self, request, pk=None):
        order = Order.objects.select_for_update().get(id=pk, assigned_driver=request.user)
        if order.status != OrderStatus.SUBMITTED:
            return Response({"error": "Invalid transition"}, status=409)
        order.status = OrderStatus.PREPARED
        order.save(update_fields=["status"])
        log_status_event(order, OrderStatus.PREPARED, "DRIVER")
        return Response({"status": order.status})
```

Rules:
- Transitions only inside `@transaction.atomic + select_for_update` actions
- Never set `status` in serializers or signals
- Every transition creates `*StatusEvent`
- Cancellation only from initial state

See `orders/services/pricing.py` for tiered fee example.

# REUSE: Generic State Machine Pattern

> Copy-paste pattern for any model with status transitions. Example: `Task draft → in_review → approved → published`. See `AGENTS.md` for transaction/locking rules.

Use when your model has status transitions that must be atomic, audited,
and role-scoped. Example: Task `draft→in_review→approved→published`.

## Model

```python
from common.models import UUIDModel, TimestampedModel

class TaskStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    PUBLISHED = "published", "Published"

class Task(TimestampedModel, UUIDModel):
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.DRAFT, db_index=True)
```

## Helpers (app/services/lifecycle.py)

```python
# REUSE: Small helpers — no business logic, just guard + log
def is_cancellable(task) -> bool:
    return task.status == TaskStatus.DRAFT

def log_status_event(task, status, changed_by: str):
    return TaskStatusEvent.objects.create(task=task, status=status, changed_by=changed_by)

def release_assignee(task):  # abstracted: decrement + availability conditional
    User.objects.filter(id=task.assignee_id, active_task_count__gt=0).update(active_task_count=F("active_task_count")-1)
    User.objects.filter(id=task.assignee_id, active_task_count=0, availability_status="unavailable").update(availability_status="offline")
    User.objects.filter(id=task.assignee_id, active_task_count=0, availability_status="on_duty").update(availability_status="available")
```

## View — role-scoped, transaction + row lock

```python
from django.db import transaction
from rest_framework.decorators import action

class TaskViewSet(BaseViewSet):
    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    @transaction.atomic
    def mark_approved(self, request, pk=None):
        task = Task.objects.select_for_update().get(id=pk, assigned_to=request.user)
        if task.status != TaskStatus.IN_REVIEW:
            return Response({"error": "Invalid transition"}, status=409)
        task.status = TaskStatus.APPROVED
        task.save(update_fields=["status"])
        log_status_event(task, TaskStatus.APPROVED, "STAFF")
        return Response({"status": task.status})
```

Rules:
- Transitions only inside `@transaction.atomic + select_for_update` actions
- Never set `status` in serializers or signals
- Every transition creates `*StatusEvent`
- Cancellation only from initial state

See `docs/examples/pricing.md` for tiered pricing example.

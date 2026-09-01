# Compliance & Contacts Guide (REUSE)

## Compliance — FAQ + Legal Docs

From ras-elbar-go `compliance/` — generic CMS, translatable, Markdown.

### Models (compliance/models.py)

```python
class DocumentType(TextChoices):
    PRIVACY_POLICY = "PRIVACY_POLICY", "Privacy Policy"
    TERMS_OF_SERVICE = "TERMS_OF_SERVICE", "Terms of Service"
    # Add: COOKIE_POLICY, REFUND_POLICY

class FAQ(TimestampedModel, UUIDModel):
    question = CharField(500)  # translatable
    answer = TextField(10000)  # translatable, Markdown
    sort_order = PositiveIntegerField(db_index=True)
    is_published = BooleanField(db_index=True)
    ordering = ["sort_order"]

class ComplianceDocument(TimestampedModel, UUIDModel):
    type = CharField(30, choices=DocumentType, unique=True)
    title = CharField(200)  # translatable
    content = TextField(50000)  # translatable, Markdown
    is_published = BooleanField(default=True)
```

Translation `compliance/translation.py`:

```python
from modeltranslation.translator import translator, TranslationOptions
class FAQTranslationOptions(TranslationOptions): fields = ("question", "answer")
translator.register(FAQ, FAQTranslationOptions)
```

Requires `modeltranslation` before `admin` in `INSTALLED_APPS`.

### Admin

```python
@admin.register(FAQ)
class FAQAdmin(TranslationBaseAdmin):  # from common.unfold_admin_bases
    list_display = ["question_preview", "is_published_badge", "sort_order"]
    # badge(): self.badge("Published","green")

@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(MarkdownAdminMixin, TranslationBaseAdmin):
    # MarkdownAdminMixin auto-applies AdminMarkdownxWidget to TextFields
```

Requires `markdownx` in `INSTALLED_APPS` + `path('markdownx/', include('markdownx.urls'))` in `project/urls.py`.

### API (compliance/views.py)

```python
class FAQViewSet(BaseViewSet):
    permission_classes = [AllowAny]
    def get_queryset(): return qs.filter(is_published=True) if not staff else qs
    # create/update/destroy → IsAdminUser

# URLs: /api/v1/compliance/faqs/, /api/v1/compliance/documents/
```

---

## Contacts — Form + Business Info

From ras-elbar-go `contacts/` — generic, no delivery logic.

### Models (contacts/models.py)

```python
class ContactMessage(TimestampedModel, UUIDModel):
    name, email, subject, message
    ordering = ["-created_at"]

class ContactInfo(TimestampedModel, UUIDModel):  # singleton
    address, phone, email, working_hours
    start_hours, end_hours = TimeField(null/blank)  # REUSE: BUSINESS_TIME_ZONE gate
    facebook_url, instagram_url, twitter_url, linkedin_url
    latitude, longitude = DecimalField(9,6, null/blank)
    def save(): if not pk and exists: raise ValidationError("Only one allowed.")
```

### Service — Hours Gate

```python
# contacts/services.py
def is_ordering_open() -> (bool, str):
    info = ContactInfo.objects.first()
    if not info or not start/end: return True, "always open"
    tz = pytz.timezone(settings.BUSINESS_TIME_ZONE)  # "Africa/Cairo"
    now_local = timezone.now().astimezone(tz)
    # Handles overnight 22:00-04:00
    return (start <= now_time <= end) if start <= end else (now_time >= start or now_time <= end)
```

Use in checkout gating: `if not is_ordering_open()[0]: block`. `BUSINESS_TIME_ZONE` in `base.py:217` (`Africa/Cairo` default).

### Serializers

```python
class ContactInfoSerializer(serializers.ModelSerializer):
    ordering_open = SerializerMethodField()  # → is_ordering_open()[0]
    site_inactive = SerializerMethodField()  # → not ordering_open
```

### Views & URLs

```python
class ContactMessageViewSet(BaseViewSet):
    permission_classes = [AllowAny]
    http_method_names = ["post", "head", "options"]  # POST only

class ContactInfoViewSet(BaseViewSet):
    permission_classes = [AllowAny]
    pagination_class = None
    def get_queryset(): return ContactInfo.objects.all()[:1]  # singleton GET

# contacts/urls.py + project/urls.py: path(f'{api_prefix}/contacts/', include('contacts.urls'))
```

---

## Setup

```bash
python manage.py makemigrations compliance contacts
python manage.py migrate
# Add in admin: FAQ, ComplianceDocument (privacy/terms), ContactInfo (hours)
```

All REUSE-commented, project-agnostic. Extend `DocumentType` or add `ContactInfo` fields per project.

---

## Removal — How to Remove This Feature

### Compliance (drop FAQ + legal docs)

1. **Settings `project/settings/base.py:63`** → delete `compliance` from `INSTALLED_APPS` + if no other app uses translation, also delete `modeltranslation` from `INSTALLED_APPS` `base.py:66` + `MODELTRANSLATION_*` block `base.py:210-214` + `LOCALE_PATHS` `base.py:204` + `LANGUAGES` `base.py:198` (see i18n guide for full unwiring).
2. **URLs `project/urls.py`** → delete `path(f'{api_prefix}/compliance/', include('compliance.urls'))`.
3. **Delete app** `compliance/` (6 files: `models.py`, `translation.py`, `admin.py` (`FAQAdmin(TranslationBaseAdmin)` `base.py:212` + `ComplianceDocumentAdmin(MarkdownAdminMixin,TranslationBaseAdmin)`), `serializers.py`, `views.py`, `urls.py`).
4. **Admin** `project/settings/unfold_config.py` → delete `Compliance` group (2 items: `FAQs` + `Policies`).
5. **Common** `common/unfold_admin_bases.py:22 from modeltranslation.admin import TranslationAdmin` + `common/admin_mixins.py:2 from markdownx.widgets import AdminMarkdownxWidget` + `common/translation_utils.py:8` — keep `TranslationBaseAdmin` class and `MarkdownAdminMixin` if other apps use them (e.g. future translatable models), delete `from modeltranslation`/`markdownx` imports only if `modeltranslation`/`markdownx` are fully removed (else `ImportError`).
6. **Requirements `requirements.txt:82-85`** → delete `django-modeltranslation==0.20.2` + `markdown==3.7` + `django-markdownx==4.0.1` **only if** no other app uses them (Live Logs does not use them, but future apps may).
7. **Env** No dedicated env var for compliance — uses `CACHE_URL`/`BUSINESS_TIME_ZONE` only via other apps.
8. **DB** `python manage.py migrate compliance zero` before deleting, or `DROP TABLE compliance_faq, compliance_compliancedocument`.

### Contacts (drop form + hours gate)

1. **Settings** `project/settings/base.py:64` → delete `contacts` from `INSTALLED_APPS` + delete `BUSINESS_TIME_ZONE = os.getenv("BUSINESS_TIME_ZONE", "Africa/Cairo")` `base.py:217` if not used elsewhere (only consumer is `contacts/services.py:22 settings.BUSINESS_TIME_ZONE` → `pytz.timezone` check for overnight `22:00-04:00`).
2. **Env** `.env.example:19` → delete `BUSINESS_TIME_ZONE=Africa/Cairo` (commented `REUSE: for is_ordering_open()`). Also delete `LOGIN_USERNAME/PASSWORD` if only used for `dashboard/forms.py` prefill, but keep if Live Logs admin uses them.
3. **URLs** `project/urls.py` → delete `path(f'{api_prefix}/contacts/', include('contacts.urls'))`.
4. **Delete app** `contacts/` (7 files: `models.py` (`ContactMessage` + `ContactInfo singleton save()`), `services.py` (`is_ordering_open()` `pytz.timezone` overnight), `serializers.py` (`ordering_open`/`site_inactive` derived), `views.py` (`AllowAny` POST only), `urls.py`, `admin.py`).
5. **Admin** `project/settings/unfold_config.py` → delete `Contacts` group (2 items: `Contact Info` + `Contact Messages`).
6. **Code** Remove any `from contacts.services import is_ordering_open` usage (e.g. checkout gating) — keep if you need hours gate elsewhere (e.g. store hours).
7. **Common** No `common/` direct import of `contacts` — generic.
8. **Requirements `requirements.txt:53`** → keep `pytz==2024.2` (`contacts/services.py:7 pytz.timezone`) only if you use timezones elsewhere — `dashboard/live_logs.py` uses `timezone.now()` not `pytz`, so safe to delete if `contacts` is the sole `pytz` consumer; `tzdata`/`tzlocal` are for Celery/DB, not contacts.
9. **DB** `python manage.py migrate contacts zero` before deleting.

After removal, run `make check && docker compose config > /dev/null`.

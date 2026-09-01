# i18n Guide — modeltranslation en/ar (REUSE)

## Setup (base.py:206)

```python
# project/settings/base.py:51 — must be before admin
INSTALLED_APPS = ["modeltranslation", "django.contrib.admin", ...]
LANGUAGES = [('en', 'English'), ('ar', 'العربية')]
USE_I18N = True
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]
MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_LANGUAGES = ('en', 'ar')
MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'ar')
MODELTRANSLATION_PREFER_ADMIN_LANGUAGE = True
TIME_ZONE = "UTC"
USE_TZ = True
BUSINESS_TIME_ZONE = "Africa/Cairo"  # REUSE: for is_ordering_open()
MIDDLEWARE = ["django.middleware.locale.LocaleMiddleware", ...]  # after Session, before Common
```

## Model (compliance/translation.py)

```python
from modeltranslation.translator import translator, TranslationOptions
from .models import FAQ

class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")  # only user-facing text, not slug/status

translator.register(FAQ, FAQTranslationOptions)
# Adds question_en/question_ar, answer_en/answer_ar columns via makemigrations
```

## Admin

```python
from common.unfold_admin_bases import TranslationBaseAdmin

@admin.register(FAQ)
class FAQAdmin(TranslationBaseAdmin):  # NOT BaseAdmin
    # Tabs per language auto-added
    list_display = ["question_preview", ...]
```

`TranslationBaseAdmin` patches `search_fields/list_display/list_filter` to current language column.

## Serializer

No changes — `obj.name` resolves to active language via `Accept-Language` header transparently.

```python
class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer"]  # virtual field works
```

## Commands

```bash
python manage.py makemessages -l ar
python manage.py compilemessages
# Generates locale/ar/LC_MESSAGES/django.po → django.mo
```

`locale/` already in `LOCALE_PATHS`. See `contacts/services.py is_ordering_open()` for `BUSINESS_TIME_ZONE` usage.

## Markdown (compliance)

```python
@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(MarkdownAdminMixin, TranslationBaseAdmin):
    pass
# Requires markdownx in INSTALLED_APPS + path('markdownx/', include('markdownx.urls'))
```

---

## Removal — How to Remove This Feature

> Fully optional — **ar/en** can be dropped to single-language `en` only.

### Drop i18n Entirely (single language `en`)

1. **Settings `project/settings/base.py`** → delete `modeltranslation` from `INSTALLED_APPS` `base.py:66`, delete `MODELTRANSLATION_*` block `base.py:210-214`, delete `LOCALE_PATHS` `base.py:204`, delete `LANGUAGES` `base.py:198` (keep `LANGUAGE_CODE="en"`), delete `LocaleMiddleware` from `MIDDLEWARE` `base.py:107`, keep `USE_I18N=True` if you still use `gettext_lazy` else `False`.
2. **Delete files** `locale/` folder (translations), `compliance/translation.py`, `notifications/models.py TranslationBaseAdmin` usage → change `FAQAdmin(TranslationBaseAdmin)` → `FAQAdmin(BaseAdmin)` in `compliance/admin.py`, same for any `TranslationBaseAdmin` in `common/unfold_admin_bases.py:22` (keep class `TranslationBaseAdmin` but its `from modeltranslation.admin import TranslationAdmin` will `ImportError` if `modeltranslation` deleted — either keep `try: import` fallback already in file, or delete the class). Also delete `common/translation_utils.py:8` re-exports if not used elsewhere.
3. **Requirements** `requirements.txt:82` → delete `django-modeltranslation==0.20.2`.
4. **URLs** `project/urls.py` → unwrap `i18n_patterns` — change `i18n_patterns(path('admin/', ...))` → plain `path('admin/', ...)`, delete `path('i18n/', include('django.conf.urls.i18n'))` + `live_logs_page/stream` stays plain (we already have fallback `admin/live-logs-nolang` — keep those as primary).
5. **Nginx** `nginx.conf:56` + `nginx.prod.conf` SSE locations `~ ^/(en|ar)?/?admin/live-logs/stream/` → simplify to `~ ^/admin/live-logs/stream/` if you drop `ar`.
6. **Check** `make check && python manage.py makemessages --help` will fail if `modeltranslation` still referenced — ensure deleted.

### Keep i18n but Drop ar Only

- Keep `modeltranslation`, delete `locale/ar/`, remove `('ar', ...)` from `LANGUAGES` + `MODELTRANSLATION_LANGUAGES`.
- `python manage.py compilemessages` still works for `en` only.


"""
Translation utilities — re-exports all helpers from common.helpers.

This module exists for backward compatibility with existing locale references.
All actual implementation lives in common.helpers.
"""

from common.helpers import (  # noqa: F401
    bulk_restore,
    bulk_soft_delete,
    camelcase_to_snakecase,
    chunk_list,
    deep_merge,
    dict_to_querystring,
    extract_dict_keys,
    flatten_list,
    format_file_size,
    generate_code,
    generate_slug,
    generate_token,
    get_date_range,
    get_file_extension,
    humanize_timedelta,
    is_allowed_file_type,
    is_strong_password,
    is_valid_email,
    is_valid_ipv4,
    is_valid_phone,
    is_valid_url,
    is_within_timeframe,
    log_audit,
    mask_email,
    mask_phone,
    safe_json_dumps,
    safe_json_loads,
    snakecase_to_camelcase,
    truncate_string,
)

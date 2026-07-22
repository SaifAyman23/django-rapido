"""
Translation utilities — re-exports all helpers from common.helpers.

This module exists for backward compatibility with existing locale references.
All actual implementation lives in common.helpers.
"""

from common.helpers import (  # noqa: F401
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    is_valid_ipv4,
    is_strong_password,
    truncate_string,
    camelcase_to_snakecase,
    snakecase_to_camelcase,
    generate_slug,
    mask_email,
    mask_phone,
    safe_json_loads,
    safe_json_dumps,
    deep_merge,
    get_date_range,
    is_within_timeframe,
    humanize_timedelta,
    generate_token,
    generate_code,
    chunk_list,
    flatten_list,
    dict_to_querystring,
    extract_dict_keys,
    get_file_extension,
    is_allowed_file_type,
    format_file_size,
    bulk_soft_delete,
    bulk_restore,
    log_audit,
)

"""Reusable view and function decorators.

Provides permission checks, logging, caching, and retry helpers for API views.
"""

import hashlib
import logging
from functools import wraps
from typing import Callable, List, TypeVar

from django.core.cache import cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ===========================
# Permission & Auth Decorators
# ===========================


def check_permissions(required_permissions: List[str]):
    """Require specific Django permissions before calling the view method."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied("Authentication required")

            for perm in required_permissions:
                if not user.has_perm(perm):
                    raise PermissionDenied(f"Permission {perm} required")

            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def check_object_permissions(func):
    """Enforce object-level permissions using the view's check_object_permissions."""

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        obj = self.get_object()
        self.check_object_permissions(request, obj)
        return func(self, request, *args, **kwargs)

    return wrapper


def log_action(action_type: str):
    """Log the view action with user and request metadata for auditing."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            logger.info(
                f"{action_type}: {self.__class__.__name__}",
                extra={
                    "user_id": request.user.id if request.user else None,
                    "method": request.method,
                    "path": request.path,
                },
            )
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


# ===========================
# Caching Decorators
# ===========================
def cache_result(timeout: int = 300):
    """Cache the function's return value for the given timeout in seconds."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key
            cache_key = f"{func.__module__}.{func.__name__}"
            if args:
                cache_key += f":{hashlib.md5(str(args).encode()).hexdigest()}"
            if kwargs:
                cache_key += f":{hashlib.md5(str(kwargs).encode()).hexdigest()}"

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache set: {cache_key} (timeout: {timeout}s)")

            return result

        wrapper.clear_cache = lambda: cache.delete(cache_key)
        return wrapper

    return decorator


def cache_per_request():
    """Memoize the result per-request instance to avoid duplicate work."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs) -> T:
            cache_attr = f"_cache_{func.__name__}"

            if not hasattr(request, cache_attr):
                result = func(self, request, *args, **kwargs)
                setattr(request, cache_attr, result)
            else:
                result = getattr(request, cache_attr)

            return result

        return wrapper

    return decorator


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Retry the function on exception with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries exceeded for {func.__name__}: {str(e)}")
                        raise

                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}"
                    )

                    import time

                    time.sleep(delay * (2**attempt))  # Exponential backoff

        return wrapper

    return decorator


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """In-memory memoization for pure functions within the process lifetime."""
    cache_dict = {}

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        key = (args, tuple(sorted(kwargs.items())))

        if key not in cache_dict:
            cache_dict[key] = func(*args, **kwargs)

        return cache_dict[key]

    wrapper.cache = cache_dict
    wrapper.clear_cache = cache_dict.clear

    return wrapper

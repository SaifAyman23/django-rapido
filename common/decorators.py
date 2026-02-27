import logging
import hashlib

from django.core.cache import cache
from typing import TypeVar, Callable, List
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ===========================
# Permission & Auth Decorators
# ===========================

def check_permissions(required_permissions: List[str]):
    """Decorator to check multiple permissions"""
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
    """Decorator to check object-level permissions"""
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        obj = self.get_object()
        self.check_object_permissions(request, obj)
        return func(self, request, *args, **kwargs)
    return wrapper


def log_action(action_type: str):
    """Decorator to log view actions"""
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
    """Cache function result"""
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
    """Cache result per request"""
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
    """Retry function on exception"""
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
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff

        return wrapper

    return decorator


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """Memoize function results (in-memory cache)"""
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


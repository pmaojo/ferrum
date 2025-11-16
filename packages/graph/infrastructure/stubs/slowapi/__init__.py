"""Stub slowapi package for tests.

This module provides a *very* small subset of the real ``slowapi`` package so
that the rest of the codebase can be executed without the optional dependency
installed.  A minimal in-memory rate limiter is included purely for testing
purposes and lacks many features of the real implementation (time windows,
per-client limits, etc.). ``RateLimitExceeded`` is available from
``slowapi.errors`` and is imported here only for internal use.
"""

from collections import defaultdict

from .errors import RateLimitExceeded  # re-exported from ``slowapi.errors``


class Limiter:
    """Extremely small in-memory rate limiter used for tests.

    The limiter simply counts how many times a decorated function has been
    called.  Once the configured maximum is exceeded a ``RateLimitExceeded``
    exception is raised.  All advanced behaviours from the real package are
    intentionally omitted.
    """

    def __init__(self, *_, **__):
        self._counts = defaultdict(int)

    def limit(self, limit_value, *_, **__):
        """Return a decorator enforcing a maximum call count.

        ``limit_value`` may be a simple integer or a string such as ``"5/min"``;
        only the leading integer portion is considered.  If parsing fails no
        limiting is applied.
        """

        try:
            max_calls = int(str(limit_value).split("/")[0])
        except Exception:
            max_calls = None

        def decorator(func):
            def wrapper(*args, **kwargs):
                if max_calls is not None:
                    self._counts[func] += 1
                    if self._counts[func] > max_calls:
                        raise RateLimitExceeded("Rate limit exceeded")
                # When ``max_calls`` is ``None`` no limiting is applied.
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Simple no-op handler used by FastAPI in tests.
_rate_limit_exceeded_handler = lambda request, exc: None


__all__ = ["Limiter", "_rate_limit_exceeded_handler"]

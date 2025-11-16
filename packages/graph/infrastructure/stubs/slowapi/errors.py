"""Exception types for the :mod:`slowapi` stub.

``RateLimitExceeded`` is defined here so that it is exported from a single
location.  Import it as ``slowapi.errors.RateLimitExceeded``; the package root
does not re-export the symbol to keep the stub minimal.
"""


class RateLimitExceeded(Exception):
    """Raised when a request exceeds the configured rate limit."""

    pass


__all__ = ["RateLimitExceeded"]

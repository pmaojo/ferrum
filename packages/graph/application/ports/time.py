from abc import abstractmethod
from datetime import datetime, timezone
from typing import Protocol


class ClockPort(Protocol):
    """Abstraction for retrieving the current time.

    The clock port enables deterministic tests by allowing callers to
    supply a predictable time source. Implementations should be side
    effect free and may delegate to ``time.time`` or other time APIs.
    """

    @abstractmethod
    def now(self) -> float:
        """Return the current time in seconds since the epoch."""
        ...

    def now_datetime(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.now(), tz=timezone.utc)


__all__ = ["ClockPort"]

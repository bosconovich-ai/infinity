"""Runtime helpers for deterministic services."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Return the current UTC time."""

    def now(self) -> datetime:
        """Return a timezone-aware UTC timestamp."""

        return datetime.now(tz=UTC)


class TimestampIdGenerator:
    """Generate ids derived from the creation timestamp."""

    def new_id(self, created_at: datetime) -> str:
        """Build a stable id using UTC timestamp precision down to microseconds."""

        return created_at.strftime("idea_%Y%m%d_%H%M%S_%f")

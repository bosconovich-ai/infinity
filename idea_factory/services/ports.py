"""Ports used by the service layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, Sequence

from idea_factory.domain.models import IdeaCard, IdeaStatus, StructuredIdeaDraft


class LLMPort(Protocol):
    """Build structured idea drafts from raw human comments."""

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        """Convert free-form text into a normalized idea draft."""


class IdeaRepositoryPort(Protocol):
    """Persist and query idea cards."""

    def save(self, card: IdeaCard) -> Path:
        """Persist an idea card and return the file path."""

    def list_by_status(
        self,
        status: IdeaStatus,
        *,
        limit: int = 5,
    ) -> Sequence[IdeaCard]:
        """Return recent cards for a given status."""


class ClockPort(Protocol):
    """Provide current time for deterministic services."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""


class IdGeneratorPort(Protocol):
    """Generate stable identifiers for new idea cards."""

    def new_id(self, created_at: datetime) -> str:
        """Create an id for a new idea card."""

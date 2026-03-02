"""Ports used by the service layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, Sequence

from idea_factory.domain.ideation import IdeationDomainProfile
from idea_factory.domain.models import IdeaCard, IdeaStatus, StructuredIdeaDraft
from idea_factory.domain.signals import MarketSignal


class LLMPort(Protocol):
    """Build structured idea drafts from raw human comments."""

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        """Convert free-form text into a normalized idea draft."""


class AutonomousIdeationPort(Protocol):
    """Generate batches of autonomous project ideas."""

    def generate_ideas(
        self,
        *,
        batch_size: int,
        seed_context: str,
        domain_profile: IdeationDomainProfile,
        creative_angle: str,
    ) -> Sequence[StructuredIdeaDraft]:
        """Generate a batch of structured ideas for one domain focus."""


class SignalCollectorPort(Protocol):
    """Collect live market signals for a given domain."""

    def collect_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
        limit: int,
    ) -> Sequence[MarketSignal]:
        """Return collected market signals."""


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

    def get_by_id(self, idea_id: str) -> IdeaCard | None:
        """Return one idea card by id if it exists."""

    def move_to_status(self, idea_id: str, *, status: IdeaStatus) -> Path:
        """Move an existing idea card into another status bucket."""


class ClockPort(Protocol):
    """Provide current time for deterministic services."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""


class IdGeneratorPort(Protocol):
    """Generate stable identifiers for new idea cards."""

    def new_id(self, created_at: datetime) -> str:
        """Create an id for a new idea card."""

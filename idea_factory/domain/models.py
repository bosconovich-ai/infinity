"""Core domain entities for the idea intake workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DecisionAction(StrEnum):
    """Actions available to the human reviewer."""

    DO = "do"
    DONT = "dont"
    RETHINK = "rethink"


class IdeaStatus(StrEnum):
    """Storage states for idea cards."""

    INBOX = "inbox"
    APPROVED = "approved"
    REJECTED = "rejected"
    INCUBATING = "incubating"


@dataclass(frozen=True, slots=True)
class StructuredIdeaDraft:
    """Normalized idea information returned by the structuring layer."""

    title: str
    one_liner: str
    problem: str
    target_user: str
    why_subscription: str
    acquisition_channel: str
    key_features: tuple[str, ...]
    risks: tuple[str, ...]
    source_signals: tuple[str, ...]
    agent_notes: str
    score: float | None = None


@dataclass(frozen=True, slots=True)
class IdeaCard:
    """Persisted project idea ready for human review or implementation."""

    idea_id: str
    status: IdeaStatus
    created_at: datetime
    title: str
    one_liner: str
    problem: str
    target_user: str
    why_subscription: str
    acquisition_channel: str
    key_features: tuple[str, ...]
    risks: tuple[str, ...]
    source_signals: tuple[str, ...]
    agent_notes: str
    human_comment: str
    score: float | None = None

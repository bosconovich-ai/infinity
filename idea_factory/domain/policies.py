"""Pure domain policies for routing and naming idea cards."""

from __future__ import annotations

import re

from idea_factory.domain.models import DecisionAction, IdeaStatus

_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def status_for_decision(decision: DecisionAction) -> IdeaStatus:
    """Map a reviewer action to the persisted status.

    Args:
        decision: The action chosen by the reviewer.

    Returns:
        The storage status for the resulting idea card.
    """

    mapping = {
        DecisionAction.DO: IdeaStatus.APPROVED,
        DecisionAction.DONT: IdeaStatus.REJECTED,
        DecisionAction.RETHINK: IdeaStatus.INCUBATING,
    }
    return mapping[decision]


def slugify_title(title: str) -> str:
    """Create a filesystem-safe slug from an idea title.

    Args:
        title: Human-readable title.

    Returns:
        Lower-case slug suitable for filenames.
    """

    normalized = _NON_ALNUM_PATTERN.sub("-", title.lower()).strip("-")
    return normalized or "idea"

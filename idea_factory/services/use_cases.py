"""Use-cases for creating and browsing idea cards."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from idea_factory.domain.models import DecisionAction, IdeaCard, IdeaStatus
from idea_factory.domain.policies import status_for_decision
from idea_factory.services.ports import (
    ClockPort,
    IdGeneratorPort,
    IdeaRepositoryPort,
    LLMPort,
)


@dataclass(frozen=True, slots=True)
class SavedIdeaResult:
    """Result returned after persisting an idea card."""

    card: IdeaCard
    path: Path


class CreateIdeaFromCommentUseCase:
    """Turn a free-form comment into a persisted idea card."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        repository: IdeaRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
    ) -> None:
        self._llm = llm
        self._repository = repository
        self._clock = clock
        self._id_generator = id_generator

    def execute(
        self,
        *,
        raw_comment: str,
        decision: DecisionAction,
    ) -> SavedIdeaResult:
        """Normalize a raw comment and save it under the chosen decision.

        Args:
            raw_comment: Unstructured project note from the human reviewer.
            decision: Target decision bucket.

        Returns:
            A saved card and its file location.

        Raises:
            ValueError: If the comment is empty after trimming.
        """

        clean_comment = " ".join(raw_comment.split())
        if not clean_comment:
            raise ValueError("Project comment must not be empty.")

        draft = self._llm.structure_comment(clean_comment)
        created_at = self._clock.now()
        card = IdeaCard(
            idea_id=self._id_generator.new_id(created_at),
            status=status_for_decision(decision),
            created_at=created_at,
            title=draft.title,
            one_liner=draft.one_liner,
            problem=draft.problem,
            target_user=draft.target_user,
            why_subscription=draft.why_subscription,
            acquisition_channel=draft.acquisition_channel,
            key_features=draft.key_features,
            risks=draft.risks,
            source_signals=draft.source_signals,
            agent_notes=draft.agent_notes,
            human_comment=clean_comment,
            score=draft.score,
        )
        path = self._repository.save(card)
        return SavedIdeaResult(card=card, path=path)


class ListIdeasByStatusUseCase:
    """Return recent idea cards for a given status."""

    def __init__(self, *, repository: IdeaRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        status: IdeaStatus,
        limit: int = 5,
    ) -> Sequence[IdeaCard]:
        """Load recent idea cards for presentation."""

        return self._repository.list_by_status(status, limit=limit)

"""Use-cases for creating and browsing idea cards."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Sequence

from idea_factory.domain.ideation import (
    IDEATION_CREATIVE_ANGLES,
    IDEATION_DOMAIN_PROFILES,
    IdeationDomainProfile,
    clamp_idea_generation_count,
)
from idea_factory.domain.models import DecisionAction, IdeaCard, IdeaStatus, StructuredIdeaDraft
from idea_factory.domain.policies import status_for_decision
from idea_factory.domain.signals import MarketSignal
from idea_factory.services.ports import (
    AutonomousIdeationPort,
    ClockPort,
    IdGeneratorPort,
    IdeaRepositoryPort,
    LLMPort,
    SignalSamplerPort,
)


@dataclass(frozen=True, slots=True)
class SavedIdeaResult:
    """Result returned after persisting an idea card."""

    card: IdeaCard
    path: Path


@dataclass(frozen=True, slots=True)
class SavedIdeaBatchResult:
    """Result returned after persisting a batch of autonomous ideas."""

    generated_count: int
    cards: tuple[IdeaCard, ...]
    paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class ReviewedIdeaResult:
    """Result returned after moving an idea into a target bucket."""

    card: IdeaCard
    path: Path


@dataclass(frozen=True, slots=True)
class IdeaGenerationTask:
    """One parallel autonomous ideation request."""

    task_index: int
    domain_profile: IdeationDomainProfile
    creative_angle: str
    generation_context: str
    signals: tuple[MarketSignal, ...]


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


class GenerateAutonomousIdeasUseCase:
    """Generate structured inbox ideas across multiple domains."""

    def __init__(
        self,
        *,
        ideation_llm: AutonomousIdeationPort,
        repository: IdeaRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        signal_sampler: SignalSamplerPort | None = None,
        signals_per_domain: int = 6,
        max_parallel_requests: int = 6,
    ) -> None:
        self._ideation_llm = ideation_llm
        self._repository = repository
        self._clock = clock
        self._id_generator = id_generator
        self._signal_sampler = signal_sampler
        self._signals_per_domain = signals_per_domain
        self._max_parallel_requests = max(1, max_parallel_requests)

    def execute(
        self,
        *,
        requested_count: int,
        seed_context: str = "",
    ) -> SavedIdeaBatchResult:
        """Generate and persist inbox ideas.

        Args:
            requested_count: Desired idea count. Values are clamped to 1..100.
            seed_context: Optional extra guidance for the generator.

        Returns:
            Persisted cards and file paths.
        """

        target_count = clamp_idea_generation_count(requested_count)
        clean_seed = " ".join(seed_context.split())
        tasks = self._build_generation_tasks(target_count=target_count, seed_context=clean_seed)

        saved_cards: list[IdeaCard] = []
        saved_paths: list[Path] = []
        sequence_offset = 0
        drafts_by_index = self._generate_drafts(tasks)

        for task in tasks:
            draft = drafts_by_index[task.task_index]
            created_at = self._clock.now() + timedelta(microseconds=sequence_offset)
            sequence_offset += 1
            origin_context = self._build_origin_context(
                seed_context=task.generation_context,
                domain_name=task.domain_profile.name,
                creative_angle=task.creative_angle,
                signals=task.signals,
            )
            card = IdeaCard(
                idea_id=self._id_generator.new_id(created_at),
                status=IdeaStatus.INBOX,
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
                human_comment=origin_context,
                score=draft.score,
            )
            saved_cards.append(card)
            saved_paths.append(self._repository.save(card))

        return SavedIdeaBatchResult(
            generated_count=len(saved_cards),
            cards=tuple(saved_cards),
            paths=tuple(saved_paths),
        )

    def _build_generation_tasks(
        self,
        *,
        target_count: int,
        seed_context: str,
    ) -> list[IdeaGenerationTask]:
        tasks: list[IdeaGenerationTask] = []
        for task_index in range(target_count):
            domain_profile = IDEATION_DOMAIN_PROFILES[task_index % len(IDEATION_DOMAIN_PROFILES)]
            creative_angle = IDEATION_CREATIVE_ANGLES[task_index % len(IDEATION_CREATIVE_ANGLES)]
            signals = self._sample_signals(
                domain_profile=domain_profile,
                seed_context=seed_context,
            )
            generation_context = self._merge_seed_context(
                seed_context=seed_context,
                signals=signals,
            )
            tasks.append(
                IdeaGenerationTask(
                    task_index=task_index,
                    domain_profile=domain_profile,
                    creative_angle=creative_angle,
                    generation_context=generation_context,
                    signals=signals,
                )
            )
        return tasks

    def _generate_drafts(
        self,
        tasks: Sequence[IdeaGenerationTask],
    ) -> dict[int, StructuredIdeaDraft]:
        max_workers = min(len(tasks), self._max_parallel_requests)
        futures: dict[Future[StructuredIdeaDraft], int] = {}
        drafts_by_index: dict[int, StructuredIdeaDraft] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for task in tasks:
                future = executor.submit(self._generate_single_draft, task)
                futures[future] = task.task_index
            for future, task_index in futures.items():
                drafts_by_index[task_index] = future.result()
        return drafts_by_index

    def _generate_single_draft(self, task: IdeaGenerationTask) -> StructuredIdeaDraft:
        drafts = self._ideation_llm.generate_ideas(
            batch_size=1,
            seed_context=task.generation_context,
            domain_profile=task.domain_profile,
            creative_angle=task.creative_angle,
        )
        if not drafts:
            raise ValueError("Autonomous ideation returned no drafts.")
        return drafts[0]

    def _sample_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
    ) -> tuple[MarketSignal, ...]:
        if self._signal_sampler is None:
            return ()
        collected = self._signal_sampler.sample_signals(
            domain_profile=domain_profile,
            seed_context=seed_context,
            limit=self._signals_per_domain,
        )
        return tuple(collected)

    def _merge_seed_context(
        self,
        *,
        seed_context: str,
        signals: tuple[MarketSignal, ...],
    ) -> str:
        snippets = [seed_context] if seed_context else []
        if signals:
            snippets.append(self._format_signals_for_prompt(signals))
        return " ".join(part for part in snippets if part).strip()

    def _build_origin_context(
        self,
        *,
        seed_context: str,
        domain_name: str,
        creative_angle: str,
        signals: tuple[MarketSignal, ...],
    ) -> str:
        base_line = f"Autonomous batch for domain: {domain_name}. Angle: {creative_angle}"
        if signals:
            signal_lines = "; ".join(
                f"{signal.source}: {signal.title}" for signal in signals[:3]
            )
            base_line = f"{base_line} Signals: {signal_lines}"
        if not seed_context:
            return base_line
        return f"{base_line} Seed context: {seed_context}"

    def _format_signals_for_prompt(self, signals: tuple[MarketSignal, ...]) -> str:
        formatted = []
        for signal in signals[:4]:
            formatted.append(
                f"[{signal.source}] {signal.title}: {signal.summary}"
            )
        return " Market signals: " + " | ".join(formatted)


class MoveIdeaUseCase:
    """Move an idea into another status bucket."""

    def __init__(self, *, repository: IdeaRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        idea_id: str,
        target_status: IdeaStatus,
    ) -> ReviewedIdeaResult:
        """Move one idea to the chosen status.

        Args:
            idea_id: Existing idea id.
            target_status: Destination status.

        Returns:
            Updated card and new file path.

        Raises:
            FileNotFoundError: If the card is missing.
        """

        card = self._repository.get_by_id(idea_id)
        if card is None:
            raise FileNotFoundError(f"Idea '{idea_id}' was not found.")
        if card.status is target_status:
            raise ValueError("Идея уже находится в выбранной колонке.")

        path = self._repository.move_to_status(idea_id, status=target_status)
        updated_card = self._repository.get_by_id(idea_id)
        if updated_card is None:
            raise FileNotFoundError(f"Idea '{idea_id}' disappeared after move.")
        return ReviewedIdeaResult(card=updated_card, path=path)


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

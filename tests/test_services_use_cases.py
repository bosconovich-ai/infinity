"""Tests for service-layer idea creation flows."""

from __future__ import annotations

import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path

from idea_factory.domain.ideation import IdeationDomainProfile
from idea_factory.domain.models import DecisionAction, IdeaStatus, StructuredIdeaDraft
from idea_factory.domain.signals import MarketSignal
from idea_factory.infrastructure.file_repository import MarkdownIdeaRepository
from idea_factory.services.use_cases import (
    CreateIdeaFromCommentUseCase,
    GenerateAutonomousIdeasUseCase,
    ListIdeasByStatusUseCase,
    MoveIdeaUseCase,
)


class FakeLLM:
    """Return a stable draft for tests."""

    def __init__(self) -> None:
        self.batch_sizes: list[int] = []
        self._lock = threading.Lock()

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        return StructuredIdeaDraft(
            title="Refund Monitor",
            one_liner=f"Summary: {raw_comment}",
            problem="Returns are hard to inspect manually.",
            target_user="Shopify operators",
            why_subscription="Stores need continuous monitoring.",
            acquisition_channel="Shopify App Store",
            key_features=("Alerts", "Reports", "SKU drilldown"),
            risks=("Needs API access",),
            source_signals=("Manual comment",),
            agent_notes="Strong recurring workflow.",
            score=8.2,
        )

    def generate_ideas(
        self,
        *,
        batch_size: int,
        seed_context: str,
        domain_profile: IdeationDomainProfile,
        creative_angle: str,
    ) -> tuple[StructuredIdeaDraft, ...]:
        with self._lock:
            self.batch_sizes.append(batch_size)
        drafts = []
        for index in range(batch_size):
            drafts.append(
                StructuredIdeaDraft(
                    title=f"{domain_profile.name} Idea {index + 1}",
                    one_liner=f"{domain_profile.name} summary {index + 1}",
                    problem=f"{domain_profile.name} recurring pain",
                    target_user=domain_profile.audience,
                    why_subscription="Recurring workflow means recurring value.",
                    acquisition_channel=domain_profile.acquisition_channel,
                    key_features=("Alerts", "Weekly digest", "Dashboard"),
                    risks=("Needs validation",),
                    source_signals=(creative_angle, seed_context or "no-seed"),
                    agent_notes="Autonomous batch idea.",
                    score=7.5,
                )
            )
        return tuple(drafts)


class FixedClock:
    """Return a deterministic timestamp."""

    def now(self) -> datetime:
        return datetime(2026, 3, 2, 12, 30, 0, tzinfo=UTC)


class FixedIdGenerator:
    """Return a deterministic idea id."""

    def new_id(self, created_at: datetime) -> str:
        return created_at.strftime("idea_%Y%m%d_%H%M%S_%f")


class FakeSignalSampler:
    """Return deterministic cached market signals for tests."""

    def sample_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        return tuple(
            MarketSignal(
                source="reddit",
                query=f"{domain_profile.name} query",
                title=f"{domain_profile.name} complaint {index + 1}",
                summary="Operators complain about repeated manual work.",
                url=f"https://example.com/{index + 1}",
            )
            for index in range(limit)
        )


class CreateIdeaFromCommentUseCaseTests(unittest.TestCase):
    """Verify raw comments become persisted markdown cards."""

    def test_creates_and_saves_card_in_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            use_case = CreateIdeaFromCommentUseCase(
                llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )

            result = use_case.execute(
                raw_comment=" Track refund spikes for Shopify stores ",
                decision=DecisionAction.DO,
            )

            self.assertEqual(result.card.status, IdeaStatus.APPROVED)
            self.assertTrue(result.path.exists())
            self.assertIn("approved", str(result.path))
            self.assertEqual(result.card.human_comment, "Track refund spikes for Shopify stores")

    def test_rejects_empty_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            use_case = CreateIdeaFromCommentUseCase(
                llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )

            with self.assertRaises(ValueError):
                use_case.execute(raw_comment="   ", decision=DecisionAction.DONT)


class GenerateAutonomousIdeasUseCaseTests(unittest.TestCase):
    """Verify autonomous batches land in the inbox."""

    def test_generates_inbox_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            llm = FakeLLM()
            use_case = GenerateAutonomousIdeasUseCase(
                ideation_llm=llm,
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )

            result = use_case.execute(
                requested_count=3,
                seed_context="Prefer operational B2B SaaS",
            )

            self.assertEqual(result.generated_count, 3)
            self.assertEqual(len(result.cards), 3)
            self.assertTrue(all(card.status == IdeaStatus.INBOX for card in result.cards))
            self.assertTrue(all(path.exists() for path in result.paths))
            self.assertTrue(all("inbox" in str(path) for path in result.paths))
            self.assertEqual(llm.batch_sizes, [1, 1, 1])

    def test_caps_requested_count_at_100(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            use_case = GenerateAutonomousIdeasUseCase(
                ideation_llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )

            result = use_case.execute(requested_count=150)

            self.assertEqual(result.generated_count, 100)

    def test_includes_market_signal_context_when_sampler_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            use_case = GenerateAutonomousIdeasUseCase(
                ideation_llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
                signal_sampler=FakeSignalSampler(),
                signals_per_domain=2,
            )

            result = use_case.execute(requested_count=1, seed_context="Prefer SMB tools")

            self.assertIn("Signals:", result.cards[0].human_comment)
            self.assertIn("Market signals:", result.cards[0].human_comment)


class MoveIdeaUseCaseTests(unittest.TestCase):
    """Verify ideas can be moved between visible columns."""

    def test_moves_inbox_idea_to_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            generate_use_case = GenerateAutonomousIdeasUseCase(
                ideation_llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )
            batch_result = generate_use_case.execute(requested_count=1)

            move_use_case = MoveIdeaUseCase(repository=repository)
            result = move_use_case.execute(
                idea_id=batch_result.cards[0].idea_id,
                target_status=IdeaStatus.APPROVED,
            )

            self.assertEqual(result.card.status, IdeaStatus.APPROVED)
            self.assertIn("approved", str(result.path))
            self.assertIsNone(repository.get_by_id("missing-idea-id"))

    def test_moves_approved_idea_back_to_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            create_use_case = CreateIdeaFromCommentUseCase(
                llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )
            saved = create_use_case.execute(
                raw_comment="Track refund spikes for Shopify stores",
                decision=DecisionAction.DO,
            )

            move_use_case = MoveIdeaUseCase(repository=repository)
            result = move_use_case.execute(
                idea_id=saved.card.idea_id,
                target_status=IdeaStatus.INBOX,
            )

            self.assertEqual(result.card.status, IdeaStatus.INBOX)
            self.assertIn("inbox", str(result.path))

    def test_rejects_move_when_target_is_current_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            create_use_case = CreateIdeaFromCommentUseCase(
                llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )
            saved = create_use_case.execute(
                raw_comment="Track refund spikes for Shopify stores",
                decision=DecisionAction.DO,
            )

            move_use_case = MoveIdeaUseCase(repository=repository)
            with self.assertRaises(ValueError):
                move_use_case.execute(
                    idea_id=saved.card.idea_id,
                    target_status=IdeaStatus.APPROVED,
                )


class ListIdeasByStatusUseCaseTests(unittest.TestCase):
    """Verify repository-backed listing returns parsed cards."""

    def test_returns_empty_list_when_directory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            list_use_case = ListIdeasByStatusUseCase(repository=repository)

            cards = list_use_case.execute(status=IdeaStatus.APPROVED)

            self.assertEqual(cards, [])

    def test_returns_recent_cards_for_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MarkdownIdeaRepository(Path(temp_dir))
            create_use_case = CreateIdeaFromCommentUseCase(
                llm=FakeLLM(),
                repository=repository,
                clock=FixedClock(),
                id_generator=FixedIdGenerator(),
            )
            create_use_case.execute(
                raw_comment="Track refund spikes for Shopify stores",
                decision=DecisionAction.RETHINK,
            )

            list_use_case = ListIdeasByStatusUseCase(repository=repository)
            cards = list_use_case.execute(status=IdeaStatus.INCUBATING)

            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0].title, "Refund Monitor")
            self.assertEqual(cards[0].status, IdeaStatus.INCUBATING)

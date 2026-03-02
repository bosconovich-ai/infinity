"""Tests for service-layer idea creation flows."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from idea_factory.domain.models import DecisionAction, IdeaStatus, StructuredIdeaDraft
from idea_factory.infrastructure.file_repository import MarkdownIdeaRepository
from idea_factory.services.use_cases import CreateIdeaFromCommentUseCase, ListIdeasByStatusUseCase


class FakeLLM:
    """Return a stable draft for tests."""

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


class FixedClock:
    """Return a deterministic timestamp."""

    def now(self) -> datetime:
        return datetime(2026, 3, 2, 12, 30, 0, tzinfo=UTC)


class FixedIdGenerator:
    """Return a deterministic idea id."""

    def new_id(self, created_at: datetime) -> str:
        return "idea_20260302_123000"


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

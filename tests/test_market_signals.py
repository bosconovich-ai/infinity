"""Tests for live market signal collection adapters."""

from __future__ import annotations

import unittest

from idea_factory.domain.ideation import IDEATION_DOMAIN_PROFILES
from idea_factory.domain.signals import MarketSignal
from idea_factory.infrastructure.market_signals import CompositeMarketSignalCollector


class StubSource:
    """Return deterministic signals for collector tests."""

    def __init__(self, source_name: str) -> None:
        self._source_name = source_name

    def collect(self, *, query: str, limit: int) -> tuple[MarketSignal, ...]:
        return tuple(
            MarketSignal(
                source=self._source_name,
                query=query,
                title=f"{query} repeated pain {index + 1}",
                summary="Teams keep complaining about this manual workflow.",
                url=f"https://example.com/{self._source_name}/{index}",
            )
            for index in range(limit)
        )


class CompositeMarketSignalCollectorTests(unittest.TestCase):
    """Verify market signals are merged and capped cleanly."""

    def test_collects_and_caps_signals(self) -> None:
        collector = CompositeMarketSignalCollector(
            reddit=StubSource("reddit"),  # type: ignore[arg-type]
            github=StubSource("github"),  # type: ignore[arg-type]
        )

        signals = collector.collect_signals(
            domain_profile=IDEATION_DOMAIN_PROFILES[0],
            seed_context="prefer SMB",
            limit=4,
        )

        self.assertEqual(len(signals), 4)
        self.assertTrue(all(signal.title for signal in signals))

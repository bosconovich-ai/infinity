"""Tests for cached market signal storage and sampling."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from idea_factory.domain.ideation import IDEATION_DOMAIN_PROFILES
from idea_factory.domain.signals import MarketSignal
from idea_factory.infrastructure.signal_cache import (
    BackgroundSignalRefreshLoop,
    CachedMarketSignalSampler,
    JsonSignalCacheRepository,
)


class StubCollector:
    """Return deterministic signals for background refresh tests."""

    def collect_signals(
        self,
        *,
        domain_profile,
        seed_context: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        return tuple(
            MarketSignal(
                source="reddit",
                query=f"{domain_profile.name} query",
                title=f"{domain_profile.name} complaint {index + 1}",
                summary="Repeated manual workflow pain from operators.",
                url=f"https://example.com/{index + 1}",
            )
            for index in range(limit)
        )


class JsonSignalCacheRepositoryTests(unittest.TestCase):
    """Verify signal snapshots round-trip from disk."""

    def test_replaces_and_reads_domain_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonSignalCacheRepository(Path(temp_dir))
            domain = IDEATION_DOMAIN_PROFILES[0]

            saved_path = repository.replace_domain_signals(
                domain_profile=domain,
                signals=(
                    MarketSignal(
                        source="reddit",
                        query="shopify issue",
                        title="Refunds take too long",
                        summary="Merchants complain about repeated manual triage.",
                        url="https://example.com/refunds",
                    ),
                ),
            )

            loaded = repository.list_domain_signals(domain_profile=domain)

            self.assertTrue(saved_path.exists())
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].title, "Refunds take too long")


class CachedMarketSignalSamplerTests(unittest.TestCase):
    """Verify sampling pulls random entries from the cached pool."""

    def test_samples_from_cached_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonSignalCacheRepository(Path(temp_dir))
            domain = IDEATION_DOMAIN_PROFILES[0]
            repository.replace_domain_signals(
                domain_profile=domain,
                signals=tuple(
                    MarketSignal(
                        source="reddit",
                        query="shopify issue",
                        title=f"Signal {index}",
                        summary="Repeated manual workflow pain from operators.",
                        url=f"https://example.com/{index}",
                    )
                    for index in range(5)
                ),
            )
            sampler = CachedMarketSignalSampler(
                repository=repository,
                rng=random.Random(7),
            )

            sampled = sampler.sample_signals(
                domain_profile=domain,
                seed_context="",
                limit=3,
            )

            self.assertEqual(len(sampled), 3)
            self.assertEqual(len({signal.url for signal in sampled}), 3)


class BackgroundSignalRefreshLoopTests(unittest.TestCase):
    """Verify one refresh pass writes domain snapshots."""

    def test_refresh_once_persists_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonSignalCacheRepository(Path(temp_dir))
            loop = BackgroundSignalRefreshLoop(
                collector=StubCollector(),  # type: ignore[arg-type]
                repository=repository,
                refresh_limit_per_domain=2,
                interval_seconds=60,
            )

            loop.refresh_once()

            for domain in IDEATION_DOMAIN_PROFILES[:3]:
                self.assertEqual(len(repository.list_domain_signals(domain_profile=domain)), 2)

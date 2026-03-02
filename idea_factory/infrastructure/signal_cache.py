"""Persistent cache and background refresh loop for market signals."""

from __future__ import annotations

import json
import random
import threading
from pathlib import Path
from typing import Sequence

from idea_factory.domain.ideation import IDEATION_DOMAIN_PROFILES, IdeationDomainProfile
from idea_factory.domain.signals import MarketSignal
from idea_factory.infrastructure.market_signals import CompositeMarketSignalCollector


class JsonSignalCacheRepository:
    """Store per-domain market signals as JSON files."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def replace_domain_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        signals: Sequence[MarketSignal],
    ) -> Path:
        """Replace the cached signal snapshot for one domain."""

        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(domain_profile)
        payload = {
            "domain": domain_profile.name,
            "signals": [
                {
                    "source": signal.source,
                    "query": signal.query,
                    "title": signal.title,
                    "summary": signal.summary,
                    "url": signal.url,
                }
                for signal in signals
            ],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def list_domain_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
    ) -> tuple[MarketSignal, ...]:
        """Load cached signals for one domain."""

        path = self._path_for(domain_profile)
        if not path.exists():
            return ()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw_signals = payload["signals"]
            if not isinstance(raw_signals, list):
                raise TypeError("Expected signals list.")
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            return ()

        parsed: list[MarketSignal] = []
        for item in raw_signals:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(
                    MarketSignal(
                        source=str(item["source"]),
                        query=str(item["query"]),
                        title=str(item["title"]),
                        summary=str(item["summary"]),
                        url=str(item["url"]),
                    )
                )
            except KeyError:
                continue
        return tuple(parsed)

    def _path_for(self, domain_profile: IdeationDomainProfile) -> Path:
        slug = "".join(
            character.lower() if character.isalnum() else "-"
            for character in domain_profile.name
        ).strip("-")
        return self._root / f"{slug}.json"


class CachedMarketSignalSampler:
    """Sample cached signals for autonomous generation prompts."""

    def __init__(
        self,
        *,
        repository: JsonSignalCacheRepository,
        rng: random.Random | None = None,
    ) -> None:
        self._repository = repository
        self._rng = rng or random.Random()

    def sample_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        """Return a random slice of cached signals, biased by seed context."""

        cached = self._repository.list_domain_signals(domain_profile=domain_profile)
        if not cached:
            return ()

        preferred = self._filter_preferred(cached=cached, seed_context=seed_context)
        pool = preferred or list(cached)
        sample_size = min(limit, len(pool))
        if sample_size <= 0:
            return ()
        return tuple(self._rng.sample(pool, sample_size))

    def _filter_preferred(
        self,
        *,
        cached: Sequence[MarketSignal],
        seed_context: str,
    ) -> list[MarketSignal]:
        keywords = {
            token
            for token in "".join(
                character.lower() if character.isalnum() else " "
                for character in seed_context
            ).split()
            if len(token) >= 4
        }
        if not keywords:
            return []

        preferred: list[MarketSignal] = []
        for signal in cached:
            haystack = f"{signal.title} {signal.summary} {signal.query}".lower()
            if any(keyword in haystack for keyword in keywords):
                preferred.append(signal)
        return preferred


class BackgroundSignalRefreshLoop:
    """Refresh cached market signals on a daemon thread."""

    def __init__(
        self,
        *,
        collector: CompositeMarketSignalCollector,
        repository: JsonSignalCacheRepository,
        refresh_limit_per_domain: int,
        interval_seconds: int,
    ) -> None:
        self._collector = collector
        self._repository = repository
        self._refresh_limit_per_domain = refresh_limit_per_domain
        self._interval_seconds = interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the daemon refresh loop once per process."""

        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_forever,
            name="signal-refresh-loop",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the refresh loop."""

        self._stop_event.set()

    def refresh_once(self) -> None:
        """Refresh all domain snapshots immediately."""

        for domain_profile in IDEATION_DOMAIN_PROFILES:
            signals = self._collector.collect_signals(
                domain_profile=domain_profile,
                seed_context="",
                limit=self._refresh_limit_per_domain,
            )
            if not signals:
                continue
            self._repository.replace_domain_signals(
                domain_profile=domain_profile,
                signals=signals,
            )

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_once()
            if self._stop_event.wait(self._interval_seconds):
                break

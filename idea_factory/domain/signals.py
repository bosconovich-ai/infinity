"""Domain models for external market signals."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketSignal:
    """One externally collected market signal."""

    source: str
    query: str
    title: str
    summary: str
    url: str

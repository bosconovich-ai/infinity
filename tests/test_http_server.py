"""Tests for HTTP server environment configuration."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from idea_factory.interfaces.http_server import (
    build_signal_sampler,
    parse_generation_count,
    resolve_generation_parallel_requests,
    resolve_signal_refresh_interval_seconds,
    resolve_signal_refresh_limit_per_domain,
    resolve_signal_limit_per_domain,
    resolve_server_host,
    resolve_server_port,
)


class ResolveServerHostTests(unittest.TestCase):
    """Verify host binding stays predictable."""

    def test_uses_default_loopback_host(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_server_host(), "127.0.0.1")

    def test_uses_explicit_host_override(self) -> None:
        with patch.dict(os.environ, {"IDEA_FACTORY_HOST": "0.0.0.0"}, clear=True):
            self.assertEqual(resolve_server_host(), "0.0.0.0")


class ResolveServerPortTests(unittest.TestCase):
    """Verify port resolution supports container and local usage."""

    def test_defaults_to_8000(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_server_port(), 8000)

    def test_falls_back_to_app_port(self) -> None:
        with patch.dict(os.environ, {"APP_PORT": "9000"}, clear=True):
            self.assertEqual(resolve_server_port(), 9000)

    def test_prefers_explicit_idea_factory_port(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_PORT": "9000", "IDEA_FACTORY_PORT": "7000"},
            clear=True,
        ):
            self.assertEqual(resolve_server_port(), 7000)


class ParseGenerationCountTests(unittest.TestCase):
    """Verify batch size parsing stays resilient."""

    def test_returns_default_for_invalid_values(self) -> None:
        self.assertEqual(parse_generation_count("abc"), 12)

    def test_clamps_values_to_supported_range(self) -> None:
        self.assertEqual(parse_generation_count("250"), 100)
        self.assertEqual(parse_generation_count("-4"), 1)


class ResolveSignalLimitPerDomainTests(unittest.TestCase):
    """Verify scraping configuration stays bounded."""

    def test_uses_default_when_invalid(self) -> None:
        with patch.dict(os.environ, {"MARKET_SIGNAL_LIMIT_PER_DOMAIN": "abc"}, clear=True):
            self.assertEqual(resolve_signal_limit_per_domain(), 2)

    def test_clamps_limit_to_supported_range(self) -> None:
        with patch.dict(os.environ, {"MARKET_SIGNAL_LIMIT_PER_DOMAIN": "50"}, clear=True):
            self.assertEqual(resolve_signal_limit_per_domain(), 12)


class ResolveGenerationParallelRequestsTests(unittest.TestCase):
    """Verify autonomous request parallelism stays bounded."""

    def test_uses_default_when_invalid(self) -> None:
        with patch.dict(
            os.environ,
            {"AUTONOMOUS_GENERATION_PARALLEL_REQUESTS": "abc"},
            clear=True,
        ):
            self.assertEqual(resolve_generation_parallel_requests(), 8)

    def test_clamps_parallelism_to_supported_range(self) -> None:
        with patch.dict(
            os.environ,
            {"AUTONOMOUS_GENERATION_PARALLEL_REQUESTS": "100"},
            clear=True,
        ):
            self.assertEqual(resolve_generation_parallel_requests(), 24)


class ResolveSignalRefreshLimitPerDomainTests(unittest.TestCase):
    """Verify cache refresh batch sizing stays bounded."""

    def test_uses_default_when_invalid(self) -> None:
        with patch.dict(
            os.environ,
            {"MARKET_SIGNAL_REFRESH_LIMIT_PER_DOMAIN": "abc"},
            clear=True,
        ):
            self.assertEqual(resolve_signal_refresh_limit_per_domain(), 8)

    def test_clamps_limit_to_supported_range(self) -> None:
        with patch.dict(
            os.environ,
            {"MARKET_SIGNAL_REFRESH_LIMIT_PER_DOMAIN": "50"},
            clear=True,
        ):
            self.assertEqual(resolve_signal_refresh_limit_per_domain(), 24)


class ResolveSignalRefreshIntervalSecondsTests(unittest.TestCase):
    """Verify background refresh timing stays bounded."""

    def test_uses_default_when_invalid(self) -> None:
        with patch.dict(
            os.environ,
            {"MARKET_SIGNAL_REFRESH_INTERVAL_SECONDS": "abc"},
            clear=True,
        ):
            self.assertEqual(resolve_signal_refresh_interval_seconds(), 900)

    def test_clamps_interval_to_supported_range(self) -> None:
        with patch.dict(
            os.environ,
            {"MARKET_SIGNAL_REFRESH_INTERVAL_SECONDS": "5"},
            clear=True,
        ):
            self.assertEqual(resolve_signal_refresh_interval_seconds(), 60)


class BuildSignalSamplerTests(unittest.TestCase):
    """Verify cached scraping can be disabled explicitly."""

    def test_returns_none_when_scraping_is_disabled(self) -> None:
        with patch.dict(os.environ, {"ENABLE_MARKET_SCRAPING": "0"}, clear=True):
            self.assertIsNone(build_signal_sampler(storage_root=Path("ideas")))

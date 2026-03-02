"""Tests for HTTP server environment configuration."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from idea_factory.interfaces.http_server import resolve_server_host, resolve_server_port


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

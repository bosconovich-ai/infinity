"""Tests for pure domain policies."""

from __future__ import annotations

import unittest

from idea_factory.domain.ideation import clamp_idea_generation_count
from idea_factory.domain.models import DecisionAction, IdeaStatus
from idea_factory.domain.policies import slugify_title, status_for_decision


class StatusForDecisionTests(unittest.TestCase):
    """Verify reviewer actions map to the right storage status."""

    def test_maps_do_to_approved(self) -> None:
        self.assertEqual(status_for_decision(DecisionAction.DO), IdeaStatus.APPROVED)

    def test_maps_dont_to_rejected(self) -> None:
        self.assertEqual(status_for_decision(DecisionAction.DONT), IdeaStatus.REJECTED)

    def test_maps_rethink_to_incubating(self) -> None:
        self.assertEqual(status_for_decision(DecisionAction.RETHINK), IdeaStatus.INCUBATING)


class SlugifyTitleTests(unittest.TestCase):
    """Verify filesystem-safe slugs stay predictable."""

    def test_replaces_non_alphanumeric_characters(self) -> None:
        self.assertEqual(slugify_title("AI + Billing / Alerts"), "ai-billing-alerts")

    def test_falls_back_when_title_is_empty(self) -> None:
        self.assertEqual(slugify_title("   "), "idea")


class ClampIdeaGenerationCountTests(unittest.TestCase):
    """Verify autonomous generation count stays in the supported range."""

    def test_caps_count_at_100(self) -> None:
        self.assertEqual(clamp_idea_generation_count(250), 100)

    def test_raises_small_values_to_one(self) -> None:
        self.assertEqual(clamp_idea_generation_count(0), 1)

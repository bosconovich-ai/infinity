"""Markdown-backed idea repository."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from idea_factory.domain.models import IdeaCard, IdeaStatus
from idea_factory.domain.policies import slugify_title


class MarkdownIdeaRepository:
    """Persist idea cards as human-readable markdown files."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, card: IdeaCard) -> Path:
        """Persist an idea card to its status-specific directory.

        Args:
            card: Idea to persist.

        Returns:
            Path to the saved file.
        """

        directory = self._root / card.status.value
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{card.idea_id}-{slugify_title(card.title)}.md"
        path = directory / filename
        path.write_text(self._serialize(card), encoding="utf-8")
        return path

    def list_by_status(self, status: IdeaStatus, *, limit: int = 5) -> list[IdeaCard]:
        """Load recent cards from a status directory.

        Args:
            status: Directory to scan.
            limit: Maximum number of cards to return.

        Returns:
            Parsed idea cards, newest first.
        """

        directory = self._root / status.value
        if not directory.exists():
            return []

        paths = sorted(directory.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
        return [self._deserialize(path.read_text(encoding="utf-8")) for path in paths[:limit]]

    def _serialize(self, card: IdeaCard) -> str:
        metadata = {
            "id": card.idea_id,
            "status": card.status.value,
            "created_at": card.created_at.isoformat(),
            "title": card.title,
            "one_liner": card.one_liner,
            "problem": card.problem,
            "target_user": card.target_user,
            "why_subscription": card.why_subscription,
            "acquisition_channel": card.acquisition_channel,
            "key_features": list(card.key_features),
            "risks": list(card.risks),
            "source_signals": list(card.source_signals),
            "agent_notes": card.agent_notes,
            "human_comment": card.human_comment,
            "score": card.score,
        }

        lines = ["---"]
        for key, value in metadata.items():
            serialized = json.dumps(value, ensure_ascii=True)
            lines.append(f"{key}: {serialized}")
        lines.extend(
            [
                "---",
                "",
                f"# {card.title}",
                "",
                "## One-liner",
                card.one_liner,
                "",
                "## Why This Could Work",
                card.why_subscription,
                "",
                "## Target User",
                card.target_user,
                "",
                "## Problem",
                card.problem,
                "",
                "## Acquisition Channel",
                card.acquisition_channel,
                "",
                "## Key Features",
            ]
        )
        lines.extend(f"- {feature}" for feature in card.key_features)
        lines.extend(["", "## Risks"])
        lines.extend(f"- {risk}" for risk in card.risks)
        lines.extend(
            [
                "",
                "## Source Signals",
            ]
        )
        lines.extend(f"- {signal}" for signal in card.source_signals)
        lines.extend(
            [
                "",
                "## Agent Notes",
                card.agent_notes,
                "",
                "## Original Comment",
                card.human_comment,
                "",
            ]
        )
        return "\n".join(lines)

    def _deserialize(self, content: str) -> IdeaCard:
        metadata = self._parse_frontmatter(content)
        return IdeaCard(
            idea_id=str(metadata["id"]),
            status=IdeaStatus(str(metadata["status"])),
            created_at=datetime.fromisoformat(str(metadata["created_at"])),
            title=str(metadata["title"]),
            one_liner=str(metadata["one_liner"]),
            problem=str(metadata["problem"]),
            target_user=str(metadata["target_user"]),
            why_subscription=str(metadata["why_subscription"]),
            acquisition_channel=str(metadata["acquisition_channel"]),
            key_features=tuple(metadata["key_features"]),
            risks=tuple(metadata["risks"]),
            source_signals=tuple(metadata["source_signals"]),
            agent_notes=str(metadata["agent_notes"]),
            human_comment=str(metadata["human_comment"]),
            score=float(metadata["score"]) if metadata["score"] is not None else None,
        )

    def _parse_frontmatter(self, content: str) -> dict[str, object]:
        lines = content.splitlines()
        if len(lines) < 3 or lines[0].strip() != "---":
            raise ValueError("Missing frontmatter header.")

        metadata: dict[str, object] = {}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, _, raw_value = line.partition(":")
            metadata[key.strip()] = json.loads(raw_value.strip())
        return metadata

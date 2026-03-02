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

    def get_by_id(self, idea_id: str) -> IdeaCard | None:
        """Load a card by id across all status directories.

        Args:
            idea_id: Stable idea identifier.

        Returns:
            Parsed idea card if found, else None.
        """

        located_path = self._find_path_by_id(idea_id)
        if located_path is None:
            return None
        return self._deserialize(located_path.read_text(encoding="utf-8"))

    def move_to_status(self, idea_id: str, *, status: IdeaStatus) -> Path:
        """Move a saved idea card to another status bucket.

        Args:
            idea_id: Existing card identifier.
            status: Target status.

        Returns:
            New file path after the move.

        Raises:
            FileNotFoundError: If no card exists with the requested id.
        """

        located_path = self._find_path_by_id(idea_id)
        if located_path is None:
            raise FileNotFoundError(f"Idea '{idea_id}' was not found.")

        card = self._deserialize(located_path.read_text(encoding="utf-8"))
        updated_card = IdeaCard(
            idea_id=card.idea_id,
            status=status,
            created_at=card.created_at,
            title=card.title,
            one_liner=card.one_liner,
            problem=card.problem,
            target_user=card.target_user,
            why_subscription=card.why_subscription,
            acquisition_channel=card.acquisition_channel,
            key_features=card.key_features,
            risks=card.risks,
            source_signals=card.source_signals,
            agent_notes=card.agent_notes,
            human_comment=card.human_comment,
            score=card.score,
        )
        new_path = self.save(updated_card)
        if located_path != new_path and located_path.exists():
            located_path.unlink()
        return new_path

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
                "## Original Brief",
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

    def _find_path_by_id(self, idea_id: str) -> Path | None:
        for status in IdeaStatus:
            directory = self._root / status.value
            if not directory.exists():
                continue
            matches = sorted(directory.glob(f"{idea_id}-*.md"))
            if matches:
                return matches[0]
        return None

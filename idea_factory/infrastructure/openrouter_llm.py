"""LLM adapters for idea structuring."""

from __future__ import annotations

import json
import os
from urllib import error, request

from idea_factory.domain.models import StructuredIdeaDraft


class HeuristicIdeaStructurer:
    """Provide deterministic output when no remote LLM is configured."""

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        """Create a best-effort structured draft from plain text.

        Args:
            raw_comment: Raw user note.

        Returns:
            A normalized draft suitable for saving.
        """

        normalized = " ".join(raw_comment.split())
        title_words = normalized.split()[:6]
        title = " ".join(word.capitalize() for word in title_words) or "Untitled Idea"
        features = self._feature_hints(normalized)
        return StructuredIdeaDraft(
            title=title,
            one_liner=normalized,
            problem=normalized,
            target_user="Needs manual refinement based on the original comment.",
            why_subscription=(
                "Recurring value is plausible if the workflow happens regularly, "
                "but this still needs market validation."
            ),
            acquisition_channel="Validate SEO, directories, or ecosystem marketplaces.",
            key_features=tuple(features),
            risks=(
                "Problem severity may be overstated in the original note.",
                "Subscription value is not yet validated.",
                "Further competitor research is still needed.",
            ),
            source_signals=("Manual comment",),
            agent_notes=(
                "Generated without OpenRouter. Review and refine before handing "
                "this brief to Codex for implementation."
            ),
            score=None,
        )

    def _feature_hints(self, raw_comment: str) -> list[str]:
        phrases = [chunk.strip(" ,.") for chunk in raw_comment.split(",") if chunk.strip(" ,.")]
        if not phrases:
            return [
                "Capture the core workflow from the original comment.",
                "Clarify the primary user outcome.",
                "Define one recurring feature that supports subscriptions.",
            ]
        features = [f"Support: {phrase}" for phrase in phrases[:3]]
        while len(features) < 3:
            features.append("Refine the MVP scope before development.")
        return features


class OpenRouterIdeaStructurer:
    """Use OpenRouter to turn project comments into structured drafts."""

    _API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "qwen/qwen3.5-397b-a17b",
        fallback: HeuristicIdeaStructurer | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback = fallback or HeuristicIdeaStructurer()
        self._timeout_seconds = timeout_seconds

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        """Request a structured idea card from OpenRouter.

        Args:
            raw_comment: Raw project note from the user.

        Returns:
            Parsed idea draft. Falls back to local heuristics when the remote
            request fails or returns malformed JSON.
        """

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You structure startup project ideas. Return only JSON with the "
                        "keys: title, one_liner, problem, target_user, "
                        "why_subscription, acquisition_channel, key_features, "
                        "risks, source_signals, agent_notes, score. "
                        "Use arrays for key_features, risks, source_signals. "
                        "Keep output concise and practical."
                    ),
                },
                {
                    "role": "user",
                    "content": raw_comment,
                },
            ],
        }
        request_data = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self._API_URL,
            data=request_data,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://local.idea.factory",
                "X-Title": "idea-factory",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return self._fallback.structure_comment(raw_comment)

        content = self._extract_content(response_payload)
        if content is None:
            return self._fallback.structure_comment(raw_comment)

        try:
            parsed = json.loads(self._extract_json_object(content))
            return StructuredIdeaDraft(
                title=self._clean_text(parsed["title"]),
                one_liner=self._clean_text(parsed["one_liner"]),
                problem=self._clean_text(parsed["problem"]),
                target_user=self._clean_text(parsed["target_user"]),
                why_subscription=self._clean_text(parsed["why_subscription"]),
                acquisition_channel=self._clean_text(parsed["acquisition_channel"]),
                key_features=self._normalize_sequence(parsed["key_features"]),
                risks=self._normalize_sequence(parsed["risks"]),
                source_signals=self._normalize_sequence(parsed["source_signals"]),
                agent_notes=self._clean_text(parsed["agent_notes"]),
                score=self._normalize_score(parsed.get("score")),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._fallback.structure_comment(raw_comment)

    def _extract_content(self, payload: dict[str, object]) -> str | None:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first = choices[0]
        if not isinstance(first, dict):
            return None

        message = first.get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        return content if isinstance(content, str) else None

    def _extract_json_object(self, content: str) -> str:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("JSON object not found.")
        return content[start : end + 1]

    def _clean_text(self, value: object) -> str:
        return " ".join(str(value).split())

    def _normalize_sequence(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise TypeError("Expected list value.")
        normalized_items = []
        for item in value:
            clean_item = self._clean_text(item)
            if clean_item:
                normalized_items.append(clean_item)
        return tuple(normalized_items)

    def _normalize_score(self, value: object) -> float | None:
        if value in (None, ""):
            return None
        numeric = float(value)
        return max(0.0, min(10.0, numeric))


def build_default_structurer() -> HeuristicIdeaStructurer | OpenRouterIdeaStructurer:
    """Build the default LLM adapter from environment variables."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.5-397b-a17b")
    if not api_key:
        return HeuristicIdeaStructurer()
    return OpenRouterIdeaStructurer(api_key=api_key, model=model)

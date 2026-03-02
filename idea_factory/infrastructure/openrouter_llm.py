"""LLM adapters for idea structuring."""

from __future__ import annotations

import json
import os
from urllib import error, request

from idea_factory.domain.ideation import IdeationDomainProfile
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
        title = " ".join(word.capitalize() for word in title_words) or "Идея Без Названия"
        features = self._feature_hints(normalized)
        return StructuredIdeaDraft(
            title=title,
            one_liner=(
                f"{normalized} Эта идея лучше всего подходит для небольших бизнесов "
                "или частных специалистов, которым нужен понятный self-serve инструмент. "
                "Ценность должна быть заметна за короткий срок без длительного внедрения."
            ),
            problem=(
                f"{normalized} Сейчас этот сценарий, вероятно, решается вручную или через "
                "неудобную связку инструментов, из-за чего теряются время и деньги. "
                "Если сделать решение простым и узким, его можно продавать без длинных продаж."
            ),
            target_user=(
                "Небольшие бизнесы, индивидуальные предприниматели и частные специалисты, "
                "которым нужна быстрая ценность без сложных корпоративных закупок."
            ),
            why_subscription=(
                "Подписка выглядит возможной, если этот сценарий повторяется регулярно и "
                "помогает экономить время или снижать потери каждую неделю. "
                "Для малого бизнеса это должно окупаться без долгого согласования бюджета."
            ),
            acquisition_channel=(
                "Проверь SEO, каталоги интеграций, маркетплейсы экосистем и сообщества "
                "малого бизнеса, где решение можно купить без звонка."
            ),
            key_features=tuple(features),
            risks=(
                "Сила боли может быть завышена в исходной заметке.",
                "Подписочная ценность пока не подтверждена.",
                "Нужно дополнительное исследование конкурентов.",
            ),
            source_signals=("Ручной комментарий",),
            agent_notes=(
                "Сгенерировано без OpenRouter. Перед передачей в Codex стоит "
                "проверить и доработать этот бриф."
            ),
            score=None,
        )

    def generate_ideas(
        self,
        *,
        batch_size: int,
        seed_context: str,
        domain_profile: IdeationDomainProfile,
        creative_angle: str,
    ) -> tuple[StructuredIdeaDraft, ...]:
        """Generate deterministic inbox ideas without a remote model.

        Args:
            batch_size: Number of ideas to generate.
            seed_context: Optional operator guidance.
            domain_profile: Domain focus for the current batch.
            creative_angle: Prompt mutation hint.

        Returns:
            Deterministic idea drafts.
        """

        theme_pool = (
            "мониторинг",
            "алерты",
            "прогнозирование",
            "сверка",
            "аудит",
            "удержание",
            "восстановление",
            "отчётность",
        )
        outcome_pool = (
            "снижать потери в выручке",
            "сокращать ручную проверку",
            "раньше ловить аномалии",
            "улучшать еженедельные решения",
            "повышать удержание",
            "усиливать операционную дисциплину",
        )
        context_suffix = f" Контекст: {seed_context}" if seed_context else ""

        drafts: list[StructuredIdeaDraft] = []
        for index in range(batch_size):
            theme = theme_pool[index % len(theme_pool)]
            outcome = outcome_pool[index % len(outcome_pool)]
            title = f"{domain_profile.name}: {theme.title()} {index + 1}"
            drafts.append(
                StructuredIdeaDraft(
                    title=title,
                    one_liner=(
                        f"Self-serve SaaS для небольших бизнесов и частных специалистов в сегменте "
                        f"'{domain_profile.name}', который использует {theme}, чтобы {outcome}. "
                        "Продукт должен запускаться быстро, без длинного внедрения и без продаж через созвоны. "
                        f"Лучший сценарий входа: понятный MVP с узкой пользой для {domain_profile.audience}."
                    ),
                    problem=(
                        f"{domain_profile.audience} постоянно вручную решают задачи вокруг "
                        f"{domain_profile.recurring_value}, из-за чего процесс становится медленным и ошибочным. "
                        "Небольшим командам обычно не хватает отдельного специалиста на такую рутину, "
                        "поэтому они охотнее покупают простой сервис с быстрой отдачей."
                    ),
                    target_user=(
                        f"Небольшие бизнесы, маленькие команды и частные специалисты из сегмента: "
                        f"{domain_profile.audience}. Крупные корпоративные закупки и enterprise-внедрение "
                        "не являются целевым сценарием."
                    ),
                    why_subscription=(
                        f"Сценарий повторяется постоянно, и команды готовы платить за то, чтобы {outcome} "
                        "без найма дополнительных людей. Для малого бизнеса это должно быть недорогое, "
                        "понятное решение с регулярной практической пользой."
                    ),
                    acquisition_channel=domain_profile.acquisition_channel,
                    key_features=(
                        f"Автоматизированный модуль {theme} под {domain_profile.name}",
                        "Регулярные email- или Slack-сводки с понятными действиями",
                        "Пороговые алерты с объяснением недельных изменений",
                        "Небольшая, но заметная фишка для удержания: шаблоны, авто-рекомендации или быстрые действия в один клик",
                    ),
                    risks=(
                        domain_profile.constraints,
                        "Ценность нужно подтвердить через реальные интервью с пользователями.",
                        "Слишком тяжёлая интеграция может убить активацию.",
                    ),
                    source_signals=(
                        f"Автономная генерация: {domain_profile.name}",
                        f"Угол генерации: {creative_angle}",
                        f"Эвристический режим.{context_suffix}".strip(),
                    ),
                    agent_notes=(
                        f"Сгенерировано эвристически для домена {domain_profile.name}. "
                        f"Угол: {creative_angle}.{context_suffix}"
                    ),
                    score=float(6 + (index % 4)),
                )
            )
        return tuple(drafts)

    def _feature_hints(self, raw_comment: str) -> list[str]:
        phrases = [chunk.strip(" ,.") for chunk in raw_comment.split(",") if chunk.strip(" ,.")]
        if not phrases:
            return [
                "Зафиксировать основной рабочий сценарий из комментария.",
                "Уточнить главный результат для пользователя.",
                "Добавить повторяющуюся функцию, которая поддерживает подписку.",
            ]
        features = [f"Поддержать сценарий: {phrase}" for phrase in phrases[:3]]
        while len(features) < 3:
            features.append("Уточнить границы MVP перед разработкой.")
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
        structure_temperature: float = 0.7,
        ideation_temperature: float = 1.15,
        timeout_seconds: int = 20,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback = fallback or HeuristicIdeaStructurer()
        self._structure_temperature = structure_temperature
        self._ideation_temperature = ideation_temperature
        self._timeout_seconds = timeout_seconds

    def structure_comment(self, raw_comment: str) -> StructuredIdeaDraft:
        """Request a structured idea card from OpenRouter.

        Args:
            raw_comment: Raw project note from the user.

        Returns:
            Parsed idea draft. Falls back to local heuristics when the remote
            request fails or returns malformed JSON.
        """
        response_payload = self._request_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You structure startup project ideas. Return only JSON with the "
                        "keys: title, one_liner, problem, target_user, "
                        "why_subscription, acquisition_channel, key_features, "
                        "risks, source_signals, agent_notes, score. "
                        "Use arrays for key_features, risks, source_signals. "
                        "Set score to a number from 1 to 10. "
                        "Keep output practical. "
                        "Write every field value in Russian. "
                        "Make one_liner and problem detailed enough to read like 2-3 full sentences, "
                        "not a short fragment. "
                        "Explicitly set target_user to small businesses, solo operators, or private individuals "
                        "when that fits; avoid enterprise buyers by default. "
                        "Include at least 3 specific product features, with at least one small but memorable UX/product hook."
                    ),
                },
                {
                    "role": "user",
                    "content": raw_comment,
                },
            ],
            temperature=self._structure_temperature,
        )
        if response_payload is None:
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

    def generate_ideas(
        self,
        *,
        batch_size: int,
        seed_context: str,
        domain_profile: IdeationDomainProfile,
        creative_angle: str,
    ) -> tuple[StructuredIdeaDraft, ...]:
        """Generate a batch of ideas for one domain via OpenRouter.

        Args:
            batch_size: Number of ideas requested.
            seed_context: Optional operator guidance.
            domain_profile: Domain focus for this batch.
            creative_angle: Current prompt mutation instruction.

        Returns:
            Parsed drafts. Missing or invalid responses fall back to heuristics.
        """

        user_prompt = self._build_generation_prompt(
            batch_size=batch_size,
            seed_context=seed_context,
            domain_profile=domain_profile,
            creative_angle=creative_angle,
        )
        response_payload = self._request_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an autonomous startup idea factory for micro-SaaS. "
                        "Return only JSON with a top-level object containing the key "
                        "'ideas'. The value must be an array. Each item must contain: "
                        "title, one_liner, problem, target_user, why_subscription, "
                        "acquisition_channel, key_features, risks, source_signals, "
                        "agent_notes, score. Use arrays for key_features, risks, "
                        "source_signals. Score must be a number from 1 to 10. "
                        "Generate ideas that can be sold self-serve and do not require "
                        "manual outbound sales. Write every field value in Russian. "
                        "Make one_liner and problem read as 2-3 full sentences each. "
                        "Set target_user explicitly and bias it toward small businesses, solo operators, "
                        "and private individuals. Avoid enterprise-heavy ideas by default. "
                        "Every idea must include at least 3 specific features and at least one small memorable hook."
                    ),
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=self._ideation_temperature,
        )
        if response_payload is None:
            return self._fallback.generate_ideas(
                batch_size=batch_size,
                seed_context=seed_context,
                domain_profile=domain_profile,
                creative_angle=creative_angle,
            )

        content = self._extract_content(response_payload)
        if content is None:
            return self._fallback.generate_ideas(
                batch_size=batch_size,
                seed_context=seed_context,
                domain_profile=domain_profile,
                creative_angle=creative_angle,
            )

        try:
            parsed = json.loads(self._extract_json_object(content))
            ideas = parsed["ideas"]
            if not isinstance(ideas, list):
                raise TypeError("Expected list of ideas.")
            drafts: list[StructuredIdeaDraft] = []
            for item in ideas[:batch_size]:
                if not isinstance(item, dict):
                    raise TypeError("Expected dict idea payload.")
                drafts.append(self._parse_draft(item))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._fallback.generate_ideas(
                batch_size=batch_size,
                seed_context=seed_context,
                domain_profile=domain_profile,
                creative_angle=creative_angle,
            )

        if len(drafts) < batch_size:
            fallback_drafts = self._fallback.generate_ideas(
                batch_size=batch_size - len(drafts),
                seed_context=seed_context,
                domain_profile=domain_profile,
                creative_angle=creative_angle,
            )
            drafts.extend(fallback_drafts)
        return tuple(drafts)

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

    def _parse_draft(self, payload: dict[str, object]) -> StructuredIdeaDraft:
        return StructuredIdeaDraft(
            title=self._clean_text(payload["title"]),
            one_liner=self._clean_text(payload["one_liner"]),
            problem=self._clean_text(payload["problem"]),
            target_user=self._clean_text(payload["target_user"]),
            why_subscription=self._clean_text(payload["why_subscription"]),
            acquisition_channel=self._clean_text(payload["acquisition_channel"]),
            key_features=self._normalize_sequence(payload["key_features"]),
            risks=self._normalize_sequence(payload["risks"]),
            source_signals=self._normalize_sequence(payload["source_signals"]),
            agent_notes=self._clean_text(payload["agent_notes"]),
            score=self._normalize_score(payload.get("score")),
        )

    def _build_generation_prompt(
        self,
        *,
        batch_size: int,
        seed_context: str,
        domain_profile: IdeationDomainProfile,
        creative_angle: str,
    ) -> str:
        return (
            f"Generate {batch_size} distinct startup ideas.\n"
            f"Domain: {domain_profile.name}\n"
            f"Audience: {domain_profile.audience}\n"
            f"Recurring value: {domain_profile.recurring_value}\n"
            f"Primary acquisition channel: {domain_profile.acquisition_channel}\n"
            f"Constraints: {domain_profile.constraints}\n"
            f"Creative angle: {creative_angle}\n"
            "Rules:\n"
            "- Ideas must be subscription-friendly micro-SaaS or narrow vertical SaaS.\n"
            "- Prioritize self-serve acquisition and recurring workflows.\n"
            "- Prioritize small businesses, solo operators, and private individuals as the default buyer.\n"
            "- Avoid enterprise sales, large corporate procurement, and heavyweight onboarding.\n"
            "- Avoid agency work, consulting-heavy onboarding, and generic AI wrappers.\n"
            "- Keep ideas different from each other inside this batch.\n"
            "- one_liner must be 2-3 complete sentences, not a short slogan.\n"
            "- problem must be 2-3 complete sentences with concrete pain and why it matters.\n"
            "- target_user must explicitly name who we plan to sell to, and it should usually be SMB or individuals.\n"
            "- key_features must contain concrete, useful product features plus at least one small memorable hook.\n"
            "- Give each idea a realistic score from 1 to 10 based on market strength.\n"
            "- Write the resulting ideas in Russian.\n"
            f"Optional seed context: {seed_context or 'None'}"
        )

    def _request_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> dict[str, object] | None:
        payload = {
            "model": self._model,
            "temperature": temperature,
            "messages": messages,
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
                return json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return None


def build_default_structurer() -> HeuristicIdeaStructurer | OpenRouterIdeaStructurer:
    """Build the default LLM adapter from environment variables."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.5-397b-a17b")
    ideation_temperature = float(os.getenv("OPENROUTER_IDEATION_TEMPERATURE", "1.15"))
    if not api_key:
        return HeuristicIdeaStructurer()
    return OpenRouterIdeaStructurer(
        api_key=api_key,
        model=model,
        ideation_temperature=ideation_temperature,
    )

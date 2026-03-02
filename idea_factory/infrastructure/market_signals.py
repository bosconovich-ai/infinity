"""External market signal collectors backed by public web endpoints."""

from __future__ import annotations

import json
import os
from typing import Iterable
from urllib import error, parse, request

from idea_factory.domain.ideation import IdeationDomainProfile
from idea_factory.domain.signals import MarketSignal


class RedditSignalSource:
    """Collect market pain signals from Reddit search results."""

    _BASE_URL = "https://www.reddit.com/search.json"

    def collect(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        payload = self._fetch_json(
            f"{self._BASE_URL}?{parse.urlencode({'q': query, 'sort': 'top', 't': 'month', 'limit': str(limit)})}"
        )
        if payload is None:
            return ()

        try:
            children = payload["data"]["children"]
            if not isinstance(children, list):
                raise TypeError("Expected Reddit children list.")
        except (KeyError, TypeError):
            return ()

        signals: list[MarketSignal] = []
        for child in children[:limit]:
            try:
                data = child["data"]
                title = self._clean_text(data["title"])
                body = self._clean_text(data.get("selftext", "")) or "Reddit discussion about a repeated problem."
                permalink = str(data["permalink"])
            except (KeyError, TypeError):
                continue

            if not title:
                continue
            signals.append(
                MarketSignal(
                    source="reddit",
                    query=query,
                    title=title,
                    summary=body[:280],
                    url=f"https://www.reddit.com{permalink}",
                )
            )
        return tuple(signals)

    def _fetch_json(self, url: str) -> dict[str, object] | None:
        http_request = request.Request(
            url,
            headers={"User-Agent": "idea-factory/0.1 (+https://local.idea.factory)"},
        )
        try:
            with request.urlopen(http_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _clean_text(self, value: object) -> str:
        return " ".join(str(value).split())


class GitHubIssueSignalSource:
    """Collect signals from public GitHub issue search."""

    _BASE_URL = "https://api.github.com/search/issues"

    def __init__(self, *, token: str | None = None) -> None:
        self._token = token

    def collect(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        issue_query = f"{query} is:issue state:open"
        url = f"{self._BASE_URL}?{parse.urlencode({'q': issue_query, 'per_page': str(limit), 'sort': 'comments', 'order': 'desc'})}"
        payload = self._fetch_json(url)
        if payload is None:
            return ()

        try:
            items = payload["items"]
            if not isinstance(items, list):
                raise TypeError("Expected GitHub items list.")
        except (KeyError, TypeError):
            return ()

        signals: list[MarketSignal] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""))
            summary = self._clean_text(item.get("body", "")) or "GitHub issue describing an operational pain point."
            url_value = str(item.get("html_url", ""))
            if not title or not url_value:
                continue
            signals.append(
                MarketSignal(
                    source="github_issues",
                    query=issue_query,
                    title=title,
                    summary=summary[:280],
                    url=url_value,
                )
            )
        return tuple(signals)

    def _fetch_json(self, url: str) -> dict[str, object] | None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "idea-factory/0.1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        http_request = request.Request(url, headers=headers)
        try:
            with request.urlopen(http_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _clean_text(self, value: object) -> str:
        return " ".join(str(value).split())


class CompositeMarketSignalCollector:
    """Collect and deduplicate market signals across sources."""

    def __init__(
        self,
        *,
        reddit: RedditSignalSource | None = None,
        github: GitHubIssueSignalSource | None = None,
    ) -> None:
        self._reddit = reddit or RedditSignalSource()
        self._github = github or GitHubIssueSignalSource(token=os.getenv("GITHUB_TOKEN"))

    def collect_signals(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
        limit: int,
    ) -> tuple[MarketSignal, ...]:
        queries = self._build_queries(domain_profile=domain_profile, seed_context=seed_context)
        per_source_limit = max(1, min(5, limit))

        collected: list[MarketSignal] = []
        for query in queries:
            collected.extend(self._reddit.collect(query=query, limit=per_source_limit))
            collected.extend(self._github.collect(query=query, limit=per_source_limit))

        deduplicated = self._deduplicate(collected)
        return tuple(deduplicated[:limit])

    def _build_queries(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
    ) -> tuple[str, ...]:
        keywords = self._keywords_for(domain_profile=domain_profile, seed_context=seed_context)
        keyword_phrase = " ".join(keywords[:4]) or domain_profile.name
        if seed_context:
            seed_keywords = [
                token
                for token in self._keywords_for(domain_profile=domain_profile, seed_context=seed_context)
                if token in seed_context.lower()
            ]
            seed_phrase = " ".join(seed_keywords[:3]) or seed_context
            return (
                f"{seed_phrase} {keyword_phrase} manual workflow",
                f"{seed_phrase} {keyword_phrase} recurring issue",
                f"{seed_phrase} {domain_profile.name}",
            )
        return (
            f"\"{domain_profile.name}\" SaaS problem",
            f"{keyword_phrase} manual workflow",
            f"{keyword_phrase} recurring issue",
        )

    def _deduplicate(self, signals: Iterable[MarketSignal]) -> list[MarketSignal]:
        relevant = [
            signal
            for signal in signals
            if self._is_relevant(signal)
        ]
        seen: set[str] = set()
        unique: list[MarketSignal] = []
        for signal in relevant:
            fingerprint = f"{signal.source}|{signal.url}|{signal.title.lower()}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            unique.append(signal)
        return unique

    def _keywords_for(
        self,
        *,
        domain_profile: IdeationDomainProfile,
        seed_context: str,
    ) -> list[str]:
        raw_text = " ".join(
            [
                domain_profile.name,
                domain_profile.recurring_value,
                seed_context,
            ]
        ).lower()
        stop_words = {
            "and",
            "the",
            "for",
            "with",
            "that",
            "into",
            "this",
            "from",
            "have",
            "your",
            "teams",
            "small",
            "smb",
        }
        keywords: list[str] = []
        for token in raw_text.replace("-", " ").replace(",", " ").split():
            clean = "".join(char for char in token if char.isalnum())
            if len(clean) < 4 or clean in stop_words or clean in keywords:
                continue
            keywords.append(clean)
        return keywords

    def _is_relevant(self, signal: MarketSignal) -> bool:
        domain_text = f"{signal.title} {signal.summary}".lower()
        generic_terms = {
            "saas",
            "software",
            "manual",
            "workflow",
            "issue",
            "issues",
            "problem",
            "problems",
            "recurring",
        }
        query_keywords = [
            token
            for token in signal.query.lower().replace('"', " ").split()
            if len(token) >= 4 and token not in generic_terms
        ]
        if not query_keywords:
            return False
        return any(token in domain_text for token in query_keywords[:4])

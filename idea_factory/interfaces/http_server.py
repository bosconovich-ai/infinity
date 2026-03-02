"""Tiny HTTP interface with idea intake and inbox review actions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from idea_factory.domain.models import DecisionAction, IdeaStatus
from idea_factory.infrastructure.file_repository import MarkdownIdeaRepository
from idea_factory.infrastructure.market_signals import CompositeMarketSignalCollector
from idea_factory.infrastructure.openrouter_llm import build_default_structurer
from idea_factory.infrastructure.runtime import SystemClock, TimestampIdGenerator
from idea_factory.interfaces.page_renderer import render_page
from idea_factory.services.use_cases import (
    CreateIdeaFromCommentUseCase,
    GenerateAutonomousIdeasUseCase,
    ListIdeasByStatusUseCase,
    ReviewInboxIdeaUseCase,
)


@dataclass(frozen=True, slots=True)
class AppContext:
    """Container for interface dependencies."""

    create_idea: CreateIdeaFromCommentUseCase
    generate_autonomous_ideas: GenerateAutonomousIdeasUseCase
    list_ideas: ListIdeasByStatusUseCase
    review_inbox_idea: ReviewInboxIdeaUseCase


class IdeaFactoryHandler(BaseHTTPRequestHandler):
    """Render the form and handle idea submissions."""

    context: AppContext

    def do_GET(self) -> None:
        """Render the main HTML page."""

        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_text("ok")
            return

        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        params = parse_qs(parsed.query)
        message = params.get("message", [""])[0]
        self._send_html(self._render_page(message=message))

    def do_POST(self) -> None:
        """Handle project comment submission."""

        parsed = urlparse(self.path)
        if parsed.path not in {"/submit", "/generate", "/review"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(raw_body)
        try:
            if parsed.path == "/submit":
                status_message = self._handle_manual_submission(form)
            elif parsed.path == "/generate":
                status_message = self._handle_autonomous_generation(form)
            else:
                status_message = self._handle_review_submission(form)
        except Exception as exc:
            status_message = f"Ошибка во время обработки: {exc}"

        self._redirect_with_message(status_message)

    def log_message(self, format: str, *args: object) -> None:
        """Keep request logging concise."""

        return

    def _redirect_with_message(self, message: str) -> None:
        quoted = quote(message, safe="")
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?message={quoted}")
        self.end_headers()

    def _handle_manual_submission(self, form: dict[str, list[str]]) -> str:
        comment = form.get("comment", [""])[0]
        decision_value = form.get("decision", [""])[0]

        try:
            decision = DecisionAction(decision_value)
            result = self.context.create_idea.execute(raw_comment=comment, decision=decision)
            return (
                f"Saved '{result.card.title}' to "
                f"{result.card.status.value}/{result.path.name}"
            )
        except ValueError as exc:
            return str(exc)

    def _handle_autonomous_generation(self, form: dict[str, list[str]]) -> str:
        requested_count = parse_generation_count(form.get("count", ["12"])[0])
        seed_context = form.get("seed_context", [""])[0]
        result = self.context.generate_autonomous_ideas.execute(
            requested_count=requested_count,
            seed_context=seed_context,
        )
        return f"Generated {result.generated_count} inbox ideas."

    def _handle_review_submission(self, form: dict[str, list[str]]) -> str:
        idea_id = form.get("idea_id", [""])[0]
        decision_value = form.get("decision", [""])[0]
        if not idea_id:
            return "Не удалось определить идею для разбора."

        decision = DecisionAction(decision_value)
        result = self.context.review_inbox_idea.execute(idea_id=idea_id, decision=decision)
        return (
            f"Идея '{result.card.title}' перенесена в "
            f"{status_label(result.card.status)}."
        )

    def _send_html(self, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _render_page(self, *, message: str) -> str:
        inbox = self.context.list_ideas.execute(status=IdeaStatus.INBOX, limit=12)
        approved = self.context.list_ideas.execute(status=IdeaStatus.APPROVED, limit=5)
        rejected = self.context.list_ideas.execute(status=IdeaStatus.REJECTED, limit=5)
        incubating = self.context.list_ideas.execute(status=IdeaStatus.INCUBATING, limit=5)
        return render_page(
            message=message,
            inbox=inbox,
            approved=approved,
            incubating=incubating,
            rejected=rejected,
        )


def build_app_context() -> AppContext:
    """Wire default dependencies for the HTTP interface."""

    storage_root = Path(os.getenv("IDEA_STORAGE_ROOT", "ideas"))
    repository = MarkdownIdeaRepository(storage_root)
    structurer = build_default_structurer()
    create_idea = CreateIdeaFromCommentUseCase(
        llm=structurer,
        repository=repository,
        clock=SystemClock(),
        id_generator=TimestampIdGenerator(),
    )
    signal_collector = build_signal_collector()
    generate_autonomous_ideas = GenerateAutonomousIdeasUseCase(
        ideation_llm=structurer,
        repository=repository,
        clock=SystemClock(),
        id_generator=TimestampIdGenerator(),
        signal_collector=signal_collector,
        signals_per_domain=resolve_signal_limit_per_domain(),
    )
    list_ideas = ListIdeasByStatusUseCase(repository=repository)
    review_inbox_idea = ReviewInboxIdeaUseCase(repository=repository)
    return AppContext(
        create_idea=create_idea,
        generate_autonomous_ideas=generate_autonomous_ideas,
        list_ideas=list_ideas,
        review_inbox_idea=review_inbox_idea,
    )


def resolve_server_host() -> str:
    """Resolve the HTTP bind host from environment variables."""

    return os.getenv("IDEA_FACTORY_HOST", "127.0.0.1")


def resolve_server_port() -> int:
    """Resolve the HTTP bind port, preferring explicit app-level overrides."""

    port_value = os.getenv("IDEA_FACTORY_PORT") or os.getenv("APP_PORT", "8000")
    return int(port_value)


def parse_generation_count(raw_value: str) -> int:
    """Parse user-provided batch size into a safe integer."""

    try:
        numeric = int(raw_value)
    except ValueError:
        return 12
    return max(1, min(100, numeric))


def resolve_signal_limit_per_domain() -> int:
    """Resolve how many signals to collect per domain batch."""

    raw_value = os.getenv("MARKET_SIGNAL_LIMIT_PER_DOMAIN", "2")
    try:
        numeric = int(raw_value)
    except ValueError:
        return 2
    return max(1, min(12, numeric))


def build_signal_collector() -> CompositeMarketSignalCollector | None:
    """Build the live market signal collector when enabled."""

    enabled = os.getenv("ENABLE_MARKET_SCRAPING", "1")
    if enabled.lower() in {"0", "false", "no"}:
        return None
    return CompositeMarketSignalCollector()


def status_label(status: IdeaStatus) -> str:
    """Return a human-readable Russian label for one idea status."""

    labels = {
        IdeaStatus.INBOX: "Автономный инбокс",
        IdeaStatus.APPROVED: "Готово к запуску",
        IdeaStatus.INCUBATING: "Нужно додумать",
        IdeaStatus.REJECTED: "Отклонено",
    }
    return labels[status]


def main() -> None:
    """Start the local HTTP server."""

    host = resolve_server_host()
    port = resolve_server_port()
    handler = IdeaFactoryHandler
    handler.context = build_app_context()
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Idea Factory running at http://{host}:{port}", flush=True)
    server.serve_forever()

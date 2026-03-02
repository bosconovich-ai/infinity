"""Tiny HTTP interface with a textarea and three decision buttons."""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from idea_factory.domain.models import DecisionAction, IdeaStatus
from idea_factory.infrastructure.file_repository import MarkdownIdeaRepository
from idea_factory.infrastructure.openrouter_llm import build_default_structurer
from idea_factory.infrastructure.runtime import SystemClock, TimestampIdGenerator
from idea_factory.services.use_cases import (
    CreateIdeaFromCommentUseCase,
    ListIdeasByStatusUseCase,
)


@dataclass(frozen=True, slots=True)
class AppContext:
    """Container for interface dependencies."""

    create_idea: CreateIdeaFromCommentUseCase
    list_ideas: ListIdeasByStatusUseCase


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
        if parsed.path != "/submit":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(raw_body)
        comment = form.get("comment", [""])[0]
        decision_value = form.get("decision", [""])[0]

        try:
            decision = DecisionAction(decision_value)
            result = self.context.create_idea.execute(raw_comment=comment, decision=decision)
            status_message = (
                f"Saved '{result.card.title}' to "
                f"{result.card.status.value}/{result.path.name}"
            )
        except ValueError as exc:
            status_message = str(exc)

        self._redirect_with_message(status_message)

    def log_message(self, format: str, *args: object) -> None:
        """Keep request logging concise."""

        return

    def _redirect_with_message(self, message: str) -> None:
        quoted = quote(message, safe="")
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?message={quoted}")
        self.end_headers()

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
        approved = self.context.list_ideas.execute(status=IdeaStatus.APPROVED, limit=5)
        rejected = self.context.list_ideas.execute(status=IdeaStatus.REJECTED, limit=5)
        incubating = self.context.list_ideas.execute(status=IdeaStatus.INCUBATING, limit=5)

        sections = [
            ("Ready To Build", approved),
            ("Needs More Thinking", incubating),
            ("Rejected", rejected),
        ]

        cards_markup = "\n".join(
            self._render_status_section(title=title, cards=cards)
            for title, cards in sections
        )
        flash = (
            f"<p class='flash'>{html.escape(message)}</p>"
            if message
            else ""
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Idea Factory</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe5;
      --panel: #fffaf2;
      --ink: #1f1a14;
      --accent: #0c6c56;
      --warn: #8c5a12;
      --danger: #8b2e2e;
      --line: #dbcdb5;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top right, rgba(12,108,86,0.08), transparent 30%),
        radial-gradient(circle at bottom left, rgba(140,90,18,0.08), transparent 35%),
        var(--bg);
      color: var(--ink);
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{
      margin-bottom: 8px;
      font-size: clamp(2rem, 4vw, 3.5rem);
    }}
    p.lead {{
      margin-top: 0;
      max-width: 760px;
      font-size: 1.05rem;
      line-height: 1.5;
    }}
    .flash {{
      padding: 12px 14px;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 12px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(320px, 1.1fr) minmax(280px, 1fr);
      gap: 24px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 8px 24px rgba(31,26,20,0.05);
    }}
    textarea {{
      width: 100%;
      min-height: 240px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      font: inherit;
      resize: vertical;
      box-sizing: border-box;
      background: #fff;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      font: inherit;
      cursor: pointer;
      color: #fff;
    }}
    button[value="do"] {{
      background: var(--accent);
    }}
    button[value="rethink"] {{
      background: var(--warn);
    }}
    button[value="dont"] {{
      background: var(--danger);
    }}
    .columns {{
      display: grid;
      gap: 14px;
    }}
    .idea-card {{
      background: #fff;
      border-radius: 14px;
      padding: 14px;
      border: 1px solid var(--line);
    }}
    .idea-card h3 {{
      margin: 0 0 6px;
      font-size: 1rem;
    }}
    .idea-card p {{
      margin: 0 0 8px;
      line-height: 1.4;
      font-size: 0.95rem;
    }}
    .meta {{
      font-size: 0.82rem;
      color: #6b5b45;
    }}
    @media (max-width: 860px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Idea Factory</h1>
    <p class="lead">Leave a raw project comment, choose what to do with it, and the app will save a structured brief into the matching folder for later Codex work.</p>
    {flash}
    <div class="layout">
      <section class="panel">
        <h2>New Comment</h2>
        <form method="post" action="/submit">
          <textarea name="comment" placeholder="Describe the workflow, pain point, who pays, or rough project idea..."></textarea>
          <div class="actions">
            <button type="submit" name="decision" value="do">Делать</button>
            <button type="submit" name="decision" value="rethink">Додумать</button>
            <button type="submit" name="decision" value="dont">Не делать</button>
          </div>
        </form>
      </section>
      <section class="columns">
        {cards_markup}
      </section>
    </div>
  </main>
</body>
</html>"""

    def _render_status_section(self, *, title: str, cards: list[object]) -> str:
        items = [
            (
                "<article class='idea-card'>"
                f"<h3>{html.escape(card.title)}</h3>"
                f"<p>{html.escape(card.one_liner)}</p>"
                f"<div class='meta'>{html.escape(card.created_at.isoformat())}</div>"
                "</article>"
            )
            for card in cards
        ]
        empty = "<p class='meta'>No ideas yet.</p>" if not items else ""
        return (
            "<section class='panel'>"
            f"<h2>{html.escape(title)}</h2>"
            f"{''.join(items) or empty}"
            "</section>"
        )


def build_app_context() -> AppContext:
    """Wire default dependencies for the HTTP interface."""

    storage_root = Path(os.getenv("IDEA_STORAGE_ROOT", "ideas"))
    repository = MarkdownIdeaRepository(storage_root)
    create_idea = CreateIdeaFromCommentUseCase(
        llm=build_default_structurer(),
        repository=repository,
        clock=SystemClock(),
        id_generator=TimestampIdGenerator(),
    )
    list_ideas = ListIdeasByStatusUseCase(repository=repository)
    return AppContext(create_idea=create_idea, list_ideas=list_ideas)


def resolve_server_host() -> str:
    """Resolve the HTTP bind host from environment variables."""

    return os.getenv("IDEA_FACTORY_HOST", "127.0.0.1")


def resolve_server_port() -> int:
    """Resolve the HTTP bind port, preferring explicit app-level overrides."""

    port_value = os.getenv("IDEA_FACTORY_PORT") or os.getenv("APP_PORT", "8000")
    return int(port_value)


def main() -> None:
    """Start the local HTTP server."""

    host = resolve_server_host()
    port = resolve_server_port()
    handler = IdeaFactoryHandler
    handler.context = build_app_context()
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Idea Factory running at http://{host}:{port}", flush=True)
    server.serve_forever()

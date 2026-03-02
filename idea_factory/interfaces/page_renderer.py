"""HTML rendering for the idea factory web interface."""

from __future__ import annotations

import html
from typing import Sequence

from idea_factory.domain.models import IdeaCard, IdeaStatus


def render_page(
    *,
    message: str,
    inbox: Sequence[IdeaCard],
    approved: Sequence[IdeaCard],
    incubating: Sequence[IdeaCard],
    rejected: Sequence[IdeaCard],
) -> str:
    """Render the full application page."""

    inbox_markup = _render_status_section(
        title="Автономный инбокс",
        cards=inbox,
        status=IdeaStatus.INBOX,
    )
    secondary_markup = "\n".join(
        _render_status_section(title=title, cards=cards, status=status, compact=True)
        for title, cards, status in (
            ("Готово к запуску", approved, IdeaStatus.APPROVED),
            ("Нужно додумать", incubating, IdeaStatus.INCUBATING),
            ("Отклонено", rejected, IdeaStatus.REJECTED),
        )
    )
    flash = f"<p class='flash'>{html.escape(message)}</p>" if message else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Фабрика идей</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #10151b;
      --panel: #18212b;
      --panel-strong: #121a23;
      --ink: #eef4fb;
      --muted: #9cb0c3;
      --accent: #1f9d78;
      --warn: #c58a2b;
      --danger: #c04b52;
      --line: #2c3a49;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top right, rgba(31,157,120,0.18), transparent 28%),
        radial-gradient(circle at bottom left, rgba(197,138,43,0.12), transparent 32%),
        linear-gradient(160deg, rgba(255,255,255,0.02), transparent 40%),
        var(--bg);
      color: var(--ink);
    }}
    main {{
      max-width: 1360px;
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
      background: rgba(24,33,43,0.92);
      border-radius: 12px;
    }}
    .loading {{
      display: none;
      margin-top: 12px;
      padding: 12px 14px;
      border: 1px solid #705522;
      background: rgba(95,66,18,0.22);
      border-radius: 12px;
      color: #f0ca82;
      font-size: 0.95rem;
    }}
    .loading.visible {{
      display: block;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(300px, 340px) minmax(0, 1fr);
      gap: 28px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 14px 38px rgba(0,0,0,0.28);
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
      background: var(--panel-strong);
      color: var(--ink);
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    input[type="number"] {{
      width: 120px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 12px 16px;
      font: inherit;
      background: var(--panel-strong);
      color: var(--ink);
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      font: inherit;
      cursor: pointer;
      color: #fff;
      box-shadow: inset 0 -1px 0 rgba(0,0,0,0.18);
    }}
    button[value="generate"] {{
      background: #304f9e;
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
    button[name="target_status"][value="inbox"] {{
      background: #5d6472;
    }}
    button[name="target_status"][value="approved"] {{
      background: var(--accent);
    }}
    button[name="target_status"][value="incubating"] {{
      background: var(--warn);
    }}
    button[name="target_status"][value="rejected"] {{
      background: var(--danger);
    }}
    button[disabled],
    input[disabled],
    textarea[disabled] {{
      opacity: 0.6;
      cursor: wait;
    }}
    .columns {{
      display: grid;
      gap: 14px;
    }}
    .board {{
      display: grid;
      gap: 18px;
    }}
    .hero-section {{
      min-height: 58vh;
    }}
    .hero-section .idea-card {{
      padding: 16px;
    }}
    .secondary-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      align-items: start;
    }}
    .compact-section .idea-card {{
      padding: 12px;
    }}
    .compact-section .actions {{
      gap: 8px;
      margin-top: 12px;
    }}
    .compact-section button {{
      padding: 10px 12px;
      font-size: 0.9rem;
    }}
    .idea-card {{
      background: rgba(18,26,35,0.9);
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
      color: var(--muted);
    }}
    .score {{
      display: inline-block;
      margin-bottom: 8px;
      padding: 4px 9px;
      border-radius: 999px;
      background: rgba(197,138,43,0.18);
      color: #f3c978;
      font-size: 0.78rem;
    }}
    @media (max-width: 860px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .secondary-grid {{
        grid-template-columns: 1fr;
      }}
      .hero-section {{
        min-height: 0;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Фабрика идей</h1>
    <p class="lead">Запускай автономную генерацию по разным доменам или оставляй идею вручную. Приложение сохраняет структурированные брифы в папки, которые потом можно спокойно просмотреть и передать в Codex.</p>
    {flash}
    <div id="loading-indicator" class="loading" aria-live="polite"></div>
    <div class="layout">
      <section class="columns">
        <section class="panel">
          <h2>Автономная генерация</h2>
          <p class="meta">Генерирует до 100 идей, ротирует домены и углы промпта, берёт случайные сигналы из фонового кэша, использует повышенную креативность модели и сама ставит оценку от 1 до 10.</p>
          <form method="post" action="/generate" data-loading-message="Идёт генерация идей. Сигналы берутся из фонового кэша, дальше работает модель.">
            <textarea name="seed_context" placeholder="Необязательные вводные: какие рынки тебе интересны, какие продукты предпочитать, чего избегать..."></textarea>
            <div class="actions">
              <input type="number" name="count" min="1" max="100" value="12">
              <button type="submit" name="mode" value="generate">Сгенерировать</button>
            </div>
          </form>
        </section>
        <section class="panel">
          <h2>Ручной ввод</h2>
          <form method="post" action="/submit" data-loading-message="Идёт обработка идеи и сохранение карточки.">
            <textarea name="comment" placeholder="Опиши процесс, боль, кто платит, или просто набросай идею проекта..."></textarea>
            <div class="actions">
              <button type="submit" name="decision" value="do">Делать</button>
              <button type="submit" name="decision" value="rethink">Додумать</button>
              <button type="submit" name="decision" value="dont">Не делать</button>
            </div>
          </form>
        </section>
      </section>
      <section class="board">
        <section class="hero-section">
          {inbox_markup}
        </section>
        <section class="secondary-grid">
          {secondary_markup}
        </section>
      </section>
    </div>
  </main>
  <script>
    (function () {{
      const indicator = document.getElementById("loading-indicator");
      if (!indicator) {{
        return;
      }}
      for (const form of document.querySelectorAll("form[data-loading-message]")) {{
        form.addEventListener("submit", () => {{
          const message = form.getAttribute("data-loading-message") || "Идёт обработка...";
          indicator.textContent = message;
          indicator.classList.add("visible");
          for (const field of form.querySelectorAll("button, input, textarea")) {{
            field.disabled = true;
          }}
        }});
      }}
    }})();
  </script>
</body>
</html>"""


def _render_status_section(
    *,
    title: str,
    cards: Sequence[IdeaCard],
    status: IdeaStatus,
    compact: bool = False,
) -> str:
    items = [
        (
            "<article class='idea-card'>"
            f"<h3>{html.escape(card.title)}</h3>"
            f"<p>{html.escape(card.one_liner)}</p>"
            f"{_render_score(card.score)}"
            f"{_render_inbox_actions(card, status=status)}"
            f"<div class='meta'>{html.escape(card.created_at.isoformat())}</div>"
            "</article>"
        )
        for card in cards
    ]
    empty = "<p class='meta'>Пока идей нет.</p>" if not items else ""
    section_class = "panel compact-section" if compact else "panel"
    return (
        f"<section class='{section_class}'>"
        f"<h2>{html.escape(title)}</h2>"
        f"{''.join(items) or empty}"
        "</section>"
    )


def _render_score(score: float | None) -> str:
    if score is None:
        return ""
    return f"<div class='score'>Оценка: {html.escape(f'{float(score):.1f}/10')}</div>"


def _render_inbox_actions(card: IdeaCard, *, status: IdeaStatus) -> str:
    actions = []
    for target_status, label in (
        (IdeaStatus.INBOX, "В инбокс"),
        (IdeaStatus.APPROVED, "Готово к запуску"),
        (IdeaStatus.INCUBATING, "Нужно додумать"),
        (IdeaStatus.REJECTED, "Отклонено"),
    ):
        if target_status is status:
            continue
        actions.append(
            "<button type='submit' "
            f"name='target_status' value='{html.escape(target_status.value)}'>"
            f"{html.escape(label)}"
            "</button>"
        )
    if not actions:
        return ""
    return (
        "<form method='post' action='/move' "
        "data-loading-message='Идёт перенос идеи в выбранную колонку.'>"
        f"<input type='hidden' name='idea_id' value='{html.escape(card.idea_id)}'>"
        "<div class='actions'>"
        f"{''.join(actions)}"
        "</div>"
        "</form>"
    )

# Idea Factory MVP

Minimal clean-architecture project intake service:

- Accept a raw project comment.
- Normalize it into a structured idea card.
- Save the result into `ideas/approved`, `ideas/rejected`, or `ideas/incubating`.
- Use OpenRouter when configured, with a deterministic local fallback when it is not.

## Run

```bash
python3 -m idea_factory
```

Then open `http://127.0.0.1:8000`.

## Environment

- `OPENROUTER_API_KEY`: Optional. Enables external LLM structuring.
- `OPENROUTER_MODEL`: Optional. Defaults to `qwen/qwen3.5-397b-a17b`.
- `OPENROUTER_IDEATION_TEMPERATURE`: Optional. Defaults to `1.15` for autonomous generation.
- `IDEA_STORAGE_ROOT`: Optional. Defaults to `./ideas`.
- `IDEA_FACTORY_HOST`: Optional. Defaults to `127.0.0.1`.
- `IDEA_FACTORY_PORT`: Optional. Defaults to `8000`.
- `APP_PORT`: Optional fallback for containerized runs when `IDEA_FACTORY_PORT` is not set.
- `ENABLE_MARKET_SCRAPING`: Optional. Defaults to `1`.
- `MARKET_SIGNAL_LIMIT_PER_DOMAIN`: Optional. Defaults to `2`. Controls how many cached signals are sampled into one domain batch.
- `MARKET_SIGNAL_REFRESH_LIMIT_PER_DOMAIN`: Optional. Defaults to `8`. Controls how many fresh signals the background scraper stores per domain refresh.
- `MARKET_SIGNAL_REFRESH_INTERVAL_SECONDS`: Optional. Defaults to `900`.
- `GITHUB_TOKEN`: Optional. Improves GitHub issue search rate limits.

## Autonomous Factory

- Generate up to 100 ideas into `ideas/inbox`.
- The generator rotates through multiple domain profiles.
- Each batch mutates its prompt with a different creative angle.
- A daemon scraper keeps refreshing cached market signals from Reddit and GitHub issues.
- The generator samples random signals from the local cache instead of waiting on live scraping per click.
- The model self-scores each idea from `1` to `10`.
- Optional seed context lets you bias the batch toward specific markets or constraints.

## Container

```bash
docker compose up --build
```

By default the app binds to `127.0.0.1:18000` on the host and `8000` inside the container.
The service exposes a readiness endpoint at `GET /health`.
The local compose service runs as your host UID/GID by default so generated idea files remain writable on the bind-mounted `ideas/` directory.

## Testing

The test suite is written in a `pytest`-compatible layout but uses only the standard
library so it can also run with:

```bash
python3 -m unittest discover -s tests -v
```

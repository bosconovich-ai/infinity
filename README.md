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
- `OPENROUTER_MODEL`: Optional. Defaults to `qwen/qwen2.5-7b-instruct`.
- `IDEA_STORAGE_ROOT`: Optional. Defaults to `./ideas`.
- `IDEA_FACTORY_HOST`: Optional. Defaults to `127.0.0.1`.
- `IDEA_FACTORY_PORT`: Optional. Defaults to `8000`.

## Testing

The test suite is written in a `pytest`-compatible layout but uses only the standard
library so it can also run with:

```bash
python3 -m unittest discover -s tests -v
```

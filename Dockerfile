# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_PORT=8000 \
    IDEA_FACTORY_HOST=0.0.0.0 \
    IDEA_STORAGE_ROOT=/data/ideas

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /data/ideas \
    && chown -R app:app /data

COPY idea_factory ./idea_factory

USER app

EXPOSE ${APP_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"APP_PORT\", \"8000\")}/health', timeout=5).read()" || exit 1

CMD ["python", "-m", "idea_factory"]

FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /workspace/apps/api

COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/ ./
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm

WORKDIR /workspace/apps/api

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY --from=builder --chown=10001:10001 /workspace /workspace

ENV PATH="/workspace/apps/api/.venv/bin:${PATH}"
ENV PYTHONPATH="/workspace/apps/api/src"

EXPOSE 8000

USER 10001:10001

CMD ["uvicorn", "meterdesk_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

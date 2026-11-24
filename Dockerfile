FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache
COPY src ./src
RUN uv sync --locked --no-dev --no-cache
COPY config.yaml ./
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["python", "-m", "kube_certificates_syncer.main"]

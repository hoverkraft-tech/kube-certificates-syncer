# checkov:skip=CKV_DOCKER_2:This Kubernetes watch worker has no health endpoint; Kubernetes restarts it when its main process exits.
FROM python:3.12-slim@sha256:37fc60d303cb9294d3718b5b48998a0210bb1c73611c1399ef5eb7964c0536e5
COPY --from=ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache
COPY src ./src
RUN uv sync --locked --no-dev --no-cache
COPY config.yaml ./
ENV PATH="/app/.venv/bin:$PATH"
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir /certs && chown app:app /certs
USER 10001:10001
ENTRYPOINT ["python", "-m", "kube_certificates_syncer.main"]

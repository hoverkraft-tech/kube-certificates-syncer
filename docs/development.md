# Development

Install uv and Python 3.12, then use the committed lockfile:

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked black --check .
uv run --locked mypy .
uv run --locked pytest --junitxml=junit.xml --cov --cov-report=term-missing --cov-report=xml:cobertura.xml
```

The tests use synthetic Kubernetes events and temporary directories; they do
not require a cluster. To run against your configured cluster:

```sh
uv run --locked python -m kube_certificates_syncer.main
```

CI calls `ci-github-python` at `main` while the shared workflow is being
validated in consumer repositories. It runs lint, tests, dependency review and
an audit of the locked production dependencies, then builds and imports the
application in its Docker image. Nothing is published by this workflow.

Update dependencies with `uv lock --upgrade`, commit `uv.lock`, and rerun the
checks. Docker installs only production dependencies from that same lockfile.

The Kubernetes client stubs omit `Watch`. The small stub in `typings/` covers
its public streaming API so strict mypy checks can run without ignored imports.

# Development

## Environment

Open this repository in Visual Studio Code and select "Reopen in Container". The devcontainer
installs Python tooling, Docker and the GitHub CLI, then runs `make setup`.
The committed feature lockfile makes the feature resolution reproducible.
Runtime and tool versions live in [devcontainer.json](../../.devcontainer/devcontainer.json).

For a host setup, install Docker and the same language tools, then run `make setup`.
The Python version comes from [.python-version](../../.python-version); uv installs the committed `uv.lock`.

## Commands

| Command         | Purpose                                           |
| --------------- | ------------------------------------------------- |
| `make setup`    | Install or verify dependencies                    |
| `make lint`     | Check application code and repository files       |
| `make lint-fix` | Apply supported formatting fixes                  |
| `make test`     | Run tests and collect coverage                    |
| `make audit`    | Check production dependencies for vulnerabilities |
| `make build`    | Build locally without publishing                  |
| `make ci`       | Run the complete local validation sequence        |

`make lint-repository` uses the same pinned Hoverkraft Super-Linter image and
validator selection as CI. It checks workflows, action pinning policy, configuration,
Markdown, spelling, shell scripts, Dockerfiles and infrastructure security.
Language lint runs through the project-owned tools in `make lint-code` and the shared
language CI, so dependency resolution and tool configuration stay consistent.

## Continuous integration

Pull requests, merge queues and main-branch pushes run the shared language checks
and repository linter. A weekly run detects newly disclosed dependency vulnerabilities.
Shared CI reports consolidate native reports after the producer jobs finish; producer
failures continue to block validation. The semantic PR workflow and repository linter
share [.commitlintrc.json](../../.commitlintrc.json).

The `ci-github-python` references intentionally use `main` during adoption.
The pinning policy permits that repository only; other external actions use reviewed
SHAs with version comments. Replace those temporary branch references with reviewed
release pins after adoption.

Dependabot groups weekly updates for actions, language dependencies, Docker images
and devcontainer features, with a seven-day cooldown and Conventional Commit titles.
Review the lockfile and run `make ci` when updating dependencies or features.

## Application checks

Tests use synthetic Kubernetes events and temporary directories, without a cluster.
Docker installs production dependencies from the same uv lockfile as CI. CI builds
that image and checks the installed application imports; it does not publish it.

Run the application against your configured cluster with:

```sh
uv run --locked python -m kube_certificates_syncer.main
```

The Kubernetes stubs omit `Watch`; [typings](../../typings/kubernetes/watch/__init__.pyi)
covers its public streaming API without ignored imports.

## Container policy

The container runs as a non-root user. The scoped Docker health-check exception in
[the scanner configuration](../../.github/linters/trivy-exceptions.yaml) documents
why this application has no HTTP health endpoint.

The example Role grants only list/watch access to Secrets in its namespace.
That access is essential to the syncer and is the only RBAC scanner exception.
The sample deployment drops capabilities, uses a read-only root filesystem, sets
resource budgets and grants volume access through `fsGroup: 10001`. Its service
account token is required to watch the Kubernetes API.

The existing GitHub CodeQL default setup continues to scan Python. The shared
linter disables its additional CodeQL job because GitHub rejects advanced-setup
results while default setup is enabled. Actionlint, Zizmor and Checkov still check
workflow correctness and security.

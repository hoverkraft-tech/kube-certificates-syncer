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
tool configuration as CI, without a repository validator allowlist. It checks
workflows, action pinning policy, configuration,
Markdown, spelling, shell scripts, Dockerfiles and infrastructure security.
Language lint runs through the project-owned tools in `make lint-code` and the shared
language CI, so dependency resolution and tool configuration stay consistent.
The repository linter selects Black, matching the locked formatter, and reads the
project configuration for Black and isort. Pylint, Ruff and the other validators
remain enabled.

## Continuous integration

Pull requests, merge queues and main-branch pushes run the shared language checks
and repository linter. A weekly run detects newly disclosed dependency vulnerabilities.
Python 3.12 and 3.15 both retain detailed test results. Lint and coverage run once,
on Python 3.15. The Python actions validate their native reports before uploading
them; missing or malformed results fail the producer.

One final reporting job waits for the repository linter, Python checks and container
smoke test. It publishes annotations for lint and test failures, plus coverage through
GitHub when Code Quality is enabled or a PR comment otherwise. Its summary includes
the tested revision, runtime and links to the original jobs. No artifact IDs or
report inventories need forwarding. Producer failures continue to block validation. The semantic PR workflow and repository linter
share [.commitlintrc.json](../../.commitlintrc.json).

External actions and reusable workflows use reviewed release SHAs with matching
version comments. Dependabot maintains these references.

Dependabot groups weekly updates for actions, language dependencies, Docker images
and devcontainer features, with a seven-day cooldown and Conventional Commit titles.
Renovate maintains runtime versions and embedded tool versions through the scheduled
[workflow](../../.github/workflows/__renovate.yml) and
[configuration](../../.github/renovate.json). It uses the organization CI bot's
`CI_BOT_APP_CLIENT_ID` variable and `CI_BOT_APP_PRIVATE_KEY` secret. Dependabot
continues to maintain package dependencies, actions, Docker images and features.
Review the lockfile and run `make ci` when updating dependencies or features.

## Application checks

Tests use synthetic Kubernetes events and temporary directories, without a cluster.
Docker installs production dependencies from the same uv lockfile as CI.
The container job uses `ci-github-container/actions/docker/setup` to manage Docker,
Buildx and registry authentication. Docker's build action loads the image locally
for the non-root import and certificate-volume write checks. Image publication is
disabled, and the job needs only read access to repository contents and packages.

Run the application against your configured cluster with:

```sh
uv run --locked python -m kube_certificates_syncer.main
```

The Kubernetes stubs omit `Watch`; [typings](../../typings/kubernetes/watch/__init__.pyi)
covers its public streaming API without ignored imports.

## Container policy

The container runs as a non-root user and declares `HEALTHCHECK NONE`: this
Kubernetes watch worker has no HTTP health endpoint. Kubernetes restarts it when
its main process exits.

The example Role grants only list/watch access to Secrets in its namespace.
That access is essential to the syncer. Trivy does not support inline exceptions
for raw Kubernetes YAML, so its sole exception is limited to that rule and
[Role file](../../tests/manifests/role.yaml) in
[the scanner configuration](../../.github/linters/trivy-exceptions.yaml).
The sample deployment drops capabilities, uses a read-only root filesystem, sets
resource budgets and grants volume access through `fsGroup: 10001`. Its service
account token is required to watch the Kubernetes API.

The existing GitHub CodeQL default setup continues to scan Python. The shared
linter disables its additional CodeQL job because GitHub rejects advanced-setup
results while default setup is enabled. Actionlint, Zizmor and Checkov still check
workflow correctness and security.

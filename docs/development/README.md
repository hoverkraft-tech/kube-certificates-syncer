# Development

## Environment

Open this repository in Visual Studio Code and select "Reopen in Container". The devcontainer
installs Python tooling, Docker and the GitHub CLI, then runs `make setup`.
The committed feature lockfile makes the feature resolution reproducible.
Runtime and tool versions live in [devcontainer.json](../../.devcontainer/devcontainer.json).

For a host setup, install Docker and the same language tools, then run `make setup`.
The Python version comes from [.python-version](../../.python-version); uv installs the committed `uv.lock`.

## Commands

| Command           | Purpose                                               |
| ----------------- | ----------------------------------------------------- |
| `make setup`      | Install or verify dependencies                        |
| `make lint`       | Check application code and repository files           |
| `make lint-fix`   | Apply supported formatting fixes                      |
| `make test`       | Run tests and collect coverage                        |
| `make test-image` | Build and test the production image with the CI suite |
| `make audit`      | Check production dependencies for vulnerabilities     |
| `make build`      | Build locally without publishing                      |
| `make ci`         | Run the complete local validation sequence            |

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
Python lint, tests, audit and coverage run once using
[.python-version](../../.python-version). Keep this pin aligned with the production
[Dockerfile](../../Dockerfile), which defines the deployed runtime. The Python
actions validate their native reports before uploading them; missing or malformed
results fail the producer.

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
and passes its exact image ID to `ci-github-container/actions/docker/test-image`.
The action detects the [Goss suite](../../tests/container-image/goss.yaml),
which checks the production user, application import, read-only root filesystem
and writable certificate volume with dropped capabilities and no new privileges.
Goss runs directly as the container's command, using the image's application user.
Its native JUnit results join the consolidated CI report. The action supplies the
Goss binary; no test tooling is added to the production image.
Image publication is disabled; the job uses read access to Actions, contents and packages.

Run the same image suite locally with `make test-image`. It builds the production
image, resolves its immutable local ID and runs the same suite and
[Docker security options](../../tests/container-image/docker-args) with the same
Goss version as CI. The Make target extracts the binary from the pinned official
Goss image and removes its temporary containers and binary after execution.
This requires Linux, Docker with a local Unix socket and the standard `timeout`
command; no host Goss or Node.js installation or Kubernetes cluster is needed.
Execution is limited to five minutes. `make ci` includes this check.
The native JUnit report is retained, including after assertion failures, at
`.cache/container-tests/junit.xml`; the local image remains available for inspection.
Use `make test-image IMAGE=kube-certificates-syncer:custom` to choose its local tag.

These are packaging checks. They do not start the worker, connect to Kubernetes
or validate its watch loop. A Goss suite that needs a running application can call
a project-owned script that starts it, waits for readiness, checks its behavior
and stops it. Keep dependent steps together because Goss checks can run concurrently.

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

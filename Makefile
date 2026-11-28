.DEFAULT_GOAL := help
.PHONY: help setup lint lint-code lint-repository lint-fix test test-image audit build ci

LINTER_IMAGE := kube-certificates-syncer-linter:local
IMAGE ?= kube-certificates-syncer:local
# Match ci-github-container/actions/docker/test-image/tooling.json.
TESTCONTAINERS_IMAGE := ghcr.io/hoverkraft-tech/docker-base-images/testcontainers-node:1.0.5@sha256:0a8eabad2b41854803acd0608472ef404b94aa8d8ee29e472cf6e86a1ee53248
RYUK_IMAGE := docker.io/testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0

help: ## Show development commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install the locked development environment
	uv sync --locked

lint-code: ## Check Python with the project-locked tools
	uv run --locked ruff check .
	uv run --locked black --check .
	uv run --locked mypy .

test: ## Run isolated tests with JUnit and coverage reports
	uv run --locked pytest --junitxml=junit.xml --cov --cov-report=term-missing --cov-report=xml:cobertura.xml

audit: ## Audit locked production dependencies
	@set -eu; requirements=$$(mktemp); trap 'rm -f "$$requirements"' EXIT; \
	uv export --locked --no-default-groups --no-emit-project --format=requirements-txt --output-file="$$requirements" >/dev/null; \
	uvx --from pip-audit==2.10.1 pip-audit --require-hashes --disable-pip --requirement "$$requirements"

build: ## Build the production container without publishing
	docker build --tag "$(IMAGE)" .

test-image: build ## Build and test the production image with the CI suite
	@set -eu; \
	image_id=$$(docker image inspect --format '{{.Id}}' "$(IMAGE)"); \
	socket=$$(docker context inspect --format '{{.Endpoints.docker.Host}}'); \
	if [ -n "$${DOCKER_HOST:-}" ] && [ -z "$${DOCKER_CONTEXT:-}" ]; then socket=$$DOCKER_HOST; fi; \
	case "$$socket" in unix://*) socket=$${socket#unix://} ;; *) echo 'Image tests require a local Unix Docker socket.' >&2; exit 1 ;; esac; \
	test -S "$$socket"; \
	mkdir -p .cache/container-tests; \
	docker run --rm --init --network host --user 0:0 \
		--volume "$$socket:/var/run/docker.sock" \
		--volume "$(CURDIR)/tests/container-image:/workspace/image:ro" \
		--volume "$(CURDIR)/.cache/container-tests:/reports" \
		--env DOCKER_HOST=unix:///var/run/docker.sock \
		--env TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock \
		--env TESTCONTAINERS_HOST_OVERRIDE=127.0.0.1 \
		--env TESTED_IMAGE_REF="$$image_id" \
		--env RYUK_CONTAINER_IMAGE="$(RYUK_IMAGE)" \
		--env TEST_JUNIT_REPORT_PATH=/reports/junit.xml \
		--env HOST_UID="$$(id -u)" --env HOST_GID="$$(id -g)" \
		"$(TESTCONTAINERS_IMAGE)" --test-timeout=300000 /workspace/image/image.test.js

lint-fix: ## Apply Python and repository formatting fixes
	uv run --locked ruff check --fix .
	uv run --locked black .
	$(call run_linter,-e FIX_YAML_PRETTIER=true -e FIX_MARKDOWN=true -e FIX_MARKDOWN_PRETTIER=true -e FIX_BIOME_FORMAT=true -e FIX_SHELL_SHFMT=true)

lint: lint-code lint-repository ## Run application and repository checks

lint-repository: ## Run Hoverkraft's shared repository linter
	$(call run_linter,)

ci: setup ## Run local validation without rewriting tracked files
	$(MAKE) lint test audit test-image

define run_linter
	docker build --build-arg UID=$(shell id -u) --build-arg GID=$(shell id -g) --tag $(LINTER_IMAGE) .github/linters
	docker run --rm -v "$(CURDIR):$(CURDIR)" -w "$(CURDIR)" -e DEFAULT_WORKSPACE="$(CURDIR)" $(1) $(LINTER_IMAGE)
endef

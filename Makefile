.DEFAULT_GOAL := help
.PHONY: help setup lint lint-code lint-repository lint-fix test test-image audit build ci

LINTER_IMAGE := kube-certificates-syncer-linter:local
IMAGE ?= kube-certificates-syncer:local
# Match the Goss version in ci-github-container/actions/docker/test-image/tooling.json.
GOSS_IMAGE := ghcr.io/goss-org/goss:v0.4.10@sha256:8d3924f722a04a660e9e6c2403be0399d737c0187fc065714d26b992286c3f0a

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
	platform=$$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$$image_id"); \
	socket=$$(docker context inspect --format '{{.Endpoints.docker.Host}}'); \
	if [ -n "$${DOCKER_HOST:-}" ] && [ -z "$${DOCKER_CONTEXT:-}" ]; then socket=$$DOCKER_HOST; fi; \
	case "$$socket" in unix://*) socket=$${socket#unix://} ;; *) echo 'Image tests require a local Unix Docker socket.' >&2; exit 1 ;; esac; \
	test -S "$$socket"; \
	mkdir -p .cache/container-tests; \
	rm -f .cache/container-tests/junit.xml; \
	tools=$$(mktemp -d "$(CURDIR)/.cache/container-tests/tools.XXXXXX"); \
	tool_container=; test_container=; \
	trap 'if [ -n "$$test_container" ]; then docker rm --force --volumes "$$test_container" >/dev/null; fi; if [ -n "$$tool_container" ]; then docker rm --force --volumes "$$tool_container" >/dev/null; fi; rm -rf "$$tools"' EXIT; \
	trap 'exit 130' INT; trap 'exit 143' TERM; \
	tool_container=$$(docker create --platform "$$platform" "$(GOSS_IMAGE)" /bin/true); \
	docker cp "$$tool_container:/usr/bin/goss" "$$tools/goss"; \
	chmod 755 "$$tools/goss"; \
	set --; \
	while IFS= read -r option || [ -n "$$option" ]; do \
		case "$$option" in ''|'#'*) continue ;; esac; \
		set -- "$$@" "$$option"; \
	done < tests/container-image/docker-args; \
	test_container=$$(docker create "$$@" --platform "$$platform" \
		--volume "$$tools/goss:/goss-bin:ro" \
		--volume "$(CURDIR)/tests/container-image:/goss:ro" \
		--entrypoint /goss-bin "$$image_id" -g /goss/goss.yaml validate --format junit); \
	echo 'Running image checks; JUnit report: .cache/container-tests/junit.xml'; \
	timeout --kill-after=5s 300s docker start --attach "$$test_container" > .cache/container-tests/junit.xml

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

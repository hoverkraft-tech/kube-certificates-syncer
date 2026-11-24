.DEFAULT_GOAL := help
.PHONY: help setup lint lint-code lint-repository lint-fix test audit build ci

LINTER_IMAGE := kube-certificates-syncer-linter:local

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
	docker build --tag kube-certificates-syncer:local .

lint-fix: ## Apply Python and repository formatting fixes
	uv run --locked ruff check --fix .
	uv run --locked black .
	$(call run_linter,-e FIX_YAML_PRETTIER=true -e FIX_MARKDOWN=true -e FIX_MARKDOWN_PRETTIER=true -e FIX_BIOME_FORMAT=true -e FIX_SHELL_SHFMT=true)

lint: lint-code lint-repository ## Run application and repository checks

lint-repository: ## Run Hoverkraft's shared repository linter
	$(call run_linter,)

ci: setup ## Run local validation without rewriting tracked files
	$(MAKE) lint test audit build

define run_linter
	docker build --build-arg UID=$(shell id -u) --build-arg GID=$(shell id -g) --tag $(LINTER_IMAGE) .github/linters
	docker run --rm -v "$(CURDIR):$(CURDIR)" -w "$(CURDIR)" -e DEFAULT_WORKSPACE="$(CURDIR)" $(1) $(LINTER_IMAGE)
endef

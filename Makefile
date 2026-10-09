.DEFAULT_GOAL := help
.PHONY: help validate test test-go test-py lint lint-go lint-py public-surface tracked-artifacts fmt generate generate-go generate-check wiring-check audit audit-go audit-py

help: ## List repository targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

validate: lint generate-check wiring-check test ## Full offline gate: lint, formatting, generated drift, wiring, tests

test: test-go test-py ## Run every adapter's offline tests

test-go: ## Run tests in every Go module
	python3 scripts/check-adapters.py test-go

test-py: ## Run tests in every Python package with live opt-ins absent
	python3 scripts/check-adapters.py test-py

lint: public-surface tracked-artifacts lint-go lint-py ## Repository guards, source lint and formatting checks

lint-go: ## Check Go formatting and vet every Go module
	python3 scripts/check-adapters.py lint-go

lint-py: ## Check Python source, entrypoints, tests and generator scripts
	python3 scripts/check-adapters.py lint-py

public-surface: ## Run the public-surface guard and its self-test
	scripts/public-surface-check
	scripts/public-surface-check-test

tracked-artifacts: ## Refuse tracked compiled build artifacts
	scripts/tracked-artifact-check

fmt: ## Format handwritten Go and Python code
	python3 scripts/check-adapters.py fmt

generate: ## Regenerate local descriptors, bindings and typed registration
	uv run scripts/generate-go-adapters --bindings
	python3 scripts/generate-python-adapters --write

generate-go: ## Regenerate Go descriptors, typed registration and protobuf bindings
	uv run scripts/generate-go-adapters --bindings

generate-check: ## Verify bindings use the exact embedded descriptor graph
	uv run scripts/generate-go-adapters --bindings --check
	python3 scripts/generate-python-adapters --check

wiring-check: ## Verify all Python entrypoint registrations without provider I/O
	python3 scripts/check-python-wiring.py

audit: public-surface tracked-artifacts audit-go audit-py ## Run unsuppressed module and dependency vulnerability checks

audit-go: ## Verify Go sums and audit every module including tests
	python3 scripts/check-adapters.py audit-go

audit-py: ## Audit every locked Python environment
	python3 scripts/check-adapters.py audit-py

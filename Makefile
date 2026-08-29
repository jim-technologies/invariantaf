.PHONY: help help-all validate test test-go test-py lint lint-go lint-py public-surface tracked-artifacts fmt

help: ## One-screen help (make help-all for every target)
	@echo "Daily:"
	@echo "  make fmt        gofmt + ruff format everywhere"
	@echo "  make test            every adapter's tests (Go + Python)"
	@echo "  make lint            guards + go vet + ruff, every adapter"
	@echo "  make validate        the full offline gate: lint + test"
	@echo "  make public-surface  the publish guard + its self-test alone"
	@echo ""
	@echo "Everything else: make help-all"

help-all: ## Every target with its description
	@grep -hE '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'

test: test-go test-py ## All tests in every adapter (Go + Python)

test-go: ## go test in every Go module
	@failed=0; \
	for d in $$(find . -maxdepth 2 -name "go.mod" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if (cd $$d && go test -count=1 ./... > /dev/null 2>&1); then \
			echo "PASS: $$name"; \
		else \
			echo "FAIL: $$name"; \
			failed=1; \
		fi; \
	done; \
	if [ $$failed -eq 1 ]; then exit 1; fi

test-py: ## pytest in every Python package that has tests
	@failed=0; \
	for d in $$(find . -maxdepth 2 -name "pyproject.toml" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if [ -d "$$d/tests" ] && [ -n "$$(find $$d/tests -name 'test_*.py' 2>/dev/null)" ]; then \
			if (cd $$d && uv run python -m pytest tests/ -q --no-header > /dev/null 2>&1); then \
				echo "PASS: $$name"; \
			else \
				echo "FAIL: $$name"; \
				failed=1; \
			fi; \
		fi; \
	done; \
	if [ $$failed -eq 1 ]; then exit 1; fi

# The gate. `make validate` is the one gate verb in every public repository in
# this organisation; here it routes to `lint` and `test`, this repo's full gate.
validate: lint test ## The full offline gate: lint + test

lint: public-surface tracked-artifacts lint-go lint-py ## Repo guards, then go vet + ruff

# Guard the public surface: tracked content, tracked paths, and the commit
# messages a push would publish. Exceptions live in .public-surface-allow.
public-surface: ## Public-surface guard + its self-test
	scripts/public-surface-check
	scripts/public-surface-check-test

# Refuse to publish compiled build artifacts, whatever .gitignore says.
tracked-artifacts: ## Refuse tracked compiled build artifacts
	scripts/tracked-artifact-check

fmt: ## gofmt + ruff format in every module/package
	@for d in $$(find . -maxdepth 2 -name "go.mod" -exec dirname {} \; | sort); do \
		gofmt -w "$$d"; \
	done
	@for d in $$(find . -maxdepth 2 -name "pyproject.toml" -exec dirname {} \; | sort); do \
		(cd "$$d" && ruff format . --exclude "*_pb2.py" --exclude "*_pb2.pyi" --exclude "gen"); \
	done

lint-go: ## go vet in every Go module
	@failed=0; \
	for d in $$(find . -maxdepth 2 -name "go.mod" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if (cd $$d && go vet ./... 2>&1); then \
			echo "PASS: $$name"; \
		else \
			echo "FAIL: $$name"; \
			failed=1; \
		fi; \
	done; \
	if [ $$failed -eq 1 ]; then exit 1; fi

lint-py: ## ruff check in every Python package that has src
	@failed=0; \
	for d in $$(find . -maxdepth 2 -name "pyproject.toml" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if [ -d "$$d/src" ]; then \
			if (cd $$d && uv run ruff check src/ 2>&1); then \
				echo "PASS: $$name"; \
			else \
				echo "FAIL: $$name"; \
				failed=1; \
			fi; \
		fi; \
	done; \
	if [ $$failed -eq 1 ]; then exit 1; fi

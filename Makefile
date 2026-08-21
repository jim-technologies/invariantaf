.PHONY: validate test test-go test-py lint lint-go lint-py public-surface tracked-artifacts

test: test-go test-py

test-go:
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

test-py:
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
validate: lint test

lint: public-surface tracked-artifacts lint-go lint-py

# Guard the public surface: tracked content, tracked paths, and the commit
# messages a push would publish. Exceptions live in .public-surface-allow.
public-surface:
	scripts/public-surface-check
	scripts/public-surface-check-test

# Refuse to publish compiled build artifacts, whatever .gitignore says.
tracked-artifacts:
	scripts/tracked-artifact-check

lint-go:
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

lint-py:
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

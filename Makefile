.PHONY: test test-go test-py lint lint-go lint-py

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

lint: lint-go lint-py

lint-go:
	@for d in $$(find . -maxdepth 2 -name "go.mod" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if (cd $$d && go vet ./... 2>&1); then \
			echo "PASS: $$name"; \
		else \
			echo "FAIL: $$name"; \
		fi; \
	done

lint-py:
	@for d in $$(find . -maxdepth 2 -name "pyproject.toml" -exec dirname {} \; | sort); do \
		name=$$(basename $$d); \
		if [ -d "$$d/src" ]; then \
			(cd $$d && uv run ruff check src/ 2>&1) || echo "FAIL: $$name"; \
		fi; \
	done

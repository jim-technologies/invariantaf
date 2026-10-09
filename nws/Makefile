.DEFAULT_GOAL := help
.PHONY: generate descriptor lint fmt serve-mcp serve-cli test clean

generate: ## Regenerate exact descriptor and native language bindings
	cd .. && python3 scripts/generate-python-adapters --write nws

descriptor: generate ## Rebuild descriptor and bindings from the same graph

lint: ## Lint canonical protobuf and Python source
	cd proto && buf lint
	ruff check src/ tests/ main.py

fmt: ## Format protobuf and Python source
	cd proto && buf format -w
	ruff format src/ tests/ main.py

serve-mcp: ## Serve MCP over stdio
	uv run python main.py

serve-cli: ## Serve the CLI projection
	uv run python main.py --cli

test: ## Run adapter tests with live integration opt-in
	uv run python -m pytest tests/ -v

clean: ## Remove local generated or build output
	rm -rf descriptor.binpb src/nws_mcp/gen/nws/

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

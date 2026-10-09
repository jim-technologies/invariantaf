.DEFAULT_GOAL := help
.PHONY: generate descriptor serve test clean

generate: ## Regenerate exact descriptor and native language bindings
	cd .. && python3 scripts/generate-python-adapters --write cocktaildb

descriptor: generate ## Rebuild descriptor and bindings from the same graph

lint: ## Lint canonical protobuf and Python source
	cd proto && buf lint
	ruff check src/

fmt: ## Format protobuf and Python source
	cd proto && buf format -w
	ruff format src/

serve-mcp: ## Serve MCP over stdio
	uv run python main.py

serve-cli: ## Serve the CLI projection
	uv run python main.py --cli

test: ## Run adapter tests with live integration opt-in
	uv run python -m pytest tests/ -v

clean: ## Remove local generated or build output
	rm -rf descriptor.binpb src/cocktaildb_mcp/gen/cocktaildb/

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

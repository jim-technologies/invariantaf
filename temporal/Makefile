.DEFAULT_GOAL := help
.PHONY: descriptor lint fmt serve-mcp serve-cli test clean

TEMPORAL_API_REVISION ?=

descriptor: ## Refresh from a reviewed immutable TEMPORAL_API_REVISION
	python3 ../scripts/refresh-temporal-descriptor.py "$(TEMPORAL_API_REVISION)"

lint: ## Lint the canonical source and Go implementation
	go vet ./...

fmt: ## Format protobuf and Go source
	gofmt -w .

test: ## Run Go tests with live integrations opt-in
	go test -v -count=1 ./...

serve-mcp: ## Serve MCP over stdio
	go run .

serve-cli: ## Serve the CLI projection
	go run . --cli

clean: ## Remove local generated or build output
	rm -f descriptor.binpb

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

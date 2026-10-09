.DEFAULT_GOAL := help
.PHONY: generate descriptor serve-mcp serve-cli test clean lint fmt

generate: ## Regenerate this adapter's exact descriptor graph and Go bindings
	cd .. && uv run scripts/generate-go-adapters --bindings predictfun

descriptor: generate ## Rebuild descriptor and bindings from the same graph

lint: ## Lint the canonical source and Go implementation
	cd proto && buf lint
	go vet ./...

fmt: ## Format protobuf and Go source
	cd proto && buf format -w
	gofmt -w .

serve-mcp: ## Serve MCP over stdio
	go run .

serve-cli: ## Serve the CLI projection
	go run . --cli

test: ## Run Go tests with live integrations opt-in
	go test -v -count=1 ./...

clean: ## Remove local generated or build output
	rm -rf descriptor.binpb predictfun/

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

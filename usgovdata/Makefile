.DEFAULT_GOAL := help
.PHONY: generate descriptor lint fmt serve-mcp serve-cli test clean

generate: ## Regenerate this adapter's exact descriptor graph and Go bindings
	cd .. && uv run scripts/generate-go-adapters --bindings usgovdata

descriptor: generate ## Rebuild descriptor and bindings from the same graph

lint: ## Lint the canonical source and Go implementation
	cd proto && buf lint
	go vet ./...

fmt: ## Format protobuf and Go source
	cd proto && buf format -w
	gofmt -w .

test: ## Run Go tests with live integrations opt-in
	go test -v -count=1 ./...

serve-mcp: ## Serve MCP over stdio
	go run .

serve-cli: ## Serve the CLI projection
	go run . --cli

clean: ## Remove local generated or build output
	rm -rf proto/usgovdata/v1/*.pb.go descriptor.binpb

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

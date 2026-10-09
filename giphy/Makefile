.DEFAULT_GOAL := help
.PHONY: generate descriptor build test clean lint fmt serve-mcp serve-cli

generate: ## Regenerate this adapter's exact descriptor graph and Go bindings
	cd .. && uv run scripts/generate-go-adapters --bindings giphy

descriptor: generate ## Rebuild descriptor and bindings from the same graph

build: generate ## Build this adapter locally
	go build -o giphy-mcp .

test: ## Run Go tests with live integrations opt-in
	go test -v -count=1 ./...

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

clean: ## Remove local generated or build output
	rm -rf descriptor.binpb giphy-mcp giphy/v1/giphy.pb.go

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

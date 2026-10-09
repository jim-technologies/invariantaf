.DEFAULT_GOAL := help
.PHONY: generate descriptor lint fmt test test-go test-py serve-go serve-py clean

generate: ## Regenerate exact descriptor and native language bindings
	cd .. && uv run scripts/generate-go-adapters --bindings geminipredictions
	cd .. && python3 scripts/generate-python-adapters --write geminipredictions

descriptor: generate ## Rebuild descriptor and bindings from the same graph

lint: ## Lint the canonical source and Go implementation
	cd proto && buf lint
	go vet ./...
	ruff check src/

fmt: ## Format protobuf and Go source
	cd proto && buf format -w
	gofmt -w .
	ruff format src/ tests/ main.py

test: test-go test-py ## Run Go tests with live integrations opt-in

test-go:
	go test -v -count=1 ./...

test-py:
	uv run python -m pytest tests/ -v

serve-go:
	go run .

serve-py:
	uv run python main.py

clean: ## Remove local generated or build output
	rm -rf descriptor.binpb src/geminipredictions_mcp/gen/geminipredictions/ proto/geminipredictions/v1/*.pb.go

.PHONY: help
help: ## List adapter targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z0-9_-]+:.*##/ { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

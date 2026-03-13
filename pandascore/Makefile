.PHONY: generate descriptor lint fmt serve-mcp serve-cli test test-go test-py clean

generate:
	cd proto && buf dep update
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	cd proto && buf lint
	go vet ./...
	ruff check src/ tests/ main.py

fmt:
	cd proto && buf format -w
	gofmt -w .
	ruff format src/ tests/ main.py

test: test-go test-py

test-go:
	go test -v -count=1 ./...

test-py:
	uv run python -m pytest tests/ -v

serve-mcp:
	go run .

serve-cli:
	go run . --cli

serve-mcp-py:
	uv run python main.py

serve-cli-py:
	uv run python main.py --cli

clean:
	rm -rf descriptor.binpb src/pandascore_mcp/gen/pandascore/ proto/pandascore/v1/*.pb.go

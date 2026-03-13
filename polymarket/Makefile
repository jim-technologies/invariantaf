.PHONY: generate descriptor lint fmt serve-mcp serve-cli test test-go test-python clean

generate:
	cd proto && buf dep update
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	cd proto && buf lint
	ruff check src/
	go vet ./...

fmt:
	cd proto && buf format -w
	ruff format src/
	gofmt -w .

serve-mcp:
	uv run python main.py

serve-cli:
	uv run python main.py --cli

serve-mcp-go:
	go run .

serve-cli-go:
	go run . --cli

test: test-python test-go

test-python:
	uv run python -m pytest tests/ -v

test-go:
	go test -v -count=1 ./...

clean:
	rm -rf descriptor.binpb src/gen/polymarket/ proto/polymarket/v1/*.pb.go

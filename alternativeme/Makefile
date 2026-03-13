.PHONY: generate descriptor lint fmt serve-mcp serve-cli test clean

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

serve-mcp:
	go run .

serve-cli:
	go run . --cli

test:
	go test -v -count=1 ./...

test-python:
	uv run python -m pytest tests/ -v

clean:
	rm -rf descriptor.binpb src/alternativeme_mcp/gen/alternativeme/ proto/alternativeme/v1/*.pb.go

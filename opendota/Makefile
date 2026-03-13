.PHONY: generate descriptor test test-go test-py serve-go serve-py lint fmt clean

generate:
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

test: test-go test-py

test-go:
	go test -v -count=1 ./...

test-py:
	uv run python -m pytest tests/ -v

serve-go:
	go run . --cli

serve-py:
	uv run python main.py

lint:
	cd proto && buf lint
	go vet ./...
	ruff check src/

fmt:
	cd proto && buf format -w
	gofmt -w .
	ruff format src/

clean:
	rm -rf descriptor.binpb src/gen/opendota/

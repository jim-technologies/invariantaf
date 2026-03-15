.PHONY: generate descriptor lint fmt test test-go test-py serve-go serve-py clean

generate:
	cd proto && buf dep update
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	go vet ./...
	ruff check src/

fmt:
	cd proto && buf format -w
	gofmt -w .
	ruff format src/ tests/ main.py

test: test-go test-py

test-go:
	go test -v -count=1 ./...

test-py:
	uv run python -m pytest tests/ -v

serve-go:
	go run .

serve-py:
	uv run python main.py

clean:
	rm -rf descriptor.binpb src/gen/polymarket/ proto/polymarket/v1/*.pb.go

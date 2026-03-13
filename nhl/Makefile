.PHONY: generate descriptor lint fmt serve-mcp serve-cli test clean

generate:
	cd proto && buf dep update
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	cd proto && buf lint
	ruff check src/ tests/ main.py

fmt:
	cd proto && buf format -w
	ruff format src/ tests/ main.py

serve-mcp:
	uv run python main.py

serve-cli:
	uv run python main.py --cli

test:
	uv run python -m pytest tests/ -v

clean:
	rm -rf descriptor.binpb src/nhl_mcp/gen/nhl/

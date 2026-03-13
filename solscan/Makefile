.PHONY: generate descriptor serve test clean

generate:
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	cd proto && buf lint
	ruff check src/

fmt:
	cd proto && buf format -w
	ruff format src/

serve-mcp:
	uv run python main.py

serve-cli:
	uv run python main.py --cli

test:
	uv run python -m pytest tests/ -v

clean:
	rm -rf descriptor.binpb src/solscan_mcp/gen/solscan/

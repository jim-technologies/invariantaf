# AlphaVantage MCP Server

Alpha Vantage market-data MCP server built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

## Coverage

Exposes 10 typed tools via `AlphaVantageService`:

- `GetQuote`
- `SearchSymbol`
- `GetDailyTimeSeries`
- `GetWeeklyTimeSeries`
- `GetMonthlyTimeSeries`
- `GetSMA`
- `GetRSI`
- `GetMACD`
- `GetCompanyOverview`
- `GetEarnings`

## Authentication

Requires:

- `ALPHA_VANTAGE_API_KEY`

Optional base URL override:

- `ALPHA_VANTAGE_BASE_URL` (default `https://www.alphavantage.co/query`)

## Quick start

```bash
cd alphavantage
uv sync
make generate

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli AlphaVantageService GetQuote -r '{"symbol":"AAPL"}'

# HTTP
uv run python main.py --http 8080
```

## Regenerate

```bash
make generate
```

## Run tests

```bash
make test
```

## Source docs

- https://www.alphavantage.co/documentation/

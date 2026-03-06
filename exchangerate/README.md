# ExchangeRate MCP Server

Foreign exchange rate data from the [Frankfurter API](https://www.frankfurter.app/), backed by the European Central Bank (30+ currencies).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetLatestRates` | No | Get the latest exchange rates for a base currency |
| `GetLatestForCurrencies` | No | Get the latest rates for specific target currencies |
| `Convert` | No | Convert an amount from one currency to another at the latest rate |
| `GetHistoricalRates` | No | Get exchange rates for a specific historical date |
| `GetTimeSeries` | No | Get a time series of exchange rates between two dates |
| `ListCurrencies` | No | List all supported currencies with their full names |
| `GetHistoricalForCurrencies` | No | Get historical rates for specific target currencies on a given date |
| `ConvertHistorical` | No | Convert an amount between currencies at a historical rate |
| `GetTimeSeriesForPair` | No | Get a time series for a specific currency pair |
| `GetLatestAll` | No | Get all latest rates with the default EUR base |

## Quick start

```bash
# Install
cd exchangerate
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli ExchangeRateService Convert -r '{"from": "USD", "to": "EUR", "amount": 100}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "exchangerate": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/exchangerate", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

# FRED MCP Server

U.S. economic data from [FRED](https://fred.stlouisfed.org/) (Federal Reserve Economic Data), the most comprehensive source of economic time series maintained by the Federal Reserve Bank of St. Louis (800,000+ series).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetSeries` | Yes | Get metadata for an economic data series |
| `GetSeriesObservations` | Yes | Get the actual data points for a series over time |
| `SearchSeries` | Yes | Search for economic data series by keywords |
| `GetCategory` | Yes | Get a FRED category by ID |
| `GetCategoryChildren` | Yes | Get child categories of a parent category |
| `GetCategorySeries` | Yes | Get all series within a FRED category |
| `GetRelease` | Yes | Get metadata for an economic data release |
| `GetReleaseDates` | Yes | Get release dates for economic data |
| `GetReleaseSeries` | Yes | Get all series associated with a release |
| `GetSeriesCategories` | Yes | Get the categories that a series belongs to |

## Quick start

```bash
# Install
cd fred
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli FREDService GetSeries -r '{"series_id": "GDP"}'
uv run python main.py --cli FREDService GetSeriesObservations -r '{"series_id": "CPIAUCSL", "observation_start": "2024-01-01"}'
uv run python main.py --cli FREDService SearchSeries -r '{"search_text": "unemployment rate"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Requires a free API key from https://fred.stlouisfed.org/docs/api/api_key.html. Set the `FRED_API_KEY` environment variable.

## Key series IDs

| Series ID | Description |
|-----------|-------------|
| `GDP` | Gross Domestic Product (quarterly) |
| `CPIAUCSL` | Consumer Price Index — inflation measure (monthly) |
| `UNRATE` | Civilian Unemployment Rate (monthly) |
| `FEDFUNDS` | Federal Funds Effective Rate (monthly) |
| `DGS10` | 10-Year Treasury Constant Maturity Rate (daily) |
| `SP500` | S&P 500 Index (daily) |
| `PAYEMS` | Total Nonfarm Payrolls (monthly) |
| `M2SL` | M2 Money Stock (monthly) |
| `HOUST` | Housing Starts (monthly) |
| `DEXUSEU` | U.S. / Euro Foreign Exchange Rate (daily) |

## MCP config

```json
{
  "mcpServers": {
    "fred": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/fred", "python", "main.py"],
      "env": {
        "FRED_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

# Finnhub MCP Server

Real-time stock market data from [Finnhub](https://finnhub.io/), covering US stocks, analyst recommendations, insider trading, and financial metrics.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetQuote` | Yes | Get real-time stock quote with price, change, high/low |
| `SearchSymbol` | Yes | Search for stocks by name or ticker symbol |
| `GetCompanyProfile` | Yes | Get company info: industry, market cap, IPO date, logo |
| `GetCompanyNews` | Yes | Get latest news articles for a company |
| `GetEarningsCalendar` | Yes | Get upcoming and past earnings dates |
| `GetRecommendationTrends` | Yes | Get analyst buy/sell/hold recommendations |
| `GetInsiderTransactions` | Yes | Get insider trading activity |
| `GetMarketNews` | Yes | Get general market news |
| `GetPeers` | Yes | Get similar companies/peers |
| `GetBasicFinancials` | Yes | Get key financial metrics: P/E, EPS, debt ratio, margins |

## Quick start

```bash
# Install
cd finnhub
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
FINNHUB_API_KEY=your-key uv run python main.py

# Run as CLI
FINNHUB_API_KEY=your-key uv run python main.py --cli FinnhubService GetQuote -r '{"symbol": "AAPL"}'

# Run as HTTP server
FINNHUB_API_KEY=your-key uv run python main.py --http 8080
```

## Authentication

Requires a free API key from [finnhub.io](https://finnhub.io/). Set `FINNHUB_API_KEY` environment variable.

## MCP config

```json
{
  "mcpServers": {
    "finnhub": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/finnhub", "python", "main.py"],
      "env": {
        "FINNHUB_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

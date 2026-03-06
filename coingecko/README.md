# CoinGecko MCP Server

Cryptocurrency market data from [CoinGecko](https://www.coingecko.com/), the world's largest independent crypto data aggregator (15,000+ coins).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetPrice` | No | Get current prices for one or more coins |
| `Search` | No | Search for coins, exchanges, and categories by keyword |
| `GetTrending` | No | Get trending coins, NFTs, and categories in the last 24 hours |
| `GetMarkets` | No | Get a ranked list of coins by market cap |
| `GetCoin` | No | Get detailed information about a specific coin |
| `GetMarketChart` | No | Get historical price chart data for a coin |
| `GetOHLC` | No | Get OHLC candlestick data for a coin |
| `GetGlobal` | No | Get global cryptocurrency market statistics |
| `GetCategories` | No | Get a list of coin categories with market data |
| `GetExchangeRates` | No | Get BTC exchange rates against all supported currencies |

## Quick start

```bash
# Install
cd coingecko
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli CoinGeckoService GetPrice -r '{"ids": "bitcoin,ethereum", "vs_currency": "usd"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Optional. Set `COINGECKO_API_KEY` for higher rate limits. Free tier works without a key.

## MCP config

```json
{
  "mcpServers": {
    "coingecko": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/coingecko", "python", "main.py"],
      "env": {
        "COINGECKO_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

# Alpaca MCP Server

Stock and crypto trading via [Alpaca](https://alpaca.markets/), a commission-free brokerage API.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Description |
|------|-------------|
| `GetAccount` | Get account info: buying power, equity, cash, portfolio value |
| `GetPositions` | Get all open positions with P&L |
| `GetPosition` | Get a single position by symbol |
| `PlaceOrder` | Place a market/limit/stop/stop-limit order |
| `GetOrders` | Get recent orders with status filter |
| `CancelOrder` | Cancel an order by ID |
| `GetAsset` | Get asset details: tradable, fractionable, class |
| `GetBars` | Get historical price bars (OHLCV candles) |
| `GetLatestQuote` | Get latest bid/ask quote |
| `GetLatestTrade` | Get latest trade price |

## Quick start

```bash
# Install
cd alpaca
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli AlpacaService GetAccount
uv run python main.py --cli AlpacaService PlaceOrder -r '{"symbol":"AAPL","qty":10,"side":"buy","type":"market","time_in_force":"day"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Requires `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` environment variables.

By default connects to the **paper trading** environment. Set `ALPACA_LIVE=true` to use real money.

## MCP config

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/alpaca", "python", "main.py"],
      "env": {
        "ALPACA_API_KEY": "your-api-key",
        "ALPACA_SECRET_KEY": "your-secret-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

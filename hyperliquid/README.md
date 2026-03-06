# Hyperliquid MCP Server

Trade on [Hyperliquid](https://hyperliquid.xyz) — the largest on-chain perpetual futures DEX — from any AI agent, CLI, or HTTP client.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetMeta` | No | List all 229+ tradable perpetual assets with leverage limits |
| `GetAllMids` | No | Mid prices for every asset |
| `GetOrderbook` | No | L2 order book (20 levels per side) |
| `GetCandles` | No | OHLCV candlestick data (1m to 1d) |
| `GetAccountState` | No* | Positions, margins, PnL, liquidation prices |
| `GetOpenOrders` | No* | Resting limit orders |
| `GetFills` | No* | Trade execution history |
| `PlaceOrder` | Yes | Limit/IOC/post-only orders |
| `CancelOrder` | Yes | Cancel by order ID |
| `MarketOpen` | Yes | Market buy/sell with slippage |
| `MarketClose` | Yes | Close entire position at market |
| `UpdateLeverage` | Yes | Set cross/isolated leverage |
| `Transfer` | Yes | Send USDC to another address |

*Needs wallet address but no private key.

## Quick start

```bash
# Install
cd hyperliquid
uv venv && uv pip install -e .

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli HyperliquidService GetAllMids
uv run python main.py --cli HyperliquidService GetOrderbook -r '{"coin":"BTC"}'

# Run as HTTP server
uv run python main.py --http 8080
# curl -X POST http://localhost:8080/hyperliquid.v1.HyperliquidService/GetAllMids -d '{}'
```

## Authentication

Read-only tools (market data, account state) work without authentication.

For trading, set your Hyperliquid API wallet private key:

```bash
export HYPERLIQUID_PRIVATE_KEY="0x..."
export HYPERLIQUID_ADDRESS="0x..."  # optional: your main account address
```

Generate an API wallet at https://app.hyperliquid.xyz/API (up to 3 per account).

## MCP config

Add to your Claude Desktop / Cursor config:

```json
{
  "mcpServers": {
    "hyperliquid": {
      "command": "uv",
      "args": ["run", "python", "/path/to/invariantaf/hyperliquid/main.py"],
      "env": {
        "HYPERLIQUID_PRIVATE_KEY": "0x...",
        "HYPERLIQUID_ADDRESS": "0x..."
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

Requires `buf` (included in flox environment).

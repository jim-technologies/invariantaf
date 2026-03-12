# Predict.fun MCP Server

Wraps the [Predict.fun](https://predict.fun/) prediction market API as an MCP server using [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

Predict.fun is a decentralized prediction market on the BNB Chain where users can trade on real-world event outcomes (sports, crypto, politics, etc.).

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| ListMarkets | Optional | List prediction markets with filters (status, category, pagination) |
| GetMarket | Optional | Get a single market by ID with full details |
| GetOrderbook | Optional | Get the orderbook (bids/asks) for a market |
| ListCategories | Optional | List available market categories |

## Authentication

- **Testnet**: No API key required. Set `PREDICTFUN_BASE_URL=https://api-testnet.predict.fun`
- **Mainnet**: Set `PREDICTFUN_API_KEY` to your API key (get one at https://predict.fun/)

Default rate limit: 240 requests per minute.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PREDICTFUN_API_KEY` | Mainnet only | API key for mainnet access |
| `PREDICTFUN_BASE_URL` | No | Override base URL (default: `https://api.predict.fun`) |

## MCP Config

```json
{
  "mcpServers": {
    "predictfun": {
      "command": "/path/to/predictfun-mcp",
      "env": {
        "PREDICTFUN_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Quick Start

```bash
# Generate proto + descriptor
make generate

# Run tests
make test

# Run as MCP server
make serve-mcp

# Run as CLI
make serve-cli

# Run as HTTP server
go run . --http 8080
```

## Regeneration

```bash
# Regenerate Go code and descriptor from proto
make generate

# Rebuild descriptor only
make descriptor
```

## API Reference

- [Predict.fun Developer Docs](https://dev.predict.fun/)
- [Predict.fun Python SDK](https://github.com/PredictDotFun/sdk-python)
- [API Swagger UI](https://api.predict.fun/docs)

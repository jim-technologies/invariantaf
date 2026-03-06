# DefiLlama MCP Server

DeFi analytics data from [DefiLlama](https://defillama.com/), the largest TVL aggregator for decentralized finance (5,000+ protocols, 200+ chains).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetProtocols` | No | List all DeFi protocols with their current TVL |
| `GetProtocol` | No | Get detailed information about a specific protocol |
| `GetTVL` | No | Get the current TVL for a single protocol |
| `GetChains` | No | Get TVL data for all blockchain networks |
| `GetGlobalTVL` | No | Get historical total DeFi TVL across all chains |
| `GetStablecoins` | No | List all stablecoins with market cap data |
| `GetYieldPools` | No | Get yield farming pool data across DeFi |
| `GetDexVolumes` | No | Get DEX trading volume overview |
| `GetFees` | No | Get protocol fee and revenue data |
| `GetStablecoinChains` | No | Get stablecoin market capitalization by chain |

## Quick start

```bash
# Install
cd defillama
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli DefiLlamaService GetProtocol -r '{"slug": "aave"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "defillama": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/defillama", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

# QuickNode MCP

QuickNode blockchain infrastructure adapter exposing 100+ API methods across 7
services as MCP tools, CLI commands, HTTP endpoints, and gRPC methods via
Invariant Protocol.

## Services

| Service | Methods | Description |
|---------|---------|-------------|
| QuickNodeConsoleService | 35 | Manage endpoints, billing, usage, rate limits, security, chains, tags |
| QuickNodeStreamsService | 10 | Create/manage real-time blockchain data streams |
| QuickNodeWebhooksService | 10 | Create/manage event-driven webhooks |
| QuickNodeKeyValueService | 13 | Persistent key-value lists and sets |
| QuickNodeIPFSService | 8 | Upload, pin, and manage IPFS objects |
| QuickNodeTokenNFTService | 19 | NFTs, tokens, transactions, ENS, block data (EVM JSON-RPC) |
| QuickNodeSolanaDASService | 12 | Solana Digital Asset Standard - assets, proofs, token accounts |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `QUICKNODE_API_KEY` | Yes (for REST APIs) | API key from dashboard.quicknode.com/api-keys |
| `QUICKNODE_ENDPOINT_URL` | Yes (for RPC methods) | Your QuickNode endpoint URL (e.g. https://xxx.quiknode.pro/yyy) |
| `QUICKNODE_API_BASE_URL` | No | Override REST API base URL (default: https://api.quicknode.com) |

The REST platform APIs (Console, Streams, Webhooks, KV Store, IPFS) use `QUICKNODE_API_KEY`.
The enhanced RPC methods (Token/NFT, Solana DAS) use `QUICKNODE_ENDPOINT_URL`.

## Quick Start

```bash
# Set credentials
export QUICKNODE_API_KEY="your-api-key"
export QUICKNODE_ENDPOINT_URL="https://your-endpoint.quiknode.pro/your-token"

# Generate protobuf code and descriptor
make generate

# Run as MCP server (stdio)
make serve-mcp

# Run as CLI
make serve-cli

# Run tests
make test
```

## CLI Examples

```bash
# List supported chains
go run . --cli ListChains

# List your endpoints
go run . --cli ListEndpoints

# Get endpoint metrics
go run . --cli GetEndpointMetrics -r '{"endpoint_id": "your-endpoint-id"}'

# Fetch NFTs for a wallet
go run . --cli FetchNFTs -r '{"wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'

# Resolve ENS name
go run . --cli ResolveENS -r '{"name_or_address": "vitalik.eth"}'

# Get token metadata
go run . --cli GetTokenMetadataByContractAddress -r '{"contract_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}'

# Create a KV list
go run . --cli CreateList -r '{"key": "tracked-wallets", "items": ["0xabc...", "0xdef..."]}'

# Get Solana asset
go run . --cli GetAsset -r '{"id": "FNftbceNV8PEr..."}'

# Estimate Solana priority fees
go run . --cli EstimatePriorityFees
```

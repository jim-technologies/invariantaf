# Polymarket MCP Server

Descriptor-driven Polymarket proxy built on [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

## Design

This project uses `Server.connect_http(...)` with `google.api.http` annotations.

- `PolymarketGammaService` -> `https://gamma-api.polymarket.com`
- `PolymarketClobService` -> `https://clob.polymarket.com`
- `PolymarketDataService` -> `https://data-api.polymarket.com`

All endpoints are exposed through typed protobuf request/response models (no `google.protobuf.Struct` / `google.protobuf.Value` payload wrappers).

## Authentication

Public methods do not require auth.

There are no L1-only RPCs currently exposed by this server.

L2-authenticated CLOB methods (8 total):

- Read-only: `GetOpenOrders`, `GetTrades`, `GetBalance`, `GetBalanceAllowance`
- Mutating: `PlaceOrder`, `CreateAndPostOrder`, `CancelOrder`, `CancelAllOrders`

`GetBalanceAllowance` is the docs-aligned RPC name; `GetBalance` is kept as a backward-compatible alias.

`main.py` builds these headers automatically when `POLYMARKET_PRIVATE_KEY` is set.

Authenticated CLOB RPCs are executed via `py-clob-client` paths (not only raw header injection), so behavior matches Polymarket SDK request construction.

Optional explicit API credentials:

- `POLYMARKET_API_KEY`
- `POLYMARKET_API_SECRET`
- `POLYMARKET_API_PASSPHRASE`

If these are not provided, credentials are derived via `py-clob-client` from `POLYMARKET_PRIVATE_KEY`.

Optional private-endpoint defaults aligned with `py-clob-client`:

- `POLYMARKET_SIGNATURE_TYPE` (`0` EOA, `1` POLY_PROXY, `2` POLY_GNOSIS_SAFE; default `0`)

## Base URL overrides

- `POLYMARKET_GAMMA_BASE_URL`
- `POLYMARKET_CLOB_BASE_URL`
- `POLYMARKET_DATA_BASE_URL`
- `POLYMARKET_CHAIN_ID` (default `137`)

Debug logging:

- `POLYMARKET_DEBUG=1` to print raw outbound HTTP request/response

## Quick start

```bash
cd polymarket
uv sync

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli PolymarketGammaService ListEvents -r '{"limit": 2}'
uv run python main.py --cli PolymarketClobService GetOrderbook -r '{"token_id":"<token-id>"}'

# Authenticated CLOB examples
uv run python main.py --cli PolymarketClobService GetBalanceAllowance -r '{"asset_type":"COLLATERAL","signature_type":2}'
uv run python main.py --cli PolymarketClobService PlaceOrder -r '{"order":{"salt":"<salt>","maker":"<maker>","signer":"<signer>","taker":"<taker-or-zero>","token_id":"<token-id>","maker_amount":"<maker-amount>","taker_amount":"<taker-amount>","expiration":"<expiration>","nonce":"<nonce>","fee_rate_bps":"<fee-bps>","side":"BUY","signature_type":2,"signature":"<sig>"},"order_type":"GTC","post_only":false}'
uv run python main.py --cli PolymarketClobService CreateAndPostOrder -r '{"token_id":"<token-id>","price":0.42,"size":10,"side":"BUY"}'
uv run python main.py --cli PolymarketClobService CancelOrder -r '{"order_id":"<order-id>"}'
uv run python main.py --cli PolymarketClobService CancelAllOrders

# HTTP
uv run python main.py --http 8080
```

## Regenerate

```bash
make generate
```

## Run tests

```bash
uv run python -m pytest tests -q
```

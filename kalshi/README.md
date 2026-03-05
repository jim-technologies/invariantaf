# Kalshi MCP Server

Descriptor-driven Kalshi Trade API proxy built from the Kalshi OpenAPI spec:
- Source spec: `https://docs.kalshi.com/openapi.yaml`
- Vendored spec: `openapi/kalshi.openapi.yaml`
- Coverage: all OpenAPI operations (85 operations)

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

## Design

This project uses `Server.connect_http(...)` with `google.api.http` annotations generated from OpenAPI.

- RPC methods map 1:1 to Kalshi operation IDs.
- Request messages include explicit path/query fields and schema-typed JSON `body`.
- Response messages use schema-typed `data` models generated from OpenAPI where possible.
- `google.protobuf.Value` is used only for OpenAPI-ambiguous shapes (e.g. free-form objects, union-like fields, some delete/command endpoints without concrete response schema).

## Authentication

Public endpoints work without auth.

Private endpoints require Kalshi headers:
- `KALSHI-ACCESS-KEY`
- `KALSHI-ACCESS-SIGNATURE`
- `KALSHI-ACCESS-TIMESTAMP`

Set these via env vars (the runtime maps them to outbound headers):
- `KALSHI_ACCESS_KEY`
- `KALSHI_ACCESS_SIGNATURE`
- `KALSHI_ACCESS_TIMESTAMP`

## Quick start

```bash
cd kalshi
uv sync

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli KalshiService GetExchangeStatus
uv run python main.py --cli KalshiService GetHistoricalMarket -r '{"ticker":"INX-24DEC31-T100"}'

# HTTP
uv run python main.py --http 8080
```

## Regenerate

```bash
make generate
```

## Run tests

```bash
# Local + mocked tests
uv run python -m pytest tests -q

# Live Kalshi public endpoint tests
KALSHI_RUN_LIVE_TESTS=1 \
  uv run python -m pytest tests/test_integration.py::TestLiveKalshiAPI -q
```

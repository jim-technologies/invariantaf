# Bybit MCP Server

Descriptor-driven Bybit V5 REST proxy built on [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

## Coverage

This adapter is generated from Bybit's official V5 API explorer YAML (`openapi/v5/*.yaml`, sourced from `bybit-exchange/docs`) and currently exposes **85 operations** across:

- `BybitAccountService`
- `BybitAssetService`
- `BybitBackupService`
- `BybitLtService`
- `BybitMarketService`
- `BybitPositionService`
- `BybitSpotMarginUtaService`
- `BybitTradeService`
- `BybitUserService`

All RPCs share the standard Bybit envelope response:
`retCode`, `retMsg`, `result`, `retExtInfo`, `time`.

## Authentication

Public methods need no auth.

Private methods are signed automatically with Bybit HMAC headers:

- `X-BAPI-API-KEY`
- `X-BAPI-SIGN`
- `X-BAPI-TIMESTAMP`
- `X-BAPI-RECV-WINDOW`
- `X-BAPI-SIGN-TYPE` (default `2`)

Set:

- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`

Optional:

- `BYBIT_RECV_WINDOW` (default `5000`)
- `BYBIT_SIGN_TYPE` (default `2`)
- `BYBIT_REFERER` (for broker flows)

## Base URL

By default this uses mainnet `https://api.bybit.com`.

Override with:

- `BYBIT_BASE_URL`

## Quick start

```bash
cd bybit
uv sync
make generate

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli BybitMarketService Time
uv run python main.py --cli BybitAccountService Wallet -r '{"accountType":"UNIFIED"}'

# HTTP
uv run python main.py --http 8080
```

## Regenerate

```bash
make generate
```

Generation script:

- `scripts/generate_from_openapi.py`

## Run tests

```bash
make test
```

## Source docs

- V5 guide: https://bybit-exchange.github.io/docs/v5/guide
- Docs repo: https://github.com/bybit-exchange/docs

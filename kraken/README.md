# Kraken MCP Server

Kraken Spot REST + Futures REST exposed as MCP tools, built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

Coverage in this implementation:
- Spot REST
  - `GetServerTime`, `GetSystemStatus`, `GetTradableAssetPairs`, `GetTickerInformation`, `GetOrderBook`
  - `GetAccountBalance`, `GetOpenOrders`, `AddOrder`, `CancelOrder`, `CancelAllOrders`, `CancelAllOrdersAfter`
- Futures REST
  - `GetInstruments`, `GetTickers`, `GetOrderbook`
  - `SendOrder`, `CancelOrder`, `GetOpenOrders`, `GetOpenPositions`, `GetFills`

The proto is strongly typed for request/response models from Kraken docs (maps are used where Kraken returns dynamic symbol keys).

## Authentication

Public endpoints need no auth.

Spot private endpoints:
- `KRAKEN_SPOT_API_KEY`
- `KRAKEN_SPOT_API_SECRET` (base64 secret)

Futures private endpoints:
- `KRAKEN_FUTURES_API_KEY`
- `KRAKEN_FUTURES_API_SECRET` (base64 secret)

Fallback for both (if service-specific vars are unset):
- `KRAKEN_API_KEY`
- `KRAKEN_API_SECRET`

Optional base URL overrides:
- `KRAKEN_SPOT_BASE_URL` (default `https://api.kraken.com/0`)
- `KRAKEN_FUTURES_BASE_URL` (default `https://futures.kraken.com/derivatives/api/v3`)

## Quick start

```bash
cd kraken
uv sync
make generate

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli KrakenSpotService GetServerTime
uv run python main.py --cli KrakenSpotService GetTickerInformation -r '{"pair":"XBTUSD"}'

# HTTP projection
uv run python main.py --http 8080
```

## Tests

```bash
cd kraken
make test
```

## Source docs

- Spot Add Order: https://docs.kraken.com/api/docs/rest-api/add-order/
- Futures Send Order: https://docs.kraken.com/api/docs/futures-api/trading/send-order/
- Spot auth guide: https://docs.kraken.com/api/docs/guides/spot-rest-auth/
- Futures REST guide: https://docs.kraken.com/api/docs/guides/futures-rest/

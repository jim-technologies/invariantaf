"""AlpacaService — wraps the Alpaca Trading API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb


class AlpacaService:
    """Implements AlpacaService RPCs via the Alpaca REST API."""

    def __init__(self):
        self._api_key = os.environ.get("ALPACA_API_KEY", "")
        self._secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        live = os.environ.get("ALPACA_LIVE", "").lower() == "true"
        self._base_url = (
            "https://api.alpaca.markets" if live else "https://paper-api.alpaca.markets"
        )
        self._data_url = "https://data.alpaca.markets"
        self._http = httpx.Client(
            timeout=30,
            headers={
                "APCA-API-KEY-ID": self._api_key,
                "APCA-API-SECRET-KEY": self._secret_key,
            },
        )

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{self._base_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict | None = None) -> Any:
        resp = self._http.post(f"{self._base_url}{path}", json=body or {})
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> None:
        resp = self._http.delete(f"{self._base_url}{path}")
        resp.raise_for_status()

    def _get_data(self, path: str, params: dict | None = None) -> Any:
        """Market data endpoints use a different base URL."""
        resp = self._http.get(f"{self._data_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    # --- Account ---

    def GetAccount(self, request: Any, context: Any = None) -> pb.GetAccountResponse:
        raw = self._get("/v2/account")
        return pb.GetAccountResponse(
            id=raw.get("id", ""),
            status=raw.get("status", ""),
            currency=raw.get("currency", ""),
            buying_power=float(raw.get("buying_power", 0)),
            cash=float(raw.get("cash", 0)),
            portfolio_value=float(raw.get("portfolio_value", 0)),
            equity=float(raw.get("equity", 0)),
            last_equity=float(raw.get("last_equity", 0)),
            long_market_value=float(raw.get("long_market_value", 0)),
            short_market_value=float(raw.get("short_market_value", 0)),
            pattern_day_trader=raw.get("pattern_day_trader", False),
            trading_blocked=raw.get("trading_blocked", False),
            account_blocked=raw.get("account_blocked", False),
        )

    # --- Positions ---

    def GetPositions(self, request: Any, context: Any = None) -> pb.GetPositionsResponse:
        raw = self._get("/v2/positions")
        resp = pb.GetPositionsResponse()
        for p in raw:
            resp.positions.append(_raw_to_position(p))
        return resp

    def GetPosition(self, request: Any, context: Any = None) -> pb.Position:
        raw = self._get(f"/v2/positions/{request.symbol}")
        return _raw_to_position(raw)

    # --- Orders ---

    def PlaceOrder(self, request: Any, context: Any = None) -> pb.PlaceOrderResponse:
        body: dict[str, Any] = {
            "symbol": request.symbol,
            "side": request.side,
            "type": request.type,
            "time_in_force": request.time_in_force or "day",
        }
        if request.qty:
            body["qty"] = str(request.qty)
        if request.notional:
            body["notional"] = str(request.notional)
        if request.limit_price:
            body["limit_price"] = str(request.limit_price)
        if request.stop_price:
            body["stop_price"] = str(request.stop_price)
        # Remove keys that ended up as None or empty.
        body = {k: v for k, v in body.items() if v is not None}

        raw = self._post("/v2/orders", body)
        return pb.PlaceOrderResponse(
            id=raw.get("id", ""),
            status=raw.get("status", ""),
            symbol=raw.get("symbol", ""),
            qty=str(raw.get("qty", "")),
            side=raw.get("side", ""),
            type=raw.get("type", ""),
            time_in_force=raw.get("time_in_force", ""),
            created_at=raw.get("created_at", ""),
        )

    def GetOrders(self, request: Any, context: Any = None) -> pb.GetOrdersResponse:
        params: dict[str, Any] = {}
        if request.status:
            params["status"] = request.status
        if request.limit:
            params["limit"] = request.limit
        raw = self._get("/v2/orders", params)
        resp = pb.GetOrdersResponse()
        for o in raw:
            resp.orders.append(_raw_to_order(o))
        return resp

    def CancelOrder(self, request: Any, context: Any = None) -> pb.CancelOrderResponse:
        try:
            self._delete(f"/v2/orders/{request.order_id}")
            return pb.CancelOrderResponse(success=True)
        except httpx.HTTPStatusError as e:
            return pb.CancelOrderResponse(success=False, error=str(e))
        except Exception as e:
            return pb.CancelOrderResponse(success=False, error=str(e))

    # --- Assets ---

    def GetAsset(self, request: Any, context: Any = None) -> pb.GetAssetResponse:
        raw = self._get(f"/v2/assets/{request.symbol}")
        return pb.GetAssetResponse(
            id=raw.get("id", ""),
            asset_class=raw.get("class", ""),
            exchange=raw.get("exchange", ""),
            symbol=raw.get("symbol", ""),
            name=raw.get("name", ""),
            tradable=raw.get("tradable", False),
            fractionable=raw.get("fractionable", False),
            status=raw.get("status", ""),
            shortable=raw.get("shortable", False),
            marginable=raw.get("marginable", False),
        )

    # --- Market Data ---

    def GetBars(self, request: Any, context: Any = None) -> pb.GetBarsResponse:
        params: dict[str, Any] = {}
        if request.timeframe:
            params["timeframe"] = request.timeframe
        if request.start:
            params["start"] = request.start
        if request.end:
            params["end"] = request.end
        if request.limit:
            params["limit"] = request.limit

        raw = self._get_data(f"/v2/stocks/{request.symbol}/bars", params)
        resp = pb.GetBarsResponse(symbol=request.symbol)
        for b in raw.get("bars", []) or []:
            resp.bars.append(pb.Bar(
                timestamp=b.get("t", ""),
                open=b.get("o", 0),
                high=b.get("h", 0),
                low=b.get("l", 0),
                close=b.get("c", 0),
                volume=b.get("v", 0),
                vwap=b.get("vw", 0),
                trade_count=b.get("n", 0),
            ))
        return resp

    def GetLatestQuote(self, request: Any, context: Any = None) -> pb.GetLatestQuoteResponse:
        raw = self._get_data(f"/v2/stocks/{request.symbol}/quotes/latest")
        quote = raw.get("quote", {})
        return pb.GetLatestQuoteResponse(
            symbol=request.symbol,
            bid_price=quote.get("bp", 0),
            bid_size=quote.get("bs", 0),
            ask_price=quote.get("ap", 0),
            ask_size=quote.get("as", 0),
            timestamp=quote.get("t", ""),
        )

    def GetLatestTrade(self, request: Any, context: Any = None) -> pb.GetLatestTradeResponse:
        raw = self._get_data(f"/v2/stocks/{request.symbol}/trades/latest")
        trade = raw.get("trade", {})
        return pb.GetLatestTradeResponse(
            symbol=request.symbol,
            price=trade.get("p", 0),
            size=trade.get("s", 0),
            exchange=trade.get("x", ""),
            timestamp=trade.get("t", ""),
        )


def _raw_to_position(raw: dict) -> pb.Position:
    """Convert a raw Alpaca API position dict to a Position proto."""
    return pb.Position(
        symbol=raw.get("symbol", ""),
        qty=str(raw.get("qty", "")),
        avg_entry_price=str(raw.get("avg_entry_price", "")),
        current_price=str(raw.get("current_price", "")),
        market_value=str(raw.get("market_value", "")),
        unrealized_pl=str(raw.get("unrealized_pl", "")),
        unrealized_plpc=str(raw.get("unrealized_plpc", "")),
        asset_class=raw.get("asset_class", ""),
        side=raw.get("side", ""),
        exchange=raw.get("exchange", ""),
        cost_basis=str(raw.get("cost_basis", "")),
    )


def _raw_to_order(raw: dict) -> pb.Order:
    """Convert a raw Alpaca API order dict to an Order proto."""
    return pb.Order(
        id=raw.get("id", ""),
        symbol=raw.get("symbol", ""),
        qty=str(raw.get("qty", "")),
        filled_qty=str(raw.get("filled_qty", "")),
        side=raw.get("side", ""),
        type=raw.get("type", ""),
        time_in_force=raw.get("time_in_force", ""),
        limit_price=str(raw.get("limit_price", "") or ""),
        stop_price=str(raw.get("stop_price", "") or ""),
        filled_avg_price=str(raw.get("filled_avg_price", "") or ""),
        status=raw.get("status", ""),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        submitted_at=raw.get("submitted_at", ""),
        filled_at=raw.get("filled_at", "") or "",
        asset_class=raw.get("asset_class", ""),
    )

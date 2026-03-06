"""HyperliquidService — wraps the official Python SDK into proto request/response methods."""

from __future__ import annotations

import os
from typing import Any

import eth_account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from hyperliquid_mcp.gen.hyperliquid.v1 import hyperliquid_pb2 as pb

# Map proto CandleInterval enum to SDK interval strings.
_INTERVAL_MAP = {
    pb.CANDLE_INTERVAL_1M: "1m",
    pb.CANDLE_INTERVAL_5M: "5m",
    pb.CANDLE_INTERVAL_15M: "15m",
    pb.CANDLE_INTERVAL_1H: "1h",
    pb.CANDLE_INTERVAL_4H: "4h",
    pb.CANDLE_INTERVAL_1D: "1d",
}


class HyperliquidService:
    """Implements HyperliquidService RPCs by delegating to the official SDK."""

    def __init__(
        self,
        *,
        base_url: str = constants.MAINNET_API_URL,
        private_key: str | None = None,
        account_address: str | None = None,
    ):
        self._info = Info(base_url, skip_ws=True)
        self._exchange: Exchange | None = None

        # Allow private key from env var.
        key = private_key or os.environ.get("HYPERLIQUID_PRIVATE_KEY")
        addr = account_address or os.environ.get("HYPERLIQUID_ADDRESS")

        if key:
            wallet = eth_account.Account.from_key(key)
            self._exchange = Exchange(
                wallet,
                base_url,
                account_address=addr,
            )

    def _require_exchange(self) -> Exchange:
        if self._exchange is None:
            raise ValueError(
                "This operation requires authentication. "
                "Set HYPERLIQUID_PRIVATE_KEY environment variable or pass private_key at init."
            )
        return self._exchange

    # --- Market Data (read-only) ---

    def GetMeta(self, request: Any, context: Any = None) -> pb.GetMetaResponse:
        raw = self._info.meta()
        resp = pb.GetMetaResponse()
        for asset in raw.get("universe", []):
            resp.assets.append(
                pb.AssetInfo(
                    name=asset["name"],
                    size_decimals=asset.get("szDecimals", 0),
                    max_leverage=asset.get("maxLeverage", 0),
                )
            )
        return resp

    def GetAllMids(self, request: Any, context: Any = None) -> pb.GetAllMidsResponse:
        raw = self._info.all_mids()
        resp = pb.GetAllMidsResponse()
        for coin, price in raw.items():
            resp.mids[coin] = str(price)
        return resp

    def GetOrderbook(self, request: Any, context: Any = None) -> pb.GetOrderbookResponse:
        raw = self._info.l2_snapshot(request.coin)
        resp = pb.GetOrderbookResponse()
        levels = raw.get("levels", [[], []])
        for bid in levels[0]:
            resp.bids.append(pb.OrderbookLevel(price=bid["px"], size=bid["sz"]))
        for ask in levels[1]:
            resp.asks.append(pb.OrderbookLevel(price=ask["px"], size=ask["sz"]))
        return resp

    def GetCandles(self, request: Any, context: Any = None) -> pb.GetCandlesResponse:
        interval = _INTERVAL_MAP.get(request.interval, "1h")
        raw = self._info.candles_snapshot(
            request.coin, interval, request.start_time, request.end_time
        )
        resp = pb.GetCandlesResponse()
        for c in raw:
            resp.candles.append(
                pb.Candle(
                    time=c.get("t", 0),
                    open=c.get("o", ""),
                    high=c.get("h", ""),
                    low=c.get("l", ""),
                    close=c.get("c", ""),
                    volume=c.get("v", ""),
                )
            )
        return resp

    # --- Account Data (read-only, needs address) ---

    def GetAccountState(self, request: Any, context: Any = None) -> pb.GetAccountStateResponse:
        raw = self._info.user_state(request.address)
        resp = pb.GetAccountStateResponse(
            account_value=raw.get("marginSummary", {}).get("accountValue", ""),
            margin_used=raw.get("marginSummary", {}).get("totalMarginUsed", ""),
            withdrawable=raw.get("withdrawable", ""),
        )

        cms = raw.get("crossMarginSummary", {})
        if cms:
            resp.cross_margin_summary.CopyFrom(
                pb.CrossMarginSummary(
                    account_value=cms.get("accountValue", ""),
                    total_notional=cms.get("totalNtlPos", ""),
                    total_margin_used=cms.get("totalMarginUsed", ""),
                    total_raw_usd=cms.get("totalRawUsd", ""),
                )
            )

        for ap in raw.get("assetPositions", []):
            pos = ap.get("position", {})
            leverage_val = ""
            lev = pos.get("leverage", {})
            if isinstance(lev, dict):
                leverage_val = str(lev.get("value", ""))

            resp.positions.append(
                pb.Position(
                    coin=pos.get("coin", ""),
                    size=pos.get("szi", ""),
                    entry_price=pos.get("entryPx", ""),
                    liquidation_price=pos.get("liquidationPx", ""),
                    unrealized_pnl=pos.get("unrealizedPnl", ""),
                    return_on_equity=pos.get("returnOnEquity", ""),
                    leverage=leverage_val,
                    margin_used=pos.get("marginUsed", ""),
                )
            )
        return resp

    def GetOpenOrders(self, request: Any, context: Any = None) -> pb.GetOpenOrdersResponse:
        raw = self._info.open_orders(request.address)
        resp = pb.GetOpenOrdersResponse()
        for o in raw:
            side = pb.SIDE_BUY if o.get("side") == "A" else pb.SIDE_SELL
            resp.orders.append(
                pb.OpenOrder(
                    coin=o.get("coin", ""),
                    side=side,
                    limit_price=o.get("limitPx", ""),
                    size=o.get("sz", ""),
                    order_id=o.get("oid", 0),
                    timestamp=o.get("timestamp", 0),
                )
            )
        return resp

    def GetFills(self, request: Any, context: Any = None) -> pb.GetFillsResponse:
        raw = self._info.user_fills(request.address)
        resp = pb.GetFillsResponse()
        for f in raw:
            side = pb.SIDE_BUY if f.get("side") == "A" else pb.SIDE_SELL
            resp.fills.append(
                pb.Fill(
                    coin=f.get("coin", ""),
                    price=f.get("px", ""),
                    size=f.get("sz", ""),
                    side=side,
                    time=f.get("time", 0),
                    fee=f.get("fee", ""),
                    closed_pnl=f.get("closedPnl", ""),
                )
            )
        return resp

    # --- Trading (authenticated) ---

    def PlaceOrder(self, request: Any, context: Any = None) -> pb.PlaceOrderResponse:
        exchange = self._require_exchange()
        is_buy = request.side == pb.SIDE_BUY
        tif_map = {
            pb.TIME_IN_FORCE_GTC: "Gtc",
            pb.TIME_IN_FORCE_IOC: "Ioc",
            pb.TIME_IN_FORCE_ALO: "Alo",
        }
        tif = tif_map.get(request.time_in_force, "Gtc")
        order_type = {"limit": {"tif": tif}}

        try:
            result = exchange.order(
                request.coin,
                is_buy,
                float(request.size),
                float(request.price),
                order_type,
                reduce_only=request.reduce_only,
            )
            return _parse_order_result(result)
        except Exception as e:
            return pb.PlaceOrderResponse(success=False, error=str(e))

    def CancelOrder(self, request: Any, context: Any = None) -> pb.CancelOrderResponse:
        exchange = self._require_exchange()
        try:
            result = exchange.cancel(request.coin, request.order_id)
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses and statuses[0] == "success":
                    return pb.CancelOrderResponse(success=True)
                return pb.CancelOrderResponse(success=False, error=str(statuses))
            return pb.CancelOrderResponse(success=False, error=str(result))
        except Exception as e:
            return pb.CancelOrderResponse(success=False, error=str(e))

    def MarketOpen(self, request: Any, context: Any = None) -> pb.MarketOpenResponse:
        exchange = self._require_exchange()
        is_buy = request.side == pb.SIDE_BUY
        slippage = request.slippage if request.HasField("slippage") else 0.01

        try:
            result = exchange.market_open(request.coin, is_buy, float(request.size), slippage=slippage)
            parsed = _parse_order_result(result)
            return pb.MarketOpenResponse(success=parsed.success, status=parsed.status, error=parsed.error)
        except Exception as e:
            return pb.MarketOpenResponse(success=False, error=str(e))

    def MarketClose(self, request: Any, context: Any = None) -> pb.MarketCloseResponse:
        exchange = self._require_exchange()
        slippage = request.slippage if request.HasField("slippage") else 0.01

        try:
            result = exchange.market_close(request.coin, slippage=slippage)
            if result is None:
                return pb.MarketCloseResponse(success=False, error="No open position found for " + request.coin)
            parsed = _parse_order_result(result)
            return pb.MarketCloseResponse(success=parsed.success, status=parsed.status, error=parsed.error)
        except Exception as e:
            return pb.MarketCloseResponse(success=False, error=str(e))

    def UpdateLeverage(self, request: Any, context: Any = None) -> pb.UpdateLeverageResponse:
        exchange = self._require_exchange()
        try:
            result = exchange.update_leverage(request.leverage, request.coin, is_cross=request.is_cross)
            if result.get("status") == "ok":
                return pb.UpdateLeverageResponse(success=True)
            return pb.UpdateLeverageResponse(success=False, error=str(result))
        except Exception as e:
            return pb.UpdateLeverageResponse(success=False, error=str(e))

    def Transfer(self, request: Any, context: Any = None) -> pb.TransferResponse:
        exchange = self._require_exchange()
        try:
            result = exchange.usd_transfer(float(request.amount), request.destination)
            if result.get("status") == "ok":
                return pb.TransferResponse(success=True)
            return pb.TransferResponse(success=False, error=str(result))
        except Exception as e:
            return pb.TransferResponse(success=False, error=str(e))


def _parse_order_result(result: dict) -> pb.PlaceOrderResponse:
    """Parse the SDK order/market_open response into a PlaceOrderResponse."""
    if result.get("status") != "ok":
        return pb.PlaceOrderResponse(success=False, error=str(result))

    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
    if not statuses:
        return pb.PlaceOrderResponse(success=False, error="No status returned")

    s = statuses[0]
    if isinstance(s, dict):
        if "resting" in s:
            return pb.PlaceOrderResponse(
                success=True,
                order_id=s["resting"].get("oid", 0),
                status="resting",
            )
        if "filled" in s:
            return pb.PlaceOrderResponse(
                success=True,
                order_id=s["filled"].get("oid", 0),
                status="filled",
            )
        if "error" in s:
            return pb.PlaceOrderResponse(success=False, error=s["error"])

    return pb.PlaceOrderResponse(success=False, error=str(s))

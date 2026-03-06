"""Kraken Spot/Futures service implementation for Invariant Protocol."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from collections.abc import Iterable
from typing import Any

import httpx
from google.protobuf import json_format

from kraken_mcp.gen.kraken.v1 import kraken_pb2 as pb

DEFAULT_SPOT_BASE_URL = "https://api.kraken.com/0"
DEFAULT_FUTURES_BASE_URL = "https://futures.kraken.com/derivatives/api/v3"


class KrakenService:
    """Implements KrakenSpotService + KrakenFuturesService."""

    def __init__(
        self,
        *,
        spot_base_url: str = DEFAULT_SPOT_BASE_URL,
        futures_base_url: str = DEFAULT_FUTURES_BASE_URL,
        timeout: float = 15.0,
    ):
        self._spot_base_url = spot_base_url.rstrip("/")
        self._futures_base_url = futures_base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # Spot handlers
    # -------------------------

    def GetServerTime(self, request: Any, context: Any = None) -> pb.GetServerTimeResponse:
        payload = self._spot_public_get("/public/Time")
        return self._parse_message(payload, pb.GetServerTimeResponse)

    def GetSystemStatus(self, request: Any, context: Any = None) -> pb.GetSystemStatusResponse:
        payload = self._spot_public_get("/public/SystemStatus")
        return self._parse_message(payload, pb.GetSystemStatusResponse)

    def GetTradableAssetPairs(
        self, request: pb.GetTradableAssetPairsRequest, context: Any = None
    ) -> pb.GetTradableAssetPairsResponse:
        query: dict[str, Any] = {}
        if request.pair:
            query["pair"] = request.pair
        self._add_opt(query, "aclass_base", request, "aclass_base")
        self._add_opt(query, "info", request, "info")
        self._add_opt(query, "country_code", request, "country_code")

        payload = self._spot_public_get("/public/AssetPairs", query)
        self._normalize_spot_errors(payload)
        self._transform_spot_asset_pairs(payload)
        return self._parse_message(payload, pb.GetTradableAssetPairsResponse)

    def GetTickerInformation(
        self, request: pb.GetTickerInformationRequest, context: Any = None
    ) -> pb.GetTickerInformationResponse:
        query: dict[str, Any] = {}
        if request.pair:
            query["pair"] = request.pair
        self._add_opt(query, "asset_class", request, "asset_class")

        payload = self._spot_public_get("/public/Ticker", query)
        self._normalize_spot_errors(payload)
        self._transform_spot_ticker(payload)
        return self._parse_message(payload, pb.GetTickerInformationResponse)

    def GetOrderBook(self, request: pb.GetOrderBookRequest, context: Any = None) -> pb.GetOrderBookResponse:
        query: dict[str, Any] = {"pair": request.pair}
        if self._has_field(request, "count"):
            query["count"] = request.count
        self._add_opt(query, "asset_class", request, "asset_class")

        payload = self._spot_public_get("/public/Depth", query)
        self._normalize_spot_errors(payload)
        self._transform_spot_orderbook(payload)
        return self._parse_message(payload, pb.GetOrderBookResponse)

    def GetAccountBalance(
        self, request: pb.GetAccountBalanceRequest, context: Any = None
    ) -> pb.GetAccountBalanceResponse:
        params: dict[str, Any] = {}
        self._add_opt(params, "nonce", request, "nonce")
        self._add_opt(params, "rebase_multiplier", request, "rebase_multiplier")

        payload = self._spot_private_post("/private/Balance", params)
        return self._parse_message(payload, pb.GetAccountBalanceResponse)

    def _spot_get_open_orders(
        self, request: pb.GetOpenOrdersRequest, context: Any = None
    ) -> pb.GetOpenOrdersResponse:
        params: dict[str, Any] = {}
        self._add_opt(params, "nonce", request, "nonce")
        self._add_opt(params, "trades", request, "trades")
        self._add_opt(params, "userref", request, "userref")
        self._add_opt(params, "cl_ord_id", request, "cl_ord_id")
        self._add_opt(params, "rebase_multiplier", request, "rebase_multiplier")

        payload = self._spot_private_post("/private/OpenOrders", params)
        self._normalize_spot_errors(payload)
        return self._parse_message(payload, pb.GetOpenOrdersResponse)

    def AddOrder(self, request: pb.AddOrderRequest, context: Any = None) -> pb.AddOrderResponse:
        params: dict[str, Any] = {
            "ordertype": request.ordertype,
            "type": request.type,
            "volume": request.volume,
            "pair": request.pair,
        }

        self._add_opt(params, "nonce", request, "nonce")
        self._add_opt(params, "userref", request, "userref")
        self._add_opt(params, "cl_ord_id", request, "cl_ord_id")
        self._add_opt(params, "displayvol", request, "displayvol")
        self._add_opt(params, "asset_class", request, "asset_class")
        self._add_opt(params, "price", request, "price")
        self._add_opt(params, "price2", request, "price2")
        self._add_opt(params, "trigger", request, "trigger")
        self._add_opt(params, "leverage", request, "leverage")
        self._add_opt(params, "reduce_only", request, "reduce_only")
        self._add_opt(params, "stptype", request, "stptype")
        self._add_opt(params, "oflags", request, "oflags")
        self._add_opt(params, "timeinforce", request, "timeinforce")
        self._add_opt(params, "starttm", request, "starttm")
        self._add_opt(params, "expiretm", request, "expiretm")
        self._add_opt(params, "close[ordertype]", request, "close_ordertype")
        self._add_opt(params, "close[price]", request, "close_price")
        self._add_opt(params, "close[price2]", request, "close_price2")
        self._add_opt(params, "deadline", request, "deadline")
        self._add_opt(params, "validate", request, "validate")

        payload = self._spot_private_post("/private/AddOrder", params)
        self._normalize_spot_errors(payload)
        return self._parse_message(payload, pb.AddOrderResponse)

    def _spot_cancel_order(
        self, request: pb.CancelOrderRequest, context: Any = None
    ) -> pb.CancelOrderResponse:
        params: dict[str, Any] = {}
        self._add_opt(params, "nonce", request, "nonce")
        if self._has_field(request, "txid"):
            params["txid"] = request.txid
        elif self._has_field(request, "txid_int"):
            params["txid"] = request.txid_int
        self._add_opt(params, "cl_ord_id", request, "cl_ord_id")

        payload = self._spot_private_post("/private/CancelOrder", params)
        self._normalize_spot_errors(payload)
        return self._parse_message(payload, pb.CancelOrderResponse)

    def CancelAllOrders(
        self, request: pb.CancelAllOrdersRequest, context: Any = None
    ) -> pb.CancelAllOrdersResponse:
        params: dict[str, Any] = {}
        self._add_opt(params, "nonce", request, "nonce")
        payload = self._spot_private_post("/private/CancelAll", params)
        self._normalize_spot_errors(payload)
        return self._parse_message(payload, pb.CancelAllOrdersResponse)

    def CancelAllOrdersAfter(
        self, request: pb.CancelAllOrdersAfterRequest, context: Any = None
    ) -> pb.CancelAllOrdersAfterResponse:
        params: dict[str, Any] = {"timeout": request.timeout}
        self._add_opt(params, "nonce", request, "nonce")

        payload = self._spot_private_post("/private/CancelAllOrdersAfter", params)
        self._normalize_spot_errors(payload)
        return self._parse_message(payload, pb.CancelAllOrdersAfterResponse)

    def GetOpenOrders(self, request: Any, context: Any = None):
        if isinstance(request, pb.GetOpenOrdersRequest):
            return self._spot_get_open_orders(request, context)
        if isinstance(request, pb.GetFuturesOpenOrdersRequest):
            return self._futures_get_open_orders(request, context)
        raise TypeError(f"unsupported request type for GetOpenOrders: {type(request).__name__}")

    def CancelOrder(self, request: Any, context: Any = None):
        if isinstance(request, pb.CancelOrderRequest):
            return self._spot_cancel_order(request, context)
        if isinstance(request, pb.CancelFuturesOrderRequest):
            return self._futures_cancel_order(request, context)
        raise TypeError(f"unsupported request type for CancelOrder: {type(request).__name__}")

    # -------------------------
    # Futures handlers
    # -------------------------

    def GetInstruments(self, request: Any, context: Any = None) -> pb.GetInstrumentsResponse:
        payload = self._futures_request("GET", "/instruments", private=False)
        return self._parse_message(payload, pb.GetInstrumentsResponse)

    def GetTickers(self, request: pb.GetTickersRequest, context: Any = None) -> pb.GetTickersResponse:
        query: dict[str, Any] = {}
        if request.symbol:
            query["symbol"] = list(request.symbol)

        payload = self._futures_request("GET", "/tickers", query=query, private=False)
        return self._parse_message(payload, pb.GetTickersResponse)

    def GetOrderbook(self, request: pb.GetOrderbookRequest, context: Any = None) -> pb.GetOrderbookResponse:
        payload = self._futures_request(
            "GET",
            "/orderbook",
            query={"symbol": request.symbol},
            private=False,
        )
        self._transform_futures_orderbook(payload)
        return self._parse_message(payload, pb.GetOrderbookResponse)

    def SendOrder(self, request: pb.SendOrderRequest, context: Any = None) -> pb.SendOrderResponse:
        params: dict[str, Any] = {
            "orderType": request.order_type,
            "symbol": request.symbol,
            "side": request.side,
            "size": request.size,
        }
        self._add_opt(params, "processBefore", request, "process_before")
        self._add_opt(params, "limitPrice", request, "limit_price")
        self._add_opt(params, "stopPrice", request, "stop_price")
        self._add_opt(params, "cliOrdId", request, "cli_ord_id")
        self._add_opt(params, "triggerSignal", request, "trigger_signal")
        self._add_opt(params, "reduceOnly", request, "reduce_only")
        self._add_opt(params, "trailingStopMaxDeviation", request, "trailing_stop_max_deviation")
        self._add_opt(params, "trailingStopDeviationUnit", request, "trailing_stop_deviation_unit")
        self._add_opt(params, "limitPriceOffsetValue", request, "limit_price_offset_value")
        self._add_opt(params, "limitPriceOffsetUnit", request, "limit_price_offset_unit")
        self._add_opt(params, "broker", request, "broker")

        payload = self._futures_request("POST", "/sendorder", query=params, private=True)
        return self._parse_message(payload, pb.SendOrderResponse)

    def _futures_cancel_order(
        self, request: pb.CancelFuturesOrderRequest, context: Any = None
    ) -> pb.CancelFuturesOrderResponse:
        params: dict[str, Any] = {}
        self._add_opt(params, "processBefore", request, "process_before")
        self._add_opt(params, "order_id", request, "order_id")
        self._add_opt(params, "cliOrdId", request, "cli_ord_id")

        payload = self._futures_request("POST", "/cancelorder", query=params, private=True)
        return self._parse_message(payload, pb.CancelFuturesOrderResponse)

    def _futures_get_open_orders(
        self, request: pb.GetFuturesOpenOrdersRequest, context: Any = None
    ) -> pb.GetFuturesOpenOrdersResponse:
        payload = self._futures_request("GET", "/openorders", private=True)
        return self._parse_message(payload, pb.GetFuturesOpenOrdersResponse)

    def GetOpenPositions(
        self, request: pb.GetOpenPositionsRequest, context: Any = None
    ) -> pb.GetOpenPositionsResponse:
        payload = self._futures_request("GET", "/openpositions", private=True)
        return self._parse_message(payload, pb.GetOpenPositionsResponse)

    def GetFills(self, request: pb.GetFillsRequest, context: Any = None) -> pb.GetFillsResponse:
        query: dict[str, Any] = {}
        self._add_opt(query, "lastFillTime", request, "last_fill_time")

        payload = self._futures_request("GET", "/fills", query=query, private=True)
        return self._parse_message(payload, pb.GetFillsResponse)

    # -------------------------
    # HTTP + auth helpers
    # -------------------------

    def _spot_public_get(self, path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self._build_url(self._spot_base_url, path, query=query)
        return self._request_json("GET", url, headers={"Accept": "application/json"})

    def _spot_private_post(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        api_key, api_secret = self._spot_credentials()

        params = dict(params)
        if "nonce" not in params or params["nonce"] in (None, 0, ""):
            params["nonce"] = int(time.time() * 1000)

        body = self._encode_params(params)
        url = self._build_url(self._spot_base_url, path)
        sign_path = urllib.parse.urlsplit(url).path
        nonce = str(params["nonce"])

        sha256_digest = hashlib.sha256((nonce + body).encode()).digest()
        signature_input = sign_path.encode() + sha256_digest
        signature = base64.b64encode(
            hmac.new(base64.b64decode(api_secret), signature_input, hashlib.sha512).digest()
        ).decode()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "API-Key": api_key,
            "API-Sign": signature,
        }
        payload = self._request_json("POST", url, headers=headers, body=body)
        self._normalize_spot_errors(payload)
        return payload

    def _futures_request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        *,
        private: bool,
    ) -> dict[str, Any]:
        query = query or {}
        method = method.upper()
        headers: dict[str, str] = {"Accept": "application/json"}

        body_text = ""
        if method == "GET":
            url = self._build_url(self._futures_base_url, path, query=query)
        else:
            url = self._build_url(self._futures_base_url, path)
            body_text = self._encode_params(query)
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if private:
            api_key, api_secret = self._futures_credentials()
            nonce = str(int(time.time() * 1000))

            parsed = urllib.parse.urlsplit(url)
            endpoint_component = parsed.path
            if parsed.query:
                endpoint_component += f"?{parsed.query}"

            prehash = f"{body_text}{nonce}{endpoint_component}"
            digest = hashlib.sha256(prehash.encode()).digest()
            authent = base64.b64encode(
                hmac.new(base64.b64decode(api_secret), digest, hashlib.sha512).digest()
            ).decode()

            headers["APIKey"] = api_key
            headers["Authent"] = authent
            headers["Nonce"] = nonce

        return self._request_json(method, url, headers=headers, body=body_text)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: str | None = None,
    ) -> dict[str, Any]:
        response = self._client.request(
            method,
            url,
            headers=headers,
            content=body.encode() if body else None,
        )

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"{method} {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"{method} {url}: HTTP {response.status_code}: {payload}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"{method} {url}: expected object JSON response, got {type(payload).__name__}")
        return payload

    # -------------------------
    # Response transforms
    # -------------------------

    def _normalize_spot_errors(self, payload: dict[str, Any]) -> None:
        errors = payload.get("error")
        if not isinstance(errors, list):
            return

        normalized: list[str] = []
        for item in errors:
            if isinstance(item, list):
                normalized.extend(str(x) for x in item)
            else:
                normalized.append(str(item))
        payload["error"] = normalized

    def _transform_spot_asset_pairs(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        if not isinstance(result, dict):
            return

        for pair_data in result.values():
            if not isinstance(pair_data, dict):
                continue
            pair_data["fees"] = self._transform_fee_levels(pair_data.get("fees"))
            pair_data["fees_maker"] = self._transform_fee_levels(pair_data.get("fees_maker"))

    def _transform_fee_levels(self, value: Any) -> list[dict[str, float]]:
        out: list[dict[str, float]] = []
        if not isinstance(value, list):
            return out

        for row in value:
            if isinstance(row, list) and len(row) >= 2:
                out.append(
                    {
                        "volume": float(row[0]),
                        "fee": float(row[1]),
                    }
                )
        return out

    def _transform_spot_ticker(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        if not isinstance(result, dict):
            return

        for ticker in result.values():
            if not isinstance(ticker, dict):
                continue
            ticker["a"] = self._array_to_price_level(ticker.get("a"))
            ticker["b"] = self._array_to_price_level(ticker.get("b"))
            ticker["c"] = self._array_to_trade_close(ticker.get("c"))
            ticker["v"] = self._array_to_two_value(ticker.get("v"))
            ticker["p"] = self._array_to_two_value(ticker.get("p"))
            ticker["t"] = self._array_to_trade_count(ticker.get("t"))
            ticker["l"] = self._array_to_two_value(ticker.get("l"))
            ticker["h"] = self._array_to_two_value(ticker.get("h"))

    def _transform_spot_orderbook(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        if not isinstance(result, dict):
            return

        for book in result.values():
            if not isinstance(book, dict):
                continue
            book["asks"] = self._array_levels_to_orderbook(book.get("asks"))
            book["bids"] = self._array_levels_to_orderbook(book.get("bids"))

    def _array_to_price_level(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, list):
            return {}
        return {
            "price": str(value[0]) if len(value) > 0 else "",
            "wholeLotVolume": str(value[1]) if len(value) > 1 else "",
            "lotVolume": str(value[2]) if len(value) > 2 else "",
        }

    def _array_to_trade_close(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, list):
            return {}
        return {
            "price": str(value[0]) if len(value) > 0 else "",
            "lotVolume": str(value[1]) if len(value) > 1 else "",
        }

    def _array_to_two_value(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, list):
            return {}
        return {
            "today": str(value[0]) if len(value) > 0 else "",
            "last24h": str(value[1]) if len(value) > 1 else "",
        }

    def _array_to_trade_count(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, list):
            return {}
        return {
            "today": int(value[0]) if len(value) > 0 else 0,
            "last24h": int(value[1]) if len(value) > 1 else 0,
        }

    def _array_levels_to_orderbook(self, levels: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not isinstance(levels, list):
            return out

        for raw in levels:
            if not isinstance(raw, list):
                continue
            level: dict[str, Any] = {
                "price": str(raw[0]) if len(raw) > 0 else "",
                "volume": str(raw[1]) if len(raw) > 1 else "",
                "timestamp": float(raw[2]) if len(raw) > 2 else 0,
            }
            if len(raw) > 3:
                level["misc"] = str(raw[3])
            out.append(level)
        return out

    def _transform_futures_orderbook(self, payload: dict[str, Any]) -> None:
        order_book = payload.get("orderBook")
        if not isinstance(order_book, dict):
            return

        for side in ("asks", "bids"):
            levels = order_book.get(side)
            parsed: list[dict[str, float]] = []
            if isinstance(levels, list):
                for row in levels:
                    if isinstance(row, list) and len(row) >= 2:
                        parsed.append({"price": float(row[0]), "size": float(row[1])})
            order_book[side] = parsed

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _build_url(self, base: str, path: str, query: dict[str, Any] | None = None) -> str:
        full = f"{base.rstrip('/')}{path}"
        if not query:
            return full

        query_string = self._encode_params(query)
        if not query_string:
            return full
        return f"{full}?{query_string}"

    def _encode_params(self, params: dict[str, Any]) -> str:
        pairs: list[tuple[str, str]] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, dict)):
                for item in value:
                    if item is None:
                        continue
                    pairs.append((key, self._to_http_scalar(item)))
                continue
            pairs.append((key, self._to_http_scalar(value)))

        return urllib.parse.urlencode(pairs, doseq=True)

    def _to_http_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int | float):
            return str(value)
        return str(value)

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False

    def _add_opt(self, out: dict[str, Any], out_name: str, request: Any, field_name: str) -> None:
        if self._has_field(request, field_name):
            out[out_name] = getattr(request, field_name)

    def _spot_credentials(self) -> tuple[str, str]:
        api_key = self._first_env("KRAKEN_SPOT_API_KEY", "KRAKEN_API_KEY")
        api_secret = self._first_env("KRAKEN_SPOT_API_SECRET", "KRAKEN_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("missing Kraken Spot credentials (KRAKEN_SPOT_API_KEY/KRAKEN_SPOT_API_SECRET)")
        return api_key, api_secret

    def _futures_credentials(self) -> tuple[str, str]:
        api_key = self._first_env("KRAKEN_FUTURES_API_KEY", "KRAKEN_API_KEY")
        api_secret = self._first_env("KRAKEN_FUTURES_API_SECRET", "KRAKEN_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError(
                "missing Kraken Futures credentials (KRAKEN_FUTURES_API_KEY/KRAKEN_FUTURES_API_SECRET)"
            )
        return api_key, api_secret

    def _first_env(self, *names: str) -> str:
        import os

        for name in names:
            value = (os.getenv(name) or "").strip()
            if value:
                return value
        return ""

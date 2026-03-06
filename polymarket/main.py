"""Polymarket MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
import sys
import time
import urllib.parse
from pathlib import Path
from threading import Lock
from typing import Any

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.polymarket.v1 import polymarket_pb2 as _polymarket_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"

DEFAULT_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_BASE_URL = "https://clob.polymarket.com"
DEFAULT_DATA_BASE_URL = "https://data-api.polymarket.com"
DEFAULT_CHAIN_ID = 137
DEFAULT_SIGNATURE_TYPE = 0

_CLOB_PRIVATE_METHODS = {
    "/polymarket.v1.PolymarketClobService/PlaceOrder",
    "/polymarket.v1.PolymarketClobService/CreateAndPostOrder",
    "/polymarket.v1.PolymarketClobService/CancelOrder",
    "/polymarket.v1.PolymarketClobService/CancelAllOrders",
    "/polymarket.v1.PolymarketClobService/GetOpenOrders",
    "/polymarket.v1.PolymarketClobService/GetTrades",
    "/polymarket.v1.PolymarketClobService/GetBalance",
    "/polymarket.v1.PolymarketClobService/GetBalanceAllowance",
}

_CLOB_BALANCE_METHODS = {
    "/polymarket.v1.PolymarketClobService/GetBalance",
    "/polymarket.v1.PolymarketClobService/GetBalanceAllowance",
}

_CLOB_SIGNATURE_TYPE_METHODS = {
    "/polymarket.v1.PolymarketClobService/CreateAndPostOrder",
    "/polymarket.v1.PolymarketClobService/GetBalance",
    "/polymarket.v1.PolymarketClobService/GetBalanceAllowance",
}

_CLOB_CURSOR_METHODS = {
    "/polymarket.v1.PolymarketClobService/GetOpenOrders",
    "/polymarket.v1.PolymarketClobService/GetTrades",
}


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _env_bool(name: str) -> bool:
    value = _env(name).lower()
    return value in {"1", "true", "yes", "y", "on"}


def _consume_flag(args: list[str], flag: str) -> tuple[bool, list[str]]:
    if flag not in args:
        return False, args
    return True, [arg for arg in args if arg != flag]


def _truncate_text(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...<truncated {len(value) - limit} chars>"


def _redact_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    redacted: dict[str, str] = {}
    sensitive = {
        "authorization",
        "poly_signature",
        "poly_passphrase",
        "poly_api_key",
        "x-api-key",
        "api-key",
        "api_key",
    }
    for key, value in headers.items():
        if key.lower() in sensitive:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def _install_http_debug_hook() -> None:
    from invariant import http_client as invariant_http_client

    if getattr(invariant_http_client, "_polymarket_debug_hook_installed", False):
        return

    original_request = invariant_http_client.httpx.request

    def debug_request(method: str, url: str, **kwargs: Any):
        started = time.perf_counter()
        headers = kwargs.get("headers") or {}
        content = kwargs.get("content")
        json_body = kwargs.get("json")
        timeout = kwargs.get("timeout")

        print(f"[polymarket-debug] >>> {method} {url}", file=sys.stderr)
        print(
            f"[polymarket-debug] >>> headers={_redact_headers(headers)} timeout={timeout}",
            file=sys.stderr,
        )
        if content is not None:
            if isinstance(content, bytes):
                body_text = content.decode("utf-8", errors="replace")
            else:
                body_text = str(content)
            print(
                f"[polymarket-debug] >>> body={_truncate_text(body_text)}",
                file=sys.stderr,
            )
        elif json_body is not None:
            print(
                f"[polymarket-debug] >>> json={_truncate_text(str(json_body))}",
                file=sys.stderr,
            )

        response = original_request(method, url, **kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        print(
            f"[polymarket-debug] <<< {response.status_code} {response.reason_phrase} ({elapsed_ms:.1f}ms)",
            file=sys.stderr,
        )
        print(
            f"[polymarket-debug] <<< headers={dict(response.headers)}",
            file=sys.stderr,
        )
        print(
            f"[polymarket-debug] <<< body={_truncate_text(response.text)}",
            file=sys.stderr,
        )
        return response

    invariant_http_client.httpx.request = debug_request
    invariant_http_client._polymarket_debug_hook_installed = True


def _read_chain_id() -> int:
    chain_id_raw = _env("POLYMARKET_CHAIN_ID") or str(DEFAULT_CHAIN_ID)
    try:
        return int(chain_id_raw)
    except ValueError as exc:
        raise SystemExit(f"POLYMARKET_CHAIN_ID must be an integer, got {chain_id_raw!r}") from exc


def _build_clob_client(clob_base_url: str, signature_type_default: int):
    private_key = _env("POLYMARKET_PRIVATE_KEY")
    if not private_key:
        return None

    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    funder = _env("POLYMARKET_FUNDER_ADDRESS") or None
    clob = ClobClient(
        clob_base_url,
        key=private_key,
        chain_id=_read_chain_id(),
        signature_type=signature_type_default,
        funder=funder,
    )

    api_key = _env("POLYMARKET_API_KEY")
    api_secret = _env("POLYMARKET_API_SECRET")
    api_passphrase = _env("POLYMARKET_API_PASSPHRASE")
    if api_key and api_secret and api_passphrase:
        clob.set_api_creds(
            ApiCreds(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            )
        )
    else:
        clob.set_api_creds(clob.create_or_derive_api_creds())
    return clob


def _build_clob_header_provider(clob):
    if clob is None:
        return None

    from py_clob_client.clob_types import RequestArgs
    from py_clob_client.headers.headers import create_level_2_headers

    def provider(req) -> dict[str, str] | None:
        if req.method_path not in _CLOB_PRIVATE_METHODS:
            return None

        path = urllib.parse.urlsplit(req.url).path or "/"
        body_text = req.body.decode("utf-8") if req.body else None
        request_args = RequestArgs(
            method=req.method,
            request_path=path,
            serialized_body=body_text,
        )
        return create_level_2_headers(clob.signer, clob.creds, request_args)

    return provider


def _read_signature_type() -> int:
    raw = _env("POLYMARKET_SIGNATURE_TYPE")
    if not raw:
        return DEFAULT_SIGNATURE_TYPE
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"POLYMARKET_SIGNATURE_TYPE must be an integer, got {raw!r}") from exc
    if value not in (0, 1, 2):
        raise SystemExit(
            f"POLYMARKET_SIGNATURE_TYPE must be one of 0, 1, 2; got {value!r}"
        )
    return value


def _build_clob_defaults_interceptor(signature_type_default: int):
    def interceptor(request, context, info, handler):
        return handler(request, context)

    return interceptor


class _PolymarketClobCompositeService:
    """Composite RPC handlers that stitch multiple CLOB operations together."""

    def __init__(self, clob_client, signature_type_default: int):
        self._clob = clob_client
        self._signature_type_default = signature_type_default
        self._lock = Lock()

    def _require_clob(self):
        import grpc
        from invariant.errors import InvariantError

        if self._clob is None:
            raise InvariantError(
                grpc.StatusCode.UNAUTHENTICATED,
                "CLOB authenticated method requires POLYMARKET_PRIVATE_KEY and CLOB L2 credentials",
            ) from None
        return self._clob

    @staticmethod
    def _parse_data(payload: dict[str, Any], out):
        import grpc
        from google.protobuf import json_format
        from invariant.errors import InvariantError

        try:
            json_format.ParseDict({"data": payload}, out, ignore_unknown_fields=True)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INTERNAL,
                f"decode response payload: {exc}",
            ) from None
        return out

    def PlaceOrder(self, request, _context):
        import grpc
        from invariant.errors import InvariantError
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()

        class _RawSignedOrder:
            def __init__(self, payload: dict[str, Any]):
                self._payload = payload

            def dict(self):
                return self._payload

        try:
            order = request.order
            raw_order = _RawSignedOrder(
                {
                    "salt": order.salt,
                    "maker": order.maker,
                    "signer": order.signer,
                    "taker": order.taker,
                    "tokenId": order.token_id,
                    "makerAmount": order.maker_amount,
                    "takerAmount": order.taker_amount,
                    "expiration": order.expiration,
                    "nonce": order.nonce,
                    "feeRateBps": order.fee_rate_bps,
                    "side": order.side,
                    "signatureType": order.signature_type,
                    "signature": order.signature,
                }
            )
            kwargs: dict[str, Any] = {}
            if request.order_type:
                kwargs["orderType"] = request.order_type
            if request.HasField("post_only"):
                kwargs["post_only"] = request.post_only
            posted = clob.post_order(raw_order, **kwargs)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"PlaceOrder failed: {exc}"
            ) from None

        out = polymarket_pb2.PlaceOrderResponse()
        return self._parse_data(posted, out)

    def CancelOrder(self, request, _context):
        import grpc
        from invariant.errors import InvariantError
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()

        order_id = (request.order_id or "").strip()

        try:
            canceled = clob.cancel(order_id)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"CancelOrder failed: {exc}"
            ) from None

        out = polymarket_pb2.CancelOrderResponse()
        return self._parse_data(canceled, out)

    def CancelAllOrders(self, _request, _context):
        import grpc
        from invariant.errors import InvariantError
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()

        try:
            canceled = clob.cancel_all()
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"CancelAllOrders failed: {exc}"
            ) from None

        out = polymarket_pb2.CancelAllOrdersResponse()
        return self._parse_data(canceled, out)

    def GetOpenOrders(self, request, _context):
        import grpc
        from invariant.errors import InvariantError
        from py_clob_client.clob_types import OpenOrderParams
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()
        params = OpenOrderParams(
            id=request.id or None,
            market=request.market or None,
            asset_id=request.asset_id or None,
        )
        if not any([params.id, params.market, params.asset_id]):
            params = None
        next_cursor = request.next_cursor or "MA=="

        try:
            rows = clob.get_orders(params=params, next_cursor=next_cursor)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"GetOpenOrders failed: {exc}"
            ) from None

        out = polymarket_pb2.GetOpenOrdersResponse()
        return self._parse_data(rows, out)

    def GetTrades(self, request, _context):
        import grpc
        from invariant.errors import InvariantError
        from py_clob_client.clob_types import TradeParams
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()
        params = TradeParams(
            id=request.id or None,
            maker_address=request.maker_address or None,
            market=request.market or None,
            asset_id=request.asset_id or None,
            before=request.before or None,
            after=request.after or None,
        )
        if not any(
            [params.id, params.maker_address, params.market, params.asset_id, params.before, params.after]
        ):
            params = None
        next_cursor = request.next_cursor or "MA=="

        try:
            rows = clob.get_trades(params=params, next_cursor=next_cursor)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"GetTrades failed: {exc}"
            ) from None

        out = polymarket_pb2.GetTradesResponse()
        return self._parse_data(rows, out)

    def _get_balance_allowance(self, request):
        import grpc
        from invariant.errors import InvariantError
        from py_clob_client.clob_types import BalanceAllowanceParams

        clob = self._require_clob()
        signature_type = -1
        if request.HasField("signature_type"):
            signature_type = request.signature_type

        params = BalanceAllowanceParams(
            asset_type=request.asset_type or None,
            token_id=request.token_id or None,
            signature_type=signature_type,
        )
        try:
            return clob.get_balance_allowance(params)
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"GetBalanceAllowance failed: {exc}"
            ) from None

    def GetBalance(self, request, _context):
        from gen.polymarket.v1 import polymarket_pb2

        payload = self._get_balance_allowance(request)
        out = polymarket_pb2.GetBalanceResponse()
        return self._parse_data(payload, out)

    def GetBalanceAllowance(self, request, _context):
        from gen.polymarket.v1 import polymarket_pb2

        payload = self._get_balance_allowance(request)
        out = polymarket_pb2.GetBalanceResponse()
        return self._parse_data(payload, out)

    def CreateAndPostOrder(self, request, _context):
        import grpc
        from invariant.errors import InvariantError
        from py_clob_client.clob_types import (
            OrderArgs,
            PartialCreateOrderOptions,
        )
        from gen.polymarket.v1 import polymarket_pb2

        clob = self._require_clob()

        order_kwargs: dict[str, Any] = {
            "token_id": request.token_id,
            "price": request.price,
            "size": request.size,
            "side": request.side,
        }
        if request.HasField("fee_rate_bps"):
            order_kwargs["fee_rate_bps"] = request.fee_rate_bps
        if request.HasField("nonce"):
            order_kwargs["nonce"] = request.nonce
        if request.HasField("expiration"):
            order_kwargs["expiration"] = request.expiration
        if request.HasField("taker"):
            order_kwargs["taker"] = request.taker

        order_args = OrderArgs(**order_kwargs)

        has_options = request.HasField("tick_size") or request.HasField("neg_risk")
        options = PartialCreateOrderOptions(
            tick_size=request.tick_size if request.HasField("tick_size") else None,
            neg_risk=request.neg_risk if request.HasField("neg_risk") else None,
        )

        try:
            with self._lock:
                if has_options:
                    posted = clob.create_and_post_order(order_args, options)
                else:
                    posted = clob.create_and_post_order(order_args)
        except InvariantError:
            raise
        except Exception as exc:
            raise InvariantError(
                grpc.StatusCode.INVALID_ARGUMENT, f"CreateAndPostOrder failed: {exc}"
            ) from None

        out = polymarket_pb2.CreateAndPostOrderResponse()
        return self._parse_data(posted, out)


def main() -> None:
    args = sys.argv[1:]
    debug_flag, args = _consume_flag(args, "--debug-http")
    if debug_flag or _env_bool("POLYMARKET_DEBUG"):
        _install_http_debug_hook()

    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="polymarket-mcp",
        version="0.2.0",
    )

    gamma_base = (_env("POLYMARKET_GAMMA_BASE_URL") or DEFAULT_GAMMA_BASE_URL).rstrip("/")
    clob_base = (_env("POLYMARKET_CLOB_BASE_URL") or DEFAULT_CLOB_BASE_URL).rstrip("/")
    data_base = (_env("POLYMARKET_DATA_BASE_URL") or DEFAULT_DATA_BASE_URL).rstrip("/")
    signature_type_default = _read_signature_type()

    # Align private endpoint defaults with py-clob-client behavior.
    server.use(_build_clob_defaults_interceptor(signature_type_default))

    clob_client = _build_clob_client(clob_base, signature_type_default)
    header_provider = _build_clob_header_provider(clob_client)
    if header_provider is not None:
        server.use_http_header_provider(header_provider)

    server.connect_http(gamma_base, service_name="polymarket.v1.PolymarketGammaService")
    server.connect_http(clob_base, service_name="polymarket.v1.PolymarketClobService")
    server.connect_http(data_base, service_name="polymarket.v1.PolymarketDataService")
    server.register(
        _PolymarketClobCompositeService(clob_client, signature_type_default),
        service_name="polymarket.v1.PolymarketClobService",
    )

    if "--cli" in args:
        idx = args.index("--cli")
        sys.argv = [sys.argv[0], *args[idx + 1 :]]
        server.serve(cli=True)
    elif "--http" in args:
        port = 8080
        idx = args.index("--http")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(http=port)
    elif "--grpc" in args:
        port = 50051
        idx = args.index("--grpc")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(grpc=port)
    else:
        server.serve(mcp=True)


if __name__ == "__main__":
    main()

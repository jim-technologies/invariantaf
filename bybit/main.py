"""Bybit V5 MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
import time
import urllib.parse
from pathlib import Path

import grpc
from invariant import Server
from invariant.errors import InvariantError

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.bybit.v1 import bybit_pb2 as _bybit_pb2  # noqa: F401

from bybit_mcp.spec_meta import PRIVATE_METHOD_PATHS, SERVICE_NAMES

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"
DEFAULT_MAINNET_BASE_URL = "https://api.bybit.com"
DEFAULT_RECV_WINDOW = 5000


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _read_base_url() -> str:
    explicit = _env("BYBIT_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    return DEFAULT_MAINNET_BASE_URL


def _read_recv_window() -> str:
    raw = _env("BYBIT_RECV_WINDOW")
    if not raw:
        return str(DEFAULT_RECV_WINDOW)
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"BYBIT_RECV_WINDOW must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise SystemExit("BYBIT_RECV_WINDOW must be greater than 0")
    return str(value)


def _build_bybit_header_provider(recv_window: str):
    referer = _env("BYBIT_REFERER")
    sign_type = _env("BYBIT_SIGN_TYPE") or "2"

    def provider(req):
        headers: dict[str, str] = {}
        if referer:
            headers["X-Referer"] = referer

        if req.method_path not in PRIVATE_METHOD_PATHS:
            return headers or None

        api_key = _env("BYBIT_API_KEY")
        api_secret = _env("BYBIT_API_SECRET")
        if not api_key or not api_secret:
            raise InvariantError(
                grpc.StatusCode.UNAUTHENTICATED,
                "private Bybit endpoint requires BYBIT_API_KEY and BYBIT_API_SECRET",
            )

        timestamp = str(int(time.time() * 1000))
        parsed = urllib.parse.urlsplit(req.url)

        if req.method.upper() == "GET":
            payload = parsed.query
        else:
            payload = req.body.decode("utf-8") if req.body else ""

        plain = f"{timestamp}{api_key}{recv_window}{payload}"
        signature = hmac.new(api_secret.encode(), plain.encode(), hashlib.sha256).hexdigest()

        headers.update(
            {
                "X-BAPI-API-KEY": api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "X-BAPI-SIGN-TYPE": sign_type,
            }
        )
        return headers

    return provider


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="bybit-mcp",
        version="0.1.0",
    )

    base_url = _read_base_url().rstrip("/")
    recv_window = _read_recv_window()

    server.use_http_header_provider(_build_bybit_header_provider(recv_window))

    for service_name in SERVICE_NAMES:
        server.connect_http(base_url, service_name=service_name)

    server.serve_from_argv()


if __name__ == "__main__":
    main()

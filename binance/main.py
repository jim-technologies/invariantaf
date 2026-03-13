"""Binance MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from binance_mcp.gen.binance.v1 import binance_pb2 as _binance_pb2  # noqa: F401
from binance_mcp.service import DEFAULT_BASE_URL, BinanceService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="binance-mcp",
        version="0.1.0",
    )

    base_url = (_env("BINANCE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = BinanceService(base_url=base_url)
    server.register(servicer, service_name="binance.v1.BinanceMarketService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

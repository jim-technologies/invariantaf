"""Kraken MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from kraken_mcp.gen.kraken.v1 import kraken_pb2 as _kraken_pb2  # noqa: F401
from kraken_mcp.service import DEFAULT_FUTURES_BASE_URL, DEFAULT_SPOT_BASE_URL, KrakenService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="kraken-mcp",
        version="0.1.0",
    )

    spot_base_url = (_env("KRAKEN_SPOT_BASE_URL") or DEFAULT_SPOT_BASE_URL).rstrip("/")
    futures_base_url = (_env("KRAKEN_FUTURES_BASE_URL") or DEFAULT_FUTURES_BASE_URL).rstrip("/")

    servicer = KrakenService(
        spot_base_url=spot_base_url,
        futures_base_url=futures_base_url,
    )

    server.register(servicer, service_name="kraken.v1.KrakenSpotService")
    server.register(servicer, service_name="kraken.v1.KrakenFuturesService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

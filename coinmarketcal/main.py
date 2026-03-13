"""CoinMarketCal MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from coinmarketcal_mcp.gen.coinmarketcal.v1 import coinmarketcal_pb2 as _coinmarketcal_pb2  # noqa: F401
from coinmarketcal_mcp.service import DEFAULT_BASE_URL, CoinMarketCalService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="coinmarketcal-mcp",
        version="0.1.0",
    )

    api_key = _env("COINMARKETCAL_API_KEY")
    base_url = (_env("COINMARKETCAL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = CoinMarketCalService(api_key=api_key, base_url=base_url)
    server.register(servicer, service_name="coinmarketcal.v1.CoinMarketCalService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

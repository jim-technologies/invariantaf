"""Kalshi MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.kalshi.v1 import kalshi_pb2 as _kalshi_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"
DEFAULT_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


def _configure_auth_env() -> None:
    # Kalshi private endpoints expect these headers.
    mappings = {
        "KALSHI_ACCESS_KEY": "INVARIANT_HTTP_HEADER_KALSHI_ACCESS_KEY",
        "KALSHI_ACCESS_SIGNATURE": "INVARIANT_HTTP_HEADER_KALSHI_ACCESS_SIGNATURE",
        "KALSHI_ACCESS_TIMESTAMP": "INVARIANT_HTTP_HEADER_KALSHI_ACCESS_TIMESTAMP",
    }
    for source, target in mappings.items():
        value = (os.getenv(source) or "").strip()
        if value:
            os.environ[target] = value
        else:
            os.environ.pop(target, None)


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="kalshi-mcp",
        version="0.1.0",
    )

    _configure_auth_env()
    base_url = (os.getenv("KALSHI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    server.connect_http(base_url, service_name="kalshi.v1.KalshiService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

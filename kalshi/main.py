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

    args = sys.argv[1:]
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

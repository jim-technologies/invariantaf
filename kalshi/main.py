"""Kalshi MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
import asyncio
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


def _projection_from_argv(argv: list[str]) -> dict:
    """Parse [--mcp|--cli|--http [port]|--grpc [port]] into serve() kwargs."""
    if not argv:
        return {"mcp": True}
    cmd = argv[0]
    if cmd in ("--mcp", "mcp", ""):
        return {"mcp": True}
    if cmd in ("--cli", "cli"):
        return {"cli": True}
    if cmd in ("--http", "http"):
        port = int(argv[1]) if len(argv) > 1 else 8080
        return {"http": port}
    if cmd in ("--grpc", "grpc"):
        port = int(argv[1]) if len(argv) > 1 else 50051
        return {"grpc": port}
    return {"mcp": True}


async def _serve(server: Server, modes: dict) -> None:
    if "grpc" in modes:
        native = server.grpc_server()
        native.add_insecure_port(f"[::]:{modes['grpc']}")
        await native.start()
        await native.wait_for_termination()
        return
    await server.serve_projections(**modes)


def main() -> None:
    server = Server.from_descriptor(str(DESCRIPTOR))

    _configure_auth_env()
    base_url = (os.getenv("KALSHI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    server.connect_http(base_url, service_name="kalshi.v1.KalshiService")

    asyncio.run(_serve(server, _projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

"""CoinMarketCal MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import asyncio
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

    api_key = _env("COINMARKETCAL_API_KEY")
    base_url = (_env("COINMARKETCAL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = CoinMarketCalService(api_key=api_key, base_url=base_url)
    server.register(servicer, service_name="coinmarketcal.v1.CoinMarketCalService")

    asyncio.run(_serve(server, _projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

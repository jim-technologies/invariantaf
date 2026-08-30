"""1inch DEX aggregator MCP server — powered by Invariant Protocol."""

import sys
import asyncio
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oneinch_mcp.service import OneInchService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


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


def main():
    server = Server.from_descriptor(str(DESCRIPTOR))
    servicer = OneInchService()
    server.register(servicer)

    asyncio.run(_serve(server, _projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

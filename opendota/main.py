"""OpenDota MCP server -- descriptor-driven HTTP client proxy via Invariant Protocol."""

from __future__ import annotations

import os
import asyncio
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.opendota.v1 import opendota_pb2 as _opendota_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"
DEFAULT_BASE_URL = "https://api.opendota.com/api"


def _configure_auth_env() -> None:
    api_key = (os.getenv("OPENDOTA_API_KEY") or "").strip()
    if not api_key:
        # No API key configured: ensure we do not forward Authorization at all.
        os.environ.pop("INVARIANT_HTTP_HEADER_AUTHORIZATION", None)
        return
    # Invariant connect_http reads outbound headers from INVARIANT_HTTP_HEADER_* env vars.
    os.environ["INVARIANT_HTTP_HEADER_AUTHORIZATION"] = f"Bearer {api_key}"


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

    _configure_auth_env()
    base_url = (os.getenv("OPENDOTA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    server.connect_http(base_url, service_name="opendota.v1.OpenDotaService")

    asyncio.run(_serve(server, _projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

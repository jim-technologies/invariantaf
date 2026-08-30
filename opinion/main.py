"""Opinion.trade MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
import asyncio
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.opinion.v1 import opinion_pb2 as _opinion_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"

DEFAULT_BASE_URL = "https://openapi.opinion.trade/openapi"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _build_auth_interceptor():
    """Attach the ``apikey`` header to every request when OPINION_API_KEY is set."""
    api_key = _env("OPINION_API_KEY")
    if not api_key:
        return None

    def provider(req) -> dict[str, str] | None:
        return {"apikey": api_key}

    return provider


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

    base_url = (_env("OPINION_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    header_provider = _build_auth_interceptor()
    if header_provider is not None:
        server.use_http_header_provider(header_provider)

    server.connect_http(base_url, service_name="opinion.v1.OpinionService")

    asyncio.run(_serve(server, _projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

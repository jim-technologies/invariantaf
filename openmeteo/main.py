"""Open-Meteo MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import asyncio
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from openmeteo_mcp.gen.openmeteo.v1 import openmeteo_pb2 as _openmeteo_pb2  # noqa: F401
from openmeteo_mcp.service import (
    DEFAULT_AIR_QUALITY_BASE_URL,
    DEFAULT_ARCHIVE_BASE_URL,
    DEFAULT_BASE_URL,
    DEFAULT_MARINE_BASE_URL,
    OpenMeteoService,
)

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


def main() -> None:
    server = Server.from_descriptor(str(DESCRIPTOR))

    base_url = (_env("OPENMETEO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    archive_base_url = (_env("OPENMETEO_ARCHIVE_BASE_URL") or DEFAULT_ARCHIVE_BASE_URL).rstrip("/")
    air_quality_base_url = (
        _env("OPENMETEO_AIR_QUALITY_BASE_URL") or DEFAULT_AIR_QUALITY_BASE_URL
    ).rstrip("/")
    marine_base_url = (_env("OPENMETEO_MARINE_BASE_URL") or DEFAULT_MARINE_BASE_URL).rstrip("/")

    servicer = OpenMeteoService(
        base_url=base_url,
        archive_base_url=archive_base_url,
        air_quality_base_url=air_quality_base_url,
        marine_base_url=marine_base_url,
    )
    server.register(servicer, service_name="openmeteo.v1.OpenMeteoService")

    asyncio.run(server.serve(**_projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()

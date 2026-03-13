"""Open-Meteo MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
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


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="openmeteo-mcp",
        version="0.1.0",
    )

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

    server.serve_from_argv()


if __name__ == "__main__":
    main()

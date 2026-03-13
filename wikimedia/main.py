"""Wikimedia MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from wikimedia_mcp.gen.wikimedia.v1 import wikimedia_pb2 as _wikimedia_pb2  # noqa: F401
from wikimedia_mcp.service import DEFAULT_BASE_URL, WikimediaService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="wikimedia-mcp",
        version="0.1.0",
    )

    base_url = (_env("WIKIMEDIA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = WikimediaService(base_url=base_url)
    server.register(servicer, service_name="wikimedia.v1.WikimediaService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

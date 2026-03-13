"""BallDontLie MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from balldontlie_mcp.gen.balldontlie.v1 import balldontlie_pb2 as _balldontlie_pb2  # noqa: F401
from balldontlie_mcp.service import DEFAULT_BASE_URL, BallDontLieService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="balldontlie-mcp",
        version="0.1.0",
    )

    base_url = (_env("BALLDONTLIE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = _env("BALLDONTLIE_API_KEY")

    servicer = BallDontLieService(base_url=base_url, api_key=api_key)
    server.register(servicer, service_name="balldontlie.v1.BallDontLieService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

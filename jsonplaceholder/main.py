"""JSONPlaceholder MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from jsonplaceholder_mcp.gen.jsonplaceholder.v1 import jsonplaceholder_pb2 as _jsonplaceholder_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"
DEFAULT_BASE_URL = "https://jsonplaceholder.typicode.com"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="jsonplaceholder-mcp",
        version="0.1.0",
    )

    base_url = (_env("JSONPLACEHOLDER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    server.connect_http(base_url, service_name="jsonplaceholder.v1.JsonPlaceholderService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

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

    args = sys.argv[1:]
    if "--cli" in args:
        idx = args.index("--cli")
        sys.argv = [sys.argv[0], *args[idx + 1 :]]
        server.serve(cli=True)
    elif "--http" in args:
        port = 8080
        idx = args.index("--http")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(http=port)
    elif "--grpc" in args:
        port = 50051
        idx = args.index("--grpc")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(grpc=port)
    else:
        server.serve(mcp=True)


if __name__ == "__main__":
    main()

"""Opinion.trade MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import os
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


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="opinion-mcp",
        version="0.1.0",
    )

    base_url = (_env("OPINION_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    header_provider = _build_auth_interceptor()
    if header_provider is not None:
        server.use_http_header_provider(header_provider)

    server.connect_http(base_url, service_name="opinion.v1.OpinionService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

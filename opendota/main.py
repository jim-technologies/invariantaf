"""OpenDota MCP server -- descriptor-driven HTTP client proxy via Invariant Protocol."""

from __future__ import annotations

import os
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


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="opendota-mcp",
        version="0.2.0",
    )

    _configure_auth_env()
    base_url = (os.getenv("OPENDOTA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    server.connect_http(base_url, service_name="opendota.v1.OpenDotaService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

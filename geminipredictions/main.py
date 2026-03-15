"""Gemini Predictions MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from geminipredictions_mcp.gen.geminipredictions.v1 import geminipredictions_pb2 as _geminipredictions_pb2  # noqa: F401
from geminipredictions_mcp.service import DEFAULT_BASE_URL, GeminiPredictionsService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="geminipredictions-mcp",
        version="0.1.0",
    )

    base_url = (_env("GEMINI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = _env("GEMINI_API_KEY")

    servicer = GeminiPredictionsService(base_url=base_url, api_key=api_key)
    server.register(servicer, service_name="geminipredictions.v1.GeminiPredictionsService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()

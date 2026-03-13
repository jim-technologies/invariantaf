"""Live integration tests for Li.Fi API -- hits the real API.

Run with:
    LIFI_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Li.Fi endpoints.
No API key or authentication is required (the API is free).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("LIFI_RUN_LIVE_TESTS") != "1",
    reason="Set LIFI_RUN_LIVE_TESTS=1 to run live Li.Fi API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from lifi_mcp.service import LifiService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-lifi-live", version="0.0.1"
    )
    servicer = LifiService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Chains ---


class TestLiveListChains:
    def test_list_chains(self, live_server):
        result = live_server._cli(["LifiService", "ListChains"])
        assert "chains" in result
        chains = result["chains"]
        assert isinstance(chains, list)
        assert len(chains) > 0
        c = chains[0]
        assert "name" in c
        assert "id" in c

    def test_has_ethereum(self, live_server):
        result = live_server._cli(["LifiService", "ListChains"])
        chains = result["chains"]
        names = [c["name"] for c in chains]
        assert "Ethereum" in names


# --- Tokens ---


class TestLiveListTokens:
    def test_list_tokens_for_ethereum(self, live_server):
        result = live_server._cli(
            [
                "LifiService",
                "ListTokens",
                "-r",
                json.dumps({"chains": "1"}),
            ]
        )
        key = "chainTokens" if "chainTokens" in result else "chain_tokens"
        assert key in result
        chain_tokens = result[key]
        assert isinstance(chain_tokens, list)
        assert len(chain_tokens) > 0
        tokens = chain_tokens[0].get("tokens", [])
        assert len(tokens) > 0
        assert "symbol" in tokens[0]


# --- Connections ---


class TestLiveGetConnections:
    def test_get_connections_eth_to_arb(self, live_server):
        result = live_server._cli(
            [
                "LifiService",
                "GetConnections",
                "-r",
                json.dumps({"fromChain": "1", "toChain": "42161"}),
            ]
        )
        assert "connections" in result
        connections = result["connections"]
        assert isinstance(connections, list)
        assert len(connections) > 0


# --- Tools ---


class TestLiveListTools:
    def test_list_tools(self, live_server):
        result = live_server._cli(["LifiService", "ListTools"])
        assert "bridges" in result
        assert "exchanges" in result
        bridges = result["bridges"]
        assert isinstance(bridges, list)
        assert len(bridges) > 0
        b = bridges[0]
        assert "key" in b
        assert "name" in b

    def test_exchanges_exist(self, live_server):
        result = live_server._cli(["LifiService", "ListTools"])
        exchanges = result["exchanges"]
        assert isinstance(exchanges, list)
        assert len(exchanges) > 0


# --- Quote ---


class TestLiveGetQuote:
    def test_get_quote_eth_to_arb(self, live_server):
        result = live_server._cli(
            [
                "LifiService",
                "GetQuote",
                "-r",
                json.dumps(
                    {
                        "fromChain": "ETH",
                        "toChain": "ARB",
                        "fromToken": "ETH",
                        "toToken": "ETH",
                        "fromAmount": "1000000000000000000",
                        "fromAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                    }
                ),
            ]
        )
        assert "action" in result
        assert "estimate" in result
        assert result.get("tool") or result.get("id")


# --- Status ---


class TestLiveGetStatus:
    def test_get_status_not_found(self, live_server):
        """Query a fake tx hash -- should return NOT_FOUND or similar."""
        result = live_server._cli(
            [
                "LifiService",
                "GetStatus",
                "-r",
                json.dumps(
                    {
                        "txHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
                    }
                ),
            ]
        )
        # The API should return a status field even for unknown transactions.
        assert "status" in result

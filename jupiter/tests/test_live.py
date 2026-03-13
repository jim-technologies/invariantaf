"""Live integration tests for Jupiter API -- hits the real API.

Run with:
    JUPITER_RUN_LIVE_TESTS=1 JUPITER_API_KEY=your-key uv run python -m pytest tests/test_live.py -v

An API key is required. Generate a free key at https://portal.jup.ag
and set the JUPITER_API_KEY environment variable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# Well-known Solana mint addresses for testing.
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

pytestmark = pytest.mark.skipif(
    os.getenv("JUPITER_RUN_LIVE_TESTS") != "1",
    reason="Set JUPITER_RUN_LIVE_TESTS=1 to run live Jupiter API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from jupiter_mcp.service import JupiterService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-jupiter-live", version="0.0.1"
    )
    servicer = JupiterService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Prices ---


class TestLivePrices:
    def test_get_price_single(self, live_server):
        result = live_server._cli([
            "JupiterService",
            "GetPrice",
            "-r",
            json.dumps({"ids": SOL_MINT}),
        ])
        assert "prices" in result
        prices = result["prices"]
        assert isinstance(prices, list)
        assert len(prices) >= 1
        p = prices[0]
        assert "mint" in p
        assert "price" in p
        assert p["price"] > 0

    def test_get_price_multiple(self, live_server):
        result = live_server._cli([
            "JupiterService",
            "GetPrice",
            "-r",
            json.dumps({"ids": f"{SOL_MINT},{USDC_MINT}"}),
        ])
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) >= 2


# --- Quotes ---


class TestLiveQuotes:
    def test_get_quote_sol_to_usdc(self, live_server):
        # Quote for 0.01 SOL -> USDC
        result = live_server._cli([
            "JupiterService",
            "GetQuote",
            "-r",
            json.dumps({
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount": "10000000",
                "slippage_bps": 50,
            }),
        ])
        # Check key fields are present (camelCase or snake_case).
        assert result.get("inputMint") or result.get("input_mint")
        assert result.get("outAmount") or result.get("out_amount")
        out_amount = result.get("outAmount") or result.get("out_amount")
        assert int(out_amount) > 0
        # Should have a route plan.
        route_plan = result.get("routePlan") or result.get("route_plan", [])
        assert len(route_plan) > 0


# --- Token Lists ---


class TestLiveTokens:
    def test_list_tokens_search(self, live_server):
        result = live_server._cli([
            "JupiterService",
            "ListTokens",
            "-r",
            json.dumps({"query": "SOL"}),
        ])
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        t = tokens[0]
        assert "symbol" in t

    def test_list_verified_tokens(self, live_server):
        result = live_server._cli(["JupiterService", "ListVerifiedTokens"])
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        t = tokens[0]
        assert "address" in t or "id" in t
        assert "symbol" in t
        assert "decimals" in t

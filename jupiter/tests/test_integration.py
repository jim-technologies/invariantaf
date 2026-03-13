"""Integration tests for Jupiter MCP — uses mocked HTTP but real Invariant server."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tests.conftest import SOL_MINT, USDC_MINT


class TestServerIntegration:
    """Test RPCs through the full Invariant Server via _cli."""

    def test_get_price(self, server):
        result = server._cli([
            "JupiterService",
            "GetPrice",
            "-r",
            json.dumps({"ids": f"{SOL_MINT},{USDC_MINT}"}),
        ])
        assert "prices" in result
        prices = result["prices"]
        assert isinstance(prices, list)
        assert len(prices) == 2

    def test_get_quote(self, server):
        result = server._cli([
            "JupiterService",
            "GetQuote",
            "-r",
            json.dumps({
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount": "1000000000",
                "slippage_bps": 50,
            }),
        ])
        assert result.get("inputMint") or result.get("input_mint")
        assert result.get("outAmount") or result.get("out_amount")

    def test_swap(self, server):
        quote_json = json.dumps({
            "inputMint": SOL_MINT,
            "outputMint": USDC_MINT,
            "inAmount": "1000000000",
            "outAmount": "172350000",
        })
        result = server._cli([
            "JupiterService",
            "Swap",
            "-r",
            json.dumps({
                "quote_response": quote_json,
                "user_public_key": "5ZWj7a1f8tWkjBESHKgrLmXshuXxqeY9SYcfbshpAqPG",
                "wrap_and_unwrap_sol": True,
            }),
        ])
        assert result.get("swapTransaction") or result.get("swap_transaction")

    def test_list_tokens(self, server):
        result = server._cli([
            "JupiterService",
            "ListTokens",
            "-r",
            json.dumps({"query": "SOL"}),
        ])
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_list_verified_tokens(self, server):
        result = server._cli(["JupiterService", "ListVerifiedTokens"])
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_list_markets(self, server):
        result = server._cli(["JupiterService", "ListMarkets"])
        assert "markets" in result
        markets = result["markets"]
        assert isinstance(markets, list)
        assert len(markets) > 0

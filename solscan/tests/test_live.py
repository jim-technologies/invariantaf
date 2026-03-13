"""Live integration tests for Solscan API -- hits the real API.

Run with:
    SOLSCAN_RUN_LIVE_TESTS=1 SOLSCAN_API_KEY=<key> uv run python -m pytest tests/test_live.py -v

Requires a valid SOLSCAN_API_KEY environment variable.
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
    os.getenv("SOLSCAN_RUN_LIVE_TESTS") != "1",
    reason="Set SOLSCAN_RUN_LIVE_TESTS=1 to run live Solscan API tests",
)

# Well-known Solana addresses for testing.
_SOL_MINT = "So11111111111111111111111111111111111111112"
_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from solscan_mcp.service import SolscanService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-solscan-live", version="0.0.1"
    )
    servicer = SolscanService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- GetAccountInfo ---


class TestLiveGetAccountInfo:
    def test_returns_account(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetAccountInfo",
                "-r",
                json.dumps({"address": _USDC_MINT}),
            ]
        )
        assert "account" in result
        account = result["account"]
        assert "address" in account or "owner" in account


# --- GetTokenMeta ---


class TestLiveGetTokenMeta:
    def test_returns_token_meta(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetTokenMeta",
                "-r",
                json.dumps({"address": _USDC_MINT}),
            ]
        )
        assert "token" in result
        token = result["token"]
        assert "symbol" in token

    def test_sol_token_meta(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetTokenMeta",
                "-r",
                json.dumps({"address": _SOL_MINT}),
            ]
        )
        assert "token" in result


# --- GetTokenPrice ---


class TestLiveGetTokenPrice:
    def test_returns_price(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetTokenPrice",
                "-r",
                json.dumps({"address": _USDC_MINT}),
            ]
        )
        assert "price" in result
        price = result["price"]
        assert "priceUsdt" in price or "price_usdt" in price


# --- GetTokenHolders ---


class TestLiveGetTokenHolders:
    def test_returns_holders(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetTokenHolders",
                "-r",
                json.dumps({"address": _USDC_MINT, "page": 1, "pageSize": 5}),
            ]
        )
        assert "holders" in result
        holders = result["holders"]
        assert isinstance(holders, list)


# --- GetMarketInfo ---


class TestLiveGetMarketInfo:
    def test_returns_market_info(self, live_server):
        result = live_server._cli(
            [
                "SolscanService",
                "GetMarketInfo",
                "-r",
                json.dumps({"address": _USDC_MINT}),
            ]
        )
        assert "market" in result

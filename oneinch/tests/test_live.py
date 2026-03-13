"""Live integration tests for 1inch API -- hits the real API.

Run with:
    ONEINCH_RUN_LIVE_TESTS=1 ONEINCH_API_KEY=<your-key> uv run python -m pytest tests/test_live.py -v

All tests require a valid ONEINCH_API_KEY environment variable.
Free keys are available at https://portal.1inch.dev/.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# Well-known token addresses on Ethereum mainnet.
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
# Vitalik's address — a well-known public wallet.
VITALIK_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

pytestmark = pytest.mark.skipif(
    os.getenv("ONEINCH_RUN_LIVE_TESTS") != "1",
    reason="Set ONEINCH_RUN_LIVE_TESTS=1 and ONEINCH_API_KEY to run live 1inch API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from oneinch_mcp.service import OneInchService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-oneinch-live", version="0.0.1"
    )
    servicer = OneInchService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Quote ---


class TestLiveGetQuote:
    def test_get_quote_eth_to_usdc(self, live_server):
        result = live_server._cli(
            [
                "OneInchService",
                "GetQuote",
                "-r",
                json.dumps(
                    {
                        "chainId": 1,
                        "src": WETH_ADDRESS,
                        "dst": USDC_ADDRESS,
                        "amount": "1000000000000000000",
                    }
                ),
            ]
        )
        dst_amount = result.get("dstAmount") or result.get("dst_amount")
        assert dst_amount, "expected a destination amount in quote"
        assert int(dst_amount) > 0, "quote dst_amount should be positive"


# --- Token Price ---


class TestLiveGetTokenPrice:
    def test_get_weth_price(self, live_server):
        result = live_server._cli(
            [
                "OneInchService",
                "GetTokenPrice",
                "-r",
                json.dumps(
                    {
                        "chainId": 1,
                        "tokens": WETH_ADDRESS,
                    }
                ),
            ]
        )
        assert "prices" in result
        prices = result["prices"]
        assert isinstance(prices, list)
        assert len(prices) > 0
        price = prices[0]
        price_usd = price.get("priceUsd") or price.get("price_usd")
        assert price_usd and float(price_usd) > 0


# --- Token Info ---


class TestLiveGetTokenInfo:
    def test_get_weth_info(self, live_server):
        result = live_server._cli(
            [
                "OneInchService",
                "GetTokenInfo",
                "-r",
                json.dumps({"chainId": 1, "address": WETH_ADDRESS}),
            ]
        )
        assert "token" in result
        token = result["token"]
        assert token.get("symbol") == "WETH"
        assert token.get("decimals") == 18


# --- Search Tokens ---


class TestLiveSearchTokens:
    def test_search_usdc(self, live_server):
        result = live_server._cli(
            [
                "OneInchService",
                "SearchTokens",
                "-r",
                json.dumps({"chainId": 1, "query": "USDC"}),
            ]
        )
        assert "tokens" in result
        tokens = result["tokens"]
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        symbols = [t.get("symbol", "") for t in tokens]
        assert "USDC" in symbols


# --- Balances ---


class TestLiveGetBalances:
    def test_get_balances(self, live_server):
        result = live_server._cli(
            [
                "OneInchService",
                "GetBalances",
                "-r",
                json.dumps({"chainId": 1, "address": VITALIK_ADDRESS}),
            ]
        )
        assert "balances" in result
        balances = result["balances"]
        assert isinstance(balances, list)
        assert len(balances) > 0
        # Vitalik should have at least some token balances.
        addresses = [b.get("address", "") for b in balances]
        assert len(addresses) > 0

"""Live integration tests for Hyperliquid API -- hits the real API.

Run with:
    HYPERLIQUID_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Hyperliquid endpoints.
Only market data RPCs are tested (GetMeta, GetAllMids, GetOrderbook, GetCandles).
Authenticated trading RPCs (PlaceOrder, CancelOrder, etc.) are skipped.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("HYPERLIQUID_RUN_LIVE_TESTS") != "1",
    reason="Set HYPERLIQUID_RUN_LIVE_TESTS=1 to run live Hyperliquid API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from hyperliquid_mcp.service import HyperliquidService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-hyperliquid-live", version="0.0.1"
    )
    # No private key -- only public market data endpoints.
    servicer = HyperliquidService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for discovery ---


@pytest.fixture(scope="module")
def first_asset_name(live_server):
    """Discover a tradable asset name (e.g. 'BTC') for tests that need one."""
    result = live_server._cli(["HyperliquidService", "GetMeta"])
    assets = result.get("assets", [])
    assert assets, "expected at least one asset in meta"
    return assets[0]["name"]


# --- Market Data ---


class TestLiveMarketData:
    def test_get_meta(self, live_server):
        result = live_server._cli(["HyperliquidService", "GetMeta"])
        assert "assets" in result
        assets = result["assets"]
        assert isinstance(assets, list)
        assert len(assets) > 0
        a = assets[0]
        assert "name" in a
        assert "size_decimals" in a or "sizeDecimals" in a

    def test_get_all_mids(self, live_server):
        result = live_server._cli(["HyperliquidService", "GetAllMids"])
        assert "mids" in result
        mids = result["mids"]
        assert isinstance(mids, dict)
        assert len(mids) > 0
        # BTC should always be listed
        assert "BTC" in mids or "ETH" in mids

    def test_get_orderbook(self, live_server, first_asset_name):
        result = live_server._cli(
            [
                "HyperliquidService",
                "GetOrderbook",
                "-r",
                json.dumps({"coin": first_asset_name}),
            ]
        )
        assert "bids" in result or "asks" in result
        # At least one side should have entries for an active market
        bids = result.get("bids", [])
        asks = result.get("asks", [])
        assert len(bids) > 0 or len(asks) > 0

    def test_get_candles(self, live_server, first_asset_name):
        # Request last 24h of 1-hour candles
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - 24 * 60 * 60 * 1000  # 24 hours ago

        result = live_server._cli(
            [
                "HyperliquidService",
                "GetCandles",
                "-r",
                json.dumps({
                    "coin": first_asset_name,
                    "interval": "CANDLE_INTERVAL_1H",
                    "start_time": start_ms,
                    "end_time": now_ms,
                }),
            ]
        )
        assert "candles" in result
        candles = result["candles"]
        assert isinstance(candles, list)
        # Should have at least some candle data
        if candles:
            c = candles[0]
            assert "open" in c
            assert "close" in c
            assert "high" in c
            assert "low" in c


# --- Account Data (public, needs an address) ---


class TestLiveAccountData:
    """Account data is public but needs a wallet address.
    We use a well-known Hyperliquid address; if it returns empty that is fine."""

    # A known active Hyperliquid vault address
    KNOWN_ADDRESS = "0x0000000000000000000000000000000000000000"

    def test_get_account_state(self, live_server):
        result = live_server._cli(
            [
                "HyperliquidService",
                "GetAccountState",
                "-r",
                json.dumps({"address": self.KNOWN_ADDRESS}),
            ]
        )
        # Should return without error; may have empty positions
        assert isinstance(result, dict)
        # Should contain account fields (may be empty/zero for unknown address)
        assert "account_value" in result or "accountValue" in result or "positions" in result

    def test_get_open_orders(self, live_server):
        result = live_server._cli(
            [
                "HyperliquidService",
                "GetOpenOrders",
                "-r",
                json.dumps({"address": self.KNOWN_ADDRESS}),
            ]
        )
        assert isinstance(result, dict)
        # Zero address may return empty dict or dict with empty orders list
        orders = result.get("orders", [])
        assert isinstance(orders, list)

    def test_get_fills(self, live_server):
        result = live_server._cli(
            [
                "HyperliquidService",
                "GetFills",
                "-r",
                json.dumps({"address": self.KNOWN_ADDRESS}),
            ]
        )
        assert isinstance(result, dict)
        assert "fills" in result
        assert isinstance(result["fills"], list)

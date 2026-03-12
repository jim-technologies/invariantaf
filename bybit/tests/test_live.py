"""Live integration tests for Bybit API -- hits the real API.

Run with:
    BYBIT_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Only PUBLIC market-data endpoints are tested (no auth required).
All private/trading endpoints (account, trade, position, asset) are skipped.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.bybit.com"

pytestmark = pytest.mark.skipif(
    os.getenv("BYBIT_RUN_LIVE_TESTS") != "1",
    reason="Set BYBIT_RUN_LIVE_TESTS=1 to run live Bybit API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.bybit.v1 import bybit_pb2 as _bybit_pb2  # noqa: F401

    base_url = (os.getenv("BYBIT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-bybit-live", version="0.0.1"
    )
    # Only connect BybitMarketService for public endpoints -- no auth needed
    srv.connect_http(base_url, service_name="bybit.v1.BybitMarketService")
    yield srv
    srv.stop()


# --- Server Time ---


class TestLiveServerTime:
    def test_get_server_time(self, live_server):
        result = live_server._cli(["BybitMarketService", "Time"])
        assert int(result.get("retCode", -1)) == 0
        assert "result" in result
        res = result["result"]
        assert "timeSecond" in res or "timeNano" in res


# --- Instruments ---


class TestLiveInstruments:
    def test_get_instruments_linear(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Instrument",
                "-r",
                json.dumps({"category": "linear"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        assert "result" in result
        res = result["result"]
        assert "list" in res
        instruments = res["list"]
        assert isinstance(instruments, list)
        assert len(instruments) > 0

    def test_get_instruments_spot(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Instrument",
                "-r",
                json.dumps({"category": "spot"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        assert len(res["list"]) > 0


# --- Tickers ---


class TestLiveTickers:
    def test_get_tickers_linear(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Tickers",
                "-r",
                json.dumps({"category": "linear", "symbol": "BTCUSDT"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        tickers = res["list"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0

    def test_get_tickers_spot(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Tickers",
                "-r",
                json.dumps({"category": "spot", "symbol": "BTCUSDT"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        assert len(res["list"]) > 0


# --- Orderbook ---


class TestLiveOrderbook:
    def test_get_orderbook(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Orderbook",
                "-r",
                json.dumps({"category": "linear", "symbol": "BTCUSDT"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        # Orderbook should have bids and asks arrays
        assert "a" in res or "b" in res


# --- Kline ---


class TestLiveKline:
    def test_get_kline(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "Kline",
                "-r",
                json.dumps({
                    "category": "linear",
                    "symbol": "BTCUSDT",
                    "interval": "60",
                    "limit": 5,
                }),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        klines = res["list"]
        assert isinstance(klines, list)
        assert len(klines) > 0


# --- Recent Trades ---


class TestLiveRecentTrades:
    def test_get_recent_trades(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "RecentTrade",
                "-r",
                json.dumps({
                    "category": "linear",
                    "symbol": "BTCUSDT",
                    "limit": 5,
                }),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        trades = res["list"]
        assert isinstance(trades, list)
        assert len(trades) > 0


# --- Open Interest ---


class TestLiveOpenInterest:
    def test_get_open_interest(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "OpenInterest",
                "-r",
                json.dumps({
                    "category": "linear",
                    "symbol": "BTCUSDT",
                    "intervalTime": "1h",
                }),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res


# --- Funding Rate History ---


class TestLiveFundingRate:
    def test_get_funding_rate_history(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "HistoryFundRate",
                "-r",
                json.dumps({
                    "category": "linear",
                    "symbol": "BTCUSDT",
                }),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res
        assert isinstance(res["list"], list)


# --- Insurance ---


class TestLiveInsurance:
    def test_get_insurance(self, live_server):
        result = live_server._cli(["BybitMarketService", "Insurance"])
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res or "updatedTime" in res


# --- Risk Limit ---


class TestLiveRiskLimit:
    def test_get_risk_limit(self, live_server):
        try:
            result = live_server._cli(
                [
                    "BybitMarketService",
                    "RiskLimit",
                    "-r",
                    json.dumps({"category": "linear"}),
                ]
            )
        except Exception as exc:
            if "timed out" in str(exc).lower():
                pytest.skip("RiskLimit endpoint timed out")
            raise
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res


# --- Delivery Price ---


class TestLiveDeliveryPrice:
    def test_get_delivery_price(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "DeliveryPrice",
                "-r",
                json.dumps({"category": "linear"}),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res


# --- Long Short Ratio ---


class TestLiveLongShortRatio:
    def test_get_long_short_ratio(self, live_server):
        result = live_server._cli(
            [
                "BybitMarketService",
                "LongShortRatio",
                "-r",
                json.dumps({
                    "category": "linear",
                    "symbol": "BTCUSDT",
                    "period": "1h",
                }),
            ]
        )
        assert int(result.get("retCode", -1)) == 0
        res = result["result"]
        assert "list" in res

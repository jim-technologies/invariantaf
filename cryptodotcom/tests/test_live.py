"""Live integration tests for Crypto.com Exchange API -- hits the real API.

Run with:
    CRYPTODOTCOM_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.crypto.com/exchange/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("CRYPTODOTCOM_RUN_LIVE_TESTS") != "1",
    reason="Set CRYPTODOTCOM_RUN_LIVE_TESTS=1 to run live Crypto.com API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    import httpx
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except (httpx.ConnectTimeout, httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"{method}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from cryptodotcom_mcp.gen.cryptodotcom.v1 import cryptodotcom_pb2 as _cryptodotcom_pb2  # noqa: F401
    from cryptodotcom_mcp.service import CryptoDotComService

    base_url = (os.getenv("CRYPTODOTCOM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-cryptodotcom-live", version="0.0.1"
    )
    servicer = CryptoDotComService(base_url=base_url)
    srv.register(servicer, service_name="cryptodotcom.v1.CryptoDotComService")
    yield srv
    srv.stop()


# --- GetInstruments ---


class TestLiveGetInstruments:
    def test_list_instruments(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetInstruments",
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        instrument = data[0]
        assert "instrument_name" in instrument
        assert "base_currency" in instrument
        assert "quote_currency" in instrument


# --- GetTickers ---


class TestLiveGetTickers:
    def test_single_ticker(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetTickers",
            {"instrument_name": "BTC_USDT"},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        ticker = data[0]
        assert "instrument_name" in ticker
        assert "latest_trade" in ticker
        assert "volume" in ticker

    def test_all_tickers(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetTickers",
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1


# --- GetOrderbook ---


class TestLiveGetOrderbook:
    def test_orderbook(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetOrderbook",
            {"instrument_name": "BTC_USDT", "depth": 5},
        )
        assert "data" in result
        data = result["data"]
        assert "bids" in data
        assert "asks" in data
        assert isinstance(data["bids"], list)
        assert isinstance(data["asks"], list)
        assert len(data["bids"]) >= 1
        assert len(data["asks"]) >= 1
        bid = data["bids"][0]
        assert "price" in bid
        assert "quantity" in bid


# --- GetCandlestick ---


class TestLiveGetCandlestick:
    def test_daily_candles(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetCandlestick",
            {"instrument_name": "BTC_USDT", "timeframe": "1D"},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        candle = data[0]
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle


# --- GetTrades ---


class TestLiveGetTrades:
    def test_recent_trades(self, live_server):
        result = _cli_or_skip(
            live_server, "CryptoDotComService", "GetTrades",
            {"instrument_name": "BTC_USDT"},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        trade = data[0]
        assert "trade_id" in trade
        assert "side" in trade
        assert "price" in trade
        assert "quantity" in trade

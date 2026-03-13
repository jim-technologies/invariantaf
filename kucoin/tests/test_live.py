"""Live integration tests for KuCoin API -- hits the real API.

Run with:
    KUCOIN_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
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

DEFAULT_BASE_URL = "https://api.kucoin.com"

pytestmark = pytest.mark.skipif(
    os.getenv("KUCOIN_RUN_LIVE_TESTS") != "1",
    reason="Set KUCOIN_RUN_LIVE_TESTS=1 to run live KuCoin API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient HTTP or network errors."""
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
    from kucoin_mcp.gen.kucoin.v1 import kucoin_pb2 as _kucoin_pb2  # noqa: F401
    from kucoin_mcp.service import KucoinService

    base_url = (os.getenv("KUCOIN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-kucoin-live", version="0.0.1"
    )
    servicer = KucoinService(base_url=base_url, timeout=10.0)
    srv.register(servicer, service_name="kucoin.v1.KucoinService")
    yield srv
    srv.stop()


# --- GetAllTickers ---


class TestLiveGetAllTickers:
    def test_get_all_tickers(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetAllTickers",
        )
        assert "time" in result
        assert "ticker" in result
        tickers = result["ticker"]
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        t = tickers[0]
        assert "symbol" in t
        assert "last" in t
        assert "buy" in t
        assert "sell" in t


# --- GetTicker ---


class TestLiveGetTicker:
    def test_get_btc_usdt(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetTicker",
            {"symbol": "BTC-USDT"},
        )
        assert result["symbol"] == "BTC-USDT"
        assert result["last"] != ""
        assert result["buy"] != ""
        assert result["sell"] != ""
        assert result["vol"] != ""

    def test_get_eth_usdt(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetTicker",
            {"symbol": "ETH-USDT"},
        )
        assert result["symbol"] == "ETH-USDT"
        assert result["last"] != ""


# --- GetOrderbook ---


class TestLiveGetOrderbook:
    def test_get_orderbook_btc(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetOrderbook",
            {"symbol": "BTC-USDT"},
        )
        assert "bids" in result
        assert "asks" in result
        assert len(result["bids"]) > 0
        assert len(result["asks"]) > 0
        assert result["bids"][0]["price"] != ""
        assert result["bids"][0]["size"] != ""
        assert result["sequence"] != ""

    def test_orderbook_has_time(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetOrderbook",
            {"symbol": "BTC-USDT"},
        )
        assert "time" in result


# --- GetKlines ---


class TestLiveGetKlines:
    def test_get_klines_btc_1hour(self, live_server):
        now = int(time.time())
        one_day_ago = now - (24 * 60 * 60)
        result = _cli_or_skip(
            live_server, "KucoinService", "GetKlines",
            {
                "symbol": "BTC-USDT",
                "type": "1hour",
                "start_at": one_day_ago,
                "end_at": now,
            },
        )
        assert "klines" in result
        klines = result["klines"]
        assert isinstance(klines, list)
        assert len(klines) > 0
        k = klines[0]
        assert "time" in k
        assert "open" in k
        assert "close" in k
        assert "high" in k
        assert "low" in k
        assert "volume" in k
        assert "turnover" in k


# --- ListSymbols ---


class TestLiveListSymbols:
    def test_list_all_symbols(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "ListSymbols",
        )
        assert "symbols" in result
        symbols = result["symbols"]
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        s = symbols[0]
        assert "symbol" in s
        assert "base_currency" in s
        assert "quote_currency" in s

    def test_list_symbols_has_trading_info(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "ListSymbols",
        )
        symbols = result["symbols"]
        assert len(symbols) > 0
        s = symbols[0]
        assert "enable_trading" in s


# --- GetFiat ---


class TestLiveGetFiat:
    def test_get_fiat_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetFiat",
            {"base": "USD"},
        )
        assert "prices" in result
        prices = result["prices"]
        assert isinstance(prices, list)
        assert len(prices) > 0
        p = prices[0]
        assert "currency" in p
        assert "price" in p
        assert p["price"] != ""

    def test_get_fiat_specific_currencies(self, live_server):
        result = _cli_or_skip(
            live_server, "KucoinService", "GetFiat",
            {"base": "USD", "currencies": "BTC,ETH"},
        )
        assert "prices" in result
        prices = result["prices"]
        assert len(prices) >= 1
        currencies = {p["currency"] for p in prices}
        assert "BTC" in currencies or "ETH" in currencies

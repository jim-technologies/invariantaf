"""Live integration tests for CoinPaprika API -- hits the real API.

Run with:
    COINPAPRIKA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

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

DEFAULT_BASE_URL = "https://api.coinpaprika.com/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("COINPAPRIKA_RUN_LIVE_TESTS") != "1",
    reason="Set COINPAPRIKA_RUN_LIVE_TESTS=1 to run live CoinPaprika API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on connection errors or transient server errors."""
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
    from coinpaprika_mcp.gen.coinpaprika.v1 import coinpaprika_pb2 as _coinpaprika_pb2  # noqa: F401
    from coinpaprika_mcp.service import CoinPaprikaService

    base_url = (os.getenv("COINPAPRIKA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-coinpaprika-live", version="0.0.1"
    )
    servicer = CoinPaprikaService(base_url=base_url)
    srv.register(servicer, service_name="coinpaprika.v1.CoinPaprikaService")
    yield srv
    srv.stop()


# --- GetGlobal ---


class TestLiveGetGlobal:
    def test_global_stats(self, live_server):
        result = _cli_or_skip(live_server, "CoinPaprikaService", "GetGlobal")
        assert result["market_cap_usd"] > 0
        assert result["volume_24h_usd"] > 0
        assert result["bitcoin_dominance_percentage"] > 0
        assert result["cryptocurrencies_number"] > 0
        assert int(result["last_updated"]) > 0


# --- ListCoins ---


class TestLiveListCoins:
    def test_list_coins(self, live_server):
        result = _cli_or_skip(live_server, "CoinPaprikaService", "ListCoins")
        assert "coins" in result
        coins = result["coins"]
        assert isinstance(coins, list)
        assert len(coins) > 100
        # Bitcoin should be in the list
        btc = [c for c in coins if c["id"] == "btc-bitcoin"]
        assert len(btc) == 1
        assert btc[0]["symbol"] == "BTC"
        assert btc[0]["rank"] == 1


# --- GetCoinById ---


class TestLiveGetCoinById:
    def test_get_bitcoin(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetCoinById",
            {"coin_id": "btc-bitcoin"},
        )
        assert result["id"] == "btc-bitcoin"
        assert result["name"] == "Bitcoin"
        assert result["symbol"] == "BTC"
        assert result["rank"] == 1
        assert len(result.get("description", "")) > 0
        assert result["is_active"] is True

    def test_get_ethereum(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetCoinById",
            {"coin_id": "eth-ethereum"},
        )
        assert result["id"] == "eth-ethereum"
        assert result["name"] == "Ethereum"
        assert result["symbol"] == "ETH"


# --- GetTickerById ---


class TestLiveGetTickerById:
    def test_get_btc_ticker(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetTickerById",
            {"coin_id": "btc-bitcoin"},
        )
        assert result["id"] == "btc-bitcoin"
        assert result["name"] == "Bitcoin"
        quotes = result["quotes_usd"]
        assert quotes["price"] > 0
        assert quotes["volume_24h"] > 0
        assert quotes["market_cap"] > 0

    def test_get_eth_ticker(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetTickerById",
            {"coin_id": "eth-ethereum"},
        )
        assert result["id"] == "eth-ethereum"
        quotes = result["quotes_usd"]
        assert quotes["price"] > 0


# --- ListTickers ---


class TestLiveListTickers:
    def test_list_tickers(self, live_server):
        result = _cli_or_skip(live_server, "CoinPaprikaService", "ListTickers")
        assert "tickers" in result
        tickers = result["tickers"]
        assert isinstance(tickers, list)
        assert len(tickers) > 100
        btc = [t for t in tickers if t["id"] == "btc-bitcoin"]
        assert len(btc) == 1
        quotes = btc[0]["quotes_usd"]
        assert quotes["price"] > 0


# --- GetCoinMarkets ---


class TestLiveGetCoinMarkets:
    def test_btc_markets(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetCoinMarkets",
            {"coin_id": "btc-bitcoin"},
        )
        assert "markets" in result
        markets = result["markets"]
        assert isinstance(markets, list)
        assert len(markets) > 0
        m = markets[0]
        assert m["exchange_name"] != ""
        assert m["pair"] != ""
        quotes = m["quotes_usd"]
        assert quotes["price"] > 0

    def test_eth_markets(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetCoinMarkets",
            {"coin_id": "eth-ethereum"},
        )
        assert "markets" in result
        assert len(result["markets"]) > 0


# --- GetCoinOHLCV ---


class TestLiveGetCoinOHLCV:
    def test_btc_ohlcv(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "GetCoinOHLCV",
            {"coin_id": "btc-bitcoin"},
        )
        assert "entries" in result
        entries = result["entries"]
        assert isinstance(entries, list)
        assert len(entries) > 0
        e = entries[0]
        assert e["open"] > 0
        assert e["high"] > 0
        assert e["low"] > 0
        assert e["close"] > 0
        assert e["volume"] > 0


# --- SearchCoins ---


class TestLiveSearchCoins:
    def test_search_bitcoin(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "SearchCoins",
            {"query": "bitcoin"},
        )
        assert "currencies" in result
        currencies = result["currencies"]
        assert isinstance(currencies, list)
        assert len(currencies) > 0
        # Bitcoin should be in results
        ids = [c["id"] for c in currencies]
        assert "btc-bitcoin" in ids

    def test_search_ethereum(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinPaprikaService", "SearchCoins",
            {"query": "ethereum"},
        )
        assert "currencies" in result
        assert len(result["currencies"]) > 0

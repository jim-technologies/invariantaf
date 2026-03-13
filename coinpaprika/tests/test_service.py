"""Unit tests for CoinPaprika service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "CoinPaprikaService.GetGlobal",
    "CoinPaprikaService.ListCoins",
    "CoinPaprikaService.GetCoinById",
    "CoinPaprikaService.GetTickerById",
    "CoinPaprikaService.ListTickers",
    "CoinPaprikaService.GetCoinMarkets",
    "CoinPaprikaService.GetCoinOHLCV",
    "CoinPaprikaService.SearchCoins",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 8

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_global(self, server):
        result = server._cli(["CoinPaprikaService", "GetGlobal"])
        assert result["market_cap_usd"] == 2500000000000
        assert result["volume_24h_usd"] == 120000000000
        assert result["bitcoin_dominance_percentage"] == 52.35
        assert result["cryptocurrencies_number"] == 10234
        assert result["market_cap_ath_date"] == "2021-11-10T00:00:00Z"
        assert result["market_cap_change_24h"] == 1.25
        assert result["volume_24h_change_24h"] == -3.5
        assert int(result["last_updated"]) == 1772720841

    def test_list_coins(self, server):
        result = server._cli(["CoinPaprikaService", "ListCoins"])
        assert "coins" in result
        coins = result["coins"]
        assert len(coins) == 1
        coin = coins[0]
        assert coin["id"] == "btc-bitcoin"
        assert coin["name"] == "Bitcoin"
        assert coin["symbol"] == "BTC"
        assert coin["rank"] == 1
        assert coin["is_active"] is True
        assert coin["type"] == "coin"

    def test_get_coin_by_id(self, server):
        result = server._cli(
            ["CoinPaprikaService", "GetCoinById", "-r", '{"coin_id":"btc-bitcoin"}']
        )
        assert result["id"] == "btc-bitcoin"
        assert result["name"] == "Bitcoin"
        assert result["symbol"] == "BTC"
        assert result["rank"] == 1
        assert "cryptocurrency" in result["description"].lower() or "payment" in result["description"].lower()
        assert result["started_at"] == "2009-01-03T00:00:00Z"
        assert result["open_source"] is True
        assert result["hash_algorithm"] == "SHA-256"
        assert len(result["tags"]) == 1
        assert result["tags"][0]["name"] == "Segwit"
        assert len(result["team"]) == 1
        assert result["team"][0]["name"] == "Satoshi Nakamoto"

    def test_get_ticker_by_id(self, server):
        result = server._cli(
            ["CoinPaprikaService", "GetTickerById", "-r", '{"coin_id":"btc-bitcoin"}']
        )
        assert result["id"] == "btc-bitcoin"
        assert result["name"] == "Bitcoin"
        assert result["symbol"] == "BTC"
        assert result["rank"] == 1
        assert result["total_supply"] == 19600000
        assert result["max_supply"] == 21000000
        assert "quotes_usd" in result
        quotes = result["quotes_usd"]
        assert quotes["price"] == 64500.0
        assert quotes["volume_24h"] == 35000000000.0
        assert quotes["percent_change_24h"] == 3.0
        assert quotes["ath_price"] == 69000.0

    def test_list_tickers(self, server):
        result = server._cli(["CoinPaprikaService", "ListTickers"])
        assert "tickers" in result
        tickers = result["tickers"]
        assert len(tickers) == 1
        t = tickers[0]
        assert t["id"] == "btc-bitcoin"
        assert t["name"] == "Bitcoin"
        quotes = t["quotes_usd"]
        assert quotes["price"] == 64500.0

    def test_get_coin_markets(self, server):
        result = server._cli(
            ["CoinPaprikaService", "GetCoinMarkets", "-r", '{"coin_id":"btc-bitcoin"}']
        )
        assert "markets" in result
        markets = result["markets"]
        assert len(markets) == 1
        m = markets[0]
        assert m["exchange_id"] == "binance"
        assert m["exchange_name"] == "Binance"
        assert m["pair"] == "BTC/USDT"
        assert m["base_currency_name"] == "Bitcoin"
        assert m["quote_currency_name"] == "Tether"
        assert m["category"] == "Spot"
        assert m["trust_score"] == "high"
        quotes = m["quotes_usd"]
        assert quotes["price"] == 64500.0
        assert quotes["volume_24h"] == 5000000000.0

    def test_get_coin_ohlcv(self, server):
        result = server._cli(
            ["CoinPaprikaService", "GetCoinOHLCV", "-r", '{"coin_id":"btc-bitcoin"}']
        )
        assert "entries" in result
        entries = result["entries"]
        assert len(entries) == 1
        e = entries[0]
        assert e["time_open"] == "2024-03-01T00:00:00Z"
        assert e["open"] == 62500.0
        assert e["high"] == 65000.0
        assert e["low"] == 62000.0
        assert e["close"] == 64500.0
        assert e["volume"] == 35000000000
        assert e["market_cap"] == 1264200000000

    def test_search_coins(self, server):
        result = server._cli(
            ["CoinPaprikaService", "SearchCoins", "-r", '{"query":"bitcoin"}']
        )
        assert "currencies" in result
        currencies = result["currencies"]
        assert len(currencies) == 1
        c = currencies[0]
        assert c["id"] == "btc-bitcoin"
        assert c["name"] == "Bitcoin"
        assert c["symbol"] == "BTC"
        assert c["rank"] == 1
        assert c["is_active"] is True

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["CoinPaprikaService", "DoesNotExist"])


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path: str, body: dict | None = None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_get_global(self):
        result = self._post("/coinpaprika.v1.CoinPaprikaService/GetGlobal")
        assert result["market_cap_usd"] == 2500000000000

    def test_list_coins(self):
        result = self._post("/coinpaprika.v1.CoinPaprikaService/ListCoins")
        assert len(result["coins"]) == 1

    def test_get_coin_by_id(self):
        result = self._post(
            "/coinpaprika.v1.CoinPaprikaService/GetCoinById",
            {"coin_id": "btc-bitcoin"},
        )
        assert result["id"] == "btc-bitcoin"

    def test_get_ticker_by_id(self):
        result = self._post(
            "/coinpaprika.v1.CoinPaprikaService/GetTickerById",
            {"coin_id": "btc-bitcoin"},
        )
        assert result["id"] == "btc-bitcoin"

    def test_get_coin_markets(self):
        result = self._post(
            "/coinpaprika.v1.CoinPaprikaService/GetCoinMarkets",
            {"coin_id": "btc-bitcoin"},
        )
        assert len(result["markets"]) == 1

    def test_get_coin_ohlcv(self):
        result = self._post(
            "/coinpaprika.v1.CoinPaprikaService/GetCoinOHLCV",
            {"coin_id": "btc-bitcoin"},
        )
        assert len(result["entries"]) == 1

    def test_search_coins(self):
        result = self._post(
            "/coinpaprika.v1.CoinPaprikaService/SearchCoins",
            {"query": "bitcoin"},
        )
        assert len(result["currencies"]) == 1

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404

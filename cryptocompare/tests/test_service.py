"""Unit tests for CryptoCompare service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "CryptoCompareService.GetPrice",
    "CryptoCompareService.GetMultiPrice",
    "CryptoCompareService.GetFullPrice",
    "CryptoCompareService.GetHistoHour",
    "CryptoCompareService.GetHistoDay",
    "CryptoCompareService.GetTopByVolume",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 6

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_price(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetPrice", "-r", '{"fsym":"BTC","tsyms":"USD,EUR,GBP"}']
        )
        assert "prices" in result
        prices = result["prices"]
        assert prices["USD"] == 64500.0
        assert prices["EUR"] == 59000.0
        assert prices["GBP"] == 51000.0

    def test_get_multi_price(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetMultiPrice", "-r", '{"fsyms":"BTC,ETH","tsyms":"USD,EUR"}']
        )
        assert "rows" in result
        rows = result["rows"]
        assert len(rows) == 2
        btc_row = next(r for r in rows if r["from_symbol"] == "BTC")
        eth_row = next(r for r in rows if r["from_symbol"] == "ETH")
        assert btc_row["prices"]["USD"] == 64500.0
        assert btc_row["prices"]["EUR"] == 59000.0
        assert eth_row["prices"]["USD"] == 2500.0
        assert eth_row["prices"]["EUR"] == 2300.0

    def test_get_full_price(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetFullPrice", "-r", '{"fsyms":"BTC,ETH","tsyms":"USD"}']
        )
        assert "coins" in result
        coins = result["coins"]
        assert len(coins) == 2
        btc = next(c for c in coins if c["from_symbol"] == "BTC")
        assert btc["to_symbol"] == "USD"
        assert btc["price"] == 64500.0
        assert btc["volume_24h"] == 25000.0
        assert btc["market_cap"] == 1250000000000.0
        assert btc["change_pct_24h"] == 2.5
        assert btc["high_24h"] == 65000.0
        assert btc["low_24h"] == 63000.0
        assert btc["open_24h"] == 63500.0
        assert btc["supply"] == 19500000.0
        eth = next(c for c in coins if c["from_symbol"] == "ETH")
        assert eth["price"] == 2500.0

    def test_get_histo_hour(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetHistoHour", "-r", '{"fsym":"BTC","tsym":"USD","limit":3}']
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) == 3
        assert int(candles[0]["time"]) == 1700000000
        assert candles[0]["open"] == 64000.0
        assert candles[0]["high"] == 64600.0
        assert candles[0]["low"] == 63900.0
        assert candles[0]["close"] == 64500.0
        assert candles[0]["volumefrom"] == 100.0
        assert candles[0]["volumeto"] == 6450000.0
        assert candles[2]["close"] == 64400.0

    def test_get_histo_day(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetHistoDay", "-r", '{"fsym":"BTC","tsym":"USD","limit":3}']
        )
        assert "candles" in result
        candles = result["candles"]
        assert len(candles) == 3
        assert int(candles[0]["time"]) == 1700000000
        assert candles[1]["open"] == 64500.0

    def test_get_top_by_volume(self, server):
        result = server._cli(
            ["CryptoCompareService", "GetTopByVolume", "-r", '{"tsym":"USD","limit":10}']
        )
        assert "coins" in result
        coins = result["coins"]
        assert len(coins) == 2
        btc = next(c for c in coins if c["symbol"] == "BTC")
        assert btc["name"] == "Bitcoin"
        assert btc["price"] == 64500.0
        assert btc["volume_24h"] == 25000.0
        assert btc["market_cap"] == 1250000000000.0
        assert btc["change_pct_24h"] == 2.5
        eth = next(c for c in coins if c["symbol"] == "ETH")
        assert eth["name"] == "Ethereum"
        assert eth["price"] == 2500.0

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["CryptoCompareService", "DoesNotExist"])


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

    def test_get_price(self):
        result = self._post(
            "/cryptocompare.v1.CryptoCompareService/GetPrice",
            {"fsym": "BTC", "tsyms": "USD,EUR,GBP"},
        )
        assert result["prices"]["USD"] == 64500.0

    def test_get_multi_price(self):
        result = self._post(
            "/cryptocompare.v1.CryptoCompareService/GetMultiPrice",
            {"fsyms": "BTC,ETH", "tsyms": "USD,EUR"},
        )
        assert len(result["rows"]) == 2

    def test_get_full_price(self):
        result = self._post(
            "/cryptocompare.v1.CryptoCompareService/GetFullPrice",
            {"fsyms": "BTC,ETH", "tsyms": "USD"},
        )
        assert len(result["coins"]) == 2

    def test_get_histo_hour(self):
        result = self._post(
            "/cryptocompare.v1.CryptoCompareService/GetHistoHour",
            {"fsym": "BTC", "tsym": "USD"},
        )
        assert len(result["candles"]) == 3

    def test_get_top_by_volume(self):
        result = self._post(
            "/cryptocompare.v1.CryptoCompareService/GetTopByVolume",
            {"tsym": "USD"},
        )
        assert len(result["coins"]) == 2

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404

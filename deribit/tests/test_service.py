"""Unit tests for Deribit service -- descriptor loading, tool registration, and proxy behavior."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "DeribitService.GetInstruments",
    "DeribitService.GetOrderbook",
    "DeribitService.GetTicker",
    "DeribitService.GetBookSummaryByCurrency",
    "DeribitService.GetHistoricalVolatility",
    "DeribitService.GetFundingRateValue",
    "DeribitService.GetIndexPrice",
    "DeribitService.GetTradingviewChartData",
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
    def test_get_instruments(self, server):
        result = server._cli(
            ["DeribitService", "GetInstruments", "-r", '{"currency":"BTC","kind":"option"}']
        )
        assert "instruments" in result
        instruments = result["instruments"]
        assert len(instruments) == 1
        inst = instruments[0]
        assert inst["instrument_name"] == "BTC-28MAR26-100000-C"
        assert inst["kind"] == "option"
        assert inst["base_currency"] == "BTC"
        assert inst["strike"] == 100000.0
        assert inst["option_type"] == "call"
        assert inst["is_active"] is True

    def test_get_orderbook(self, server):
        result = server._cli(
            ["DeribitService", "GetOrderbook", "-r", '{"instrument_name":"BTC-PERPETUAL"}']
        )
        assert result["instrument_name"] == "BTC-PERPETUAL"
        assert result["best_bid_price"] == 64500.0
        assert result["best_ask_price"] == 64510.0
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2
        assert result["bids"][0]["price"] == 64500.0
        assert result["bids"][0]["amount"] == 5.0
        assert result["asks"][0]["price"] == 64510.0
        assert result["state"] == "open"
        assert result["open_interest"] == 250000000.0

    def test_get_ticker(self, server):
        result = server._cli(
            ["DeribitService", "GetTicker", "-r", '{"instrument_name":"BTC-PERPETUAL"}']
        )
        assert result["instrument_name"] == "BTC-PERPETUAL"
        assert result["last_price"] == 64505.0
        assert result["mark_price"] == 64502.5
        assert result["volume_usd"] == 500000000.0
        assert result["mark_iv"] == 55.0
        assert result["greeks"]["delta"] == 0.65
        assert result["greeks"]["gamma"] == 0.0001
        assert result["greeks"]["vega"] == 120.5

    def test_get_book_summary_by_currency(self, server):
        result = server._cli(
            [
                "DeribitService",
                "GetBookSummaryByCurrency",
                "-r",
                '{"currency":"BTC","kind":"future"}',
            ]
        )
        assert "summaries" in result
        summaries = result["summaries"]
        assert len(summaries) == 1
        s = summaries[0]
        assert s["instrument_name"] == "BTC-PERPETUAL"
        assert s["volume_usd"] == 500000000.0
        assert s["mark_price"] == 64502.5

    def test_get_historical_volatility(self, server):
        result = server._cli(
            ["DeribitService", "GetHistoricalVolatility", "-r", '{"currency":"BTC"}']
        )
        assert "data" in result
        data = result["data"]
        assert len(data) == 3
        assert int(data[0]["timestamp"]) == 1772720000000
        assert data[0]["volatility"] == 55.5
        assert data[2]["volatility"] == 54.8

    def test_get_funding_rate_value(self, server):
        result = server._cli(
            [
                "DeribitService",
                "GetFundingRateValue",
                "-r",
                json.dumps({
                    "instrument_name": "BTC-PERPETUAL",
                    "start_timestamp": 1772720000000,
                    "end_timestamp": 1772806400000,
                }),
            ]
        )
        assert result["funding_rate"] == 0.00025

    def test_get_index_price(self, server):
        result = server._cli(
            ["DeribitService", "GetIndexPrice", "-r", '{"index_name":"btc_usd"}']
        )
        assert result["index_price"] == 64500.0
        assert result["estimated_delivery_price"] == 64500.0

    def test_get_tradingview_chart_data(self, server):
        result = server._cli(
            [
                "DeribitService",
                "GetTradingviewChartData",
                "-r",
                json.dumps({
                    "instrument_name": "BTC-PERPETUAL",
                    "start_timestamp": 1772720000000,
                    "end_timestamp": 1772730000000,
                    "resolution": "60",
                }),
            ]
        )
        assert result["status"] == "ok"
        assert len(result["ticks"]) == 3
        assert len(result["open"]) == 3
        assert len(result["close"]) == 3
        assert result["open"][0] == 64000.0
        assert result["close"][2] == 64400.0

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["DeribitService", "DoesNotExist"])


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

    def test_get_instruments(self):
        result = self._post(
            "/deribit.v1.DeribitService/GetInstruments",
            {"currency": "BTC"},
        )
        assert len(result["instruments"]) == 1

    def test_get_orderbook(self):
        result = self._post(
            "/deribit.v1.DeribitService/GetOrderbook",
            {"instrument_name": "BTC-PERPETUAL"},
        )
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2

    def test_get_ticker(self):
        result = self._post(
            "/deribit.v1.DeribitService/GetTicker",
            {"instrument_name": "BTC-PERPETUAL"},
        )
        assert result["last_price"] == 64505.0

    def test_get_index_price(self):
        result = self._post(
            "/deribit.v1.DeribitService/GetIndexPrice",
            {"index_name": "btc_usd"},
        )
        assert result["index_price"] == 64500.0

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404

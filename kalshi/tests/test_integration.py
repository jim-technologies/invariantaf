"""Integration tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 85

    def test_tool_names(self, server):
        expected = {
            "KalshiService.GetExchangeStatus",
            "KalshiService.GetHistoricalMarket",
            "KalshiService.GetMarkets",
            "KalshiService.CreateOrder",
            "KalshiService.GetFills",
            "KalshiService.GetMilestones",
        }
        assert expected.issubset(set(server.tools.keys()))


class TestCLIProjection:
    def test_get_exchange_status(self, server):
        result = server._cli(["KalshiService", "GetExchangeStatus"])
        assert "data" in result
        assert result["data"]["exchange_active"] is True

    def test_get_historical_market(self, server):
        result = server._cli(
            ["KalshiService", "GetHistoricalMarket", "-r", '{"ticker":"TEST-MKT"}']
        )
        assert "data" in result
        assert result["data"]["market"]["ticker"] == "TEST-MKT"

    def test_create_order(self, server):
        result = server._cli(
            [
                "KalshiService",
                "CreateOrder",
                "-r",
                '{"body":{"ticker":"TEST-MKT","action":"buy","count":1}}',
            ]
        )
        assert "data" in result
        assert result["data"]["order"]["status"] == "accepted"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["KalshiService", "DoesNotExist"])


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

    def test_get_markets(self):
        result = self._post("/kalshi.v1.KalshiService/GetMarkets", {"limit": 1})
        assert "data" in result
        assert len(result["data"]["markets"]) == 1

    def test_create_order(self):
        result = self._post(
            "/kalshi.v1.KalshiService/CreateOrder",
            {"body": {"ticker": "TEST-MKT", "action": "buy", "count": 1}},
        )
        assert "data" in result
        assert result["data"]["order"]["status"] == "accepted"

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


@pytest.fixture
def live_server():
    if os.getenv("KALSHI_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_TESTS=1 to run live Kalshi API tests")

    from invariant import Server
    from gen.kalshi.v1 import kalshi_pb2 as _kalshi_pb2  # noqa: F401

    base_url = (os.getenv("KALSHI_BASE_URL") or "https://api.elections.kalshi.com/trade-api/v2").rstrip("/")
    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-kalshi-live", version="0.0.1")
    srv.connect_http(base_url, service_name="kalshi.v1.KalshiService")
    yield srv
    srv.stop()


class TestLiveKalshiAPI:
    def test_live_get_exchange_status(self, live_server):
        result = live_server._cli(["KalshiService", "GetExchangeStatus"])
        assert "data" in result
        assert isinstance(result["data"].get("exchange_active"), bool)
        assert isinstance(result["data"].get("trading_active"), bool)

    def test_live_get_markets(self, live_server):
        result = live_server._cli(["KalshiService", "GetMarkets", "-r", '{"limit": 3}'])
        assert "data" in result
        markets = result["data"].get("markets")
        assert isinstance(markets, list)
        assert len(markets) > 0
        assert "ticker" in markets[0]

    def test_live_get_market_by_ticker(self, live_server):
        markets_result = live_server._cli(["KalshiService", "GetMarkets", "-r", '{"limit": 1}'])
        markets = markets_result.get("data", {}).get("markets", [])
        assert markets, "expected at least one market from live Kalshi API"
        ticker = markets[0].get("ticker")
        assert ticker, "expected ticker in market payload"

        result = live_server._cli(
            ["KalshiService", "GetMarket", "-r", json.dumps({"ticker": ticker})]
        )
        assert "data" in result
        assert result["data"]["market"]["ticker"] == ticker

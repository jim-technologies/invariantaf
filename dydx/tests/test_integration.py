"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from dydx_mcp.gen.dydx.v1 import dydx_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 5

    def test_tool_names(self, server):
        expected = {
            "DydxService.ListMarkets",
            "DydxService.GetOrderbook",
            "DydxService.GetTrades",
            "DydxService.GetCandles",
            "DydxService.GetFundingRates",
        }
        actual = set(server.tools.keys())
        missing = expected - actual
        assert not missing, f"Missing tools: {missing}"
        assert expected.issubset(actual)

    def test_tools_have_descriptions(self, server):
        for name, tool in server.tools.items():
            assert tool.description, f"{name} has no description"
            assert len(tool.description) > 10, f"{name} description too short"

    def test_tools_have_input_schemas(self, server):
        for name, tool in server.tools.items():
            schema = tool.input_schema
            assert isinstance(schema, dict), f"{name} schema is not a dict"
            assert schema.get("type") == "object", f"{name} schema type != object"


class TestCLIProjection:
    def test_list_markets(self, server):
        result = server._cli(["DydxService", "ListMarkets"])
        assert "markets" in result
        assert len(result["markets"]) == 2

    def test_list_markets_has_btc(self, server):
        result = server._cli(["DydxService", "ListMarkets"])
        tickers = [m["ticker"] for m in result["markets"]]
        assert "BTC-USD" in tickers

    def test_get_orderbook(self, server):
        result = server._cli(
            ["DydxService", "GetOrderbook", "-r", '{"ticker":"BTC-USD"}']
        )
        assert "bids" in result
        assert "asks" in result
        assert len(result["bids"]) == 3
        assert len(result["asks"]) == 3

    def test_get_trades(self, server):
        result = server._cli(
            ["DydxService", "GetTrades", "-r", '{"ticker":"BTC-USD"}']
        )
        assert "trades" in result
        assert len(result["trades"]) == 3

    def test_get_candles(self, server):
        result = server._cli(
            ["DydxService", "GetCandles", "-r", json.dumps({"ticker": "BTC-USD", "resolution": 5})]
        )
        assert "candles" in result
        assert len(result["candles"]) == 2

    def test_get_funding_rates(self, server):
        result = server._cli(
            ["DydxService", "GetFundingRates", "-r", '{"ticker":"BTC-USD"}']
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert key in result
        assert len(result[key]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["DydxService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "DydxService" in result
        assert "ListMarkets" in result

    def test_no_args_shows_usage(self, server):
        result = server._cli([])
        assert "Usage:" in result


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path, body=None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_list_markets(self):
        result = self._post("/dydx.v1.DydxService/ListMarkets")
        assert "markets" in result

    def test_get_orderbook(self):
        result = self._post(
            "/dydx.v1.DydxService/GetOrderbook", {"ticker": "BTC-USD"}
        )
        assert "bids" in result
        assert "asks" in result

    def test_get_trades(self):
        result = self._post(
            "/dydx.v1.DydxService/GetTrades", {"ticker": "BTC-USD"}
        )
        assert "trades" in result

    def test_get_candles(self):
        result = self._post(
            "/dydx.v1.DydxService/GetCandles",
            {"ticker": "BTC-USD", "resolution": 5},
        )
        assert "candles" in result

    def test_get_funding_rates(self):
        result = self._post(
            "/dydx.v1.DydxService/GetFundingRates", {"ticker": "BTC-USD"}
        )
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert key in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


class TestMCPProjection:
    """Test the actual MCP JSON-RPC protocol over stdio."""

    @staticmethod
    def _mcp_request(msg_id, method, params=None):
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            msg["params"] = params
        return json.dumps(msg)

    @staticmethod
    def _run_mcp_session(messages: list[str]) -> list[dict]:
        import subprocess
        import sys

        stdin_data = "\n".join(messages) + "\n"

        script = f"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent / "src"))

from dydx_mcp.gen.dydx.v1 import dydx_pb2 as pb
from dydx_mcp.service import DydxService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/perpetualMarkets" in url and "/candles/" not in url:
        resp.json.return_value = {{
            "markets": {{
                "BTC-USD": {{
                    "ticker": "BTC-USD",
                    "status": "ACTIVE",
                    "oraclePrice": "97500.00",
                    "priceChange24H": "0.0215",
                    "volume24H": "1250000000.50",
                    "openInterest": "4500.123",
                    "nextFundingRate": "0.000125",
                    "stepSize": "0.0001",
                    "tickSize": "1",
                    "initialMarginFraction": "0.05",
                    "maintenanceMarginFraction": "0.03",
                    "openInterestUSDC": "438761175.00",
                }},
            }},
        }}
    elif "/orderbooks/" in url:
        resp.json.return_value = {{
            "bids": [{{"price": "97500.00", "size": "1.5"}}],
            "asks": [{{"price": "97501.00", "size": "1.2"}}],
        }}
    elif "/trades/" in url:
        resp.json.return_value = {{
            "trades": [{{
                "id": "trade-001",
                "side": "BUY",
                "price": "97500.50",
                "size": "0.5",
                "createdAt": "2026-03-12T10:30:00.000Z",
            }}],
        }}
    elif "/candles/" in url:
        resp.json.return_value = {{
            "candles": [{{
                "startedAt": "2026-03-12T10:00:00.000Z",
                "open": "97400.00",
                "high": "97600.00",
                "low": "97350.00",
                "close": "97500.00",
                "baseTokenVolume": "125.5",
                "usdVolume": "12231250.00",
                "trades": 1542,
                "resolution": "1HOUR",
            }}],
        }}
    elif "/historicalFunding/" in url:
        resp.json.return_value = {{
            "historicalFunding": [{{
                "ticker": "BTC-USD",
                "rate": "0.000125",
                "price": "97500.00",
                "effectiveAt": "2026-03-12T10:00:00.000Z",
            }}],
        }}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = DydxService.__new__(DydxService)
svc._base_url = "https://indexer.dydx.trade/v4"
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-dydx", version="0.0.1")
server.register(svc)
server.serve(mcp=True)
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=10,
        )

        responses = []
        for line in proc.stdout.strip().split("\n"):
            if line.strip():
                responses.append(json.loads(line))
        return responses

    def test_initialize(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }),
        ])
        assert len(responses) == 1
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["result"]["serverInfo"]["name"] == "test-dydx"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 5
        names = {t["name"] for t in tools}
        assert "DydxService.ListMarkets" in names
        assert "DydxService.GetOrderbook" in names
        assert "DydxService.GetTrades" in names
        assert "DydxService.GetCandles" in names
        assert "DydxService.GetFundingRates" in names

    def test_tool_call_list_markets(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DydxService.ListMarkets",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "markets" in result

    def test_tool_call_get_orderbook(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DydxService.GetOrderbook",
                "arguments": {"ticker": "BTC-USD"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "bids" in result
        assert "asks" in result

    def test_tool_call_get_funding_rates(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DydxService.GetFundingRates",
                "arguments": {"ticker": "BTC-USD"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        key = "fundingRates" if "fundingRates" in result else "funding_rates"
        assert key in result

    def test_unknown_tool(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DoesNotExist",
                "arguments": {},
            }),
        ])
        resp = responses[1]
        assert "error" in resp or resp.get("result", {}).get("isError") is True

    def test_ping(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "ping", {}),
        ])
        assert responses[1]["result"] == {}


class TestInterceptor:
    def test_interceptor_fires(self, server):
        calls = []

        def logging_interceptor(request, context, info, handler):
            calls.append(info.full_method)
            return handler(request, context)

        server.use(logging_interceptor)
        server._cli(["DydxService", "ListMarkets"])
        assert len(calls) == 1
        assert calls[0] == "/dydx.v1.DydxService/ListMarkets"

    def test_interceptor_chain_order(self, server):
        order = []

        def interceptor_a(request, context, info, handler):
            order.append("A-before")
            resp = handler(request, context)
            order.append("A-after")
            return resp

        def interceptor_b(request, context, info, handler):
            order.append("B-before")
            resp = handler(request, context)
            order.append("B-after")
            return resp

        server.use(interceptor_a)
        server.use(interceptor_b)
        server._cli(["DydxService", "ListMarkets"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

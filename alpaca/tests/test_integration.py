"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 10

    def test_tool_names(self, server):
        expected = {
            "AlpacaService.GetAccount",
            "AlpacaService.GetPositions",
            "AlpacaService.GetPosition",
            "AlpacaService.PlaceOrder",
            "AlpacaService.GetOrders",
            "AlpacaService.CancelOrder",
            "AlpacaService.GetAsset",
            "AlpacaService.GetBars",
            "AlpacaService.GetLatestQuote",
            "AlpacaService.GetLatestTrade",
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
    def test_get_account(self, server):
        result = server._cli(["AlpacaService", "GetAccount"])
        assert result["id"] == "904837e3-3b76-47ec-b432-046db621571b"
        assert result.get("buyingPower") == 50000.0 or result.get("buying_power") == 50000.0

    def test_get_positions(self, server):
        result = server._cli(["AlpacaService", "GetPositions"])
        assert "positions" in result
        assert len(result["positions"]) == 2
        assert result["positions"][0]["symbol"] == "AAPL"

    def test_get_position(self, server):
        result = server._cli(
            ["AlpacaService", "GetPosition", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        assert result.get("qty") == "10"

    def test_place_order(self, server):
        result = server._cli(
            [
                "AlpacaService",
                "PlaceOrder",
                "-r",
                '{"symbol":"AAPL","qty":10,"side":"buy","type":"limit","time_in_force":"day","limit_price":180}',
            ]
        )
        assert result["symbol"] == "AAPL"
        assert result["status"] == "accepted"

    def test_get_orders(self, server):
        result = server._cli(["AlpacaService", "GetOrders"])
        assert "orders" in result
        assert len(result["orders"]) == 2

    def test_cancel_order(self, server):
        result = server._cli(
            [
                "AlpacaService",
                "CancelOrder",
                "-r",
                '{"order_id":"61e69015-8549-4baf-b96e-8c4c0c2a4bfc"}',
            ]
        )
        assert result["success"] is True

    def test_get_asset(self, server):
        result = server._cli(
            ["AlpacaService", "GetAsset", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."

    def test_get_bars(self, server):
        result = server._cli(
            [
                "AlpacaService",
                "GetBars",
                "-r",
                '{"symbol":"AAPL","timeframe":"1Day","start":"2025-01-13"}',
            ]
        )
        assert "bars" in result
        assert len(result["bars"]) == 2

    def test_get_latest_quote(self, server):
        result = server._cli(
            ["AlpacaService", "GetLatestQuote", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        assert result.get("bidPrice") == 182.25 or result.get("bid_price") == 182.25

    def test_get_latest_trade(self, server):
        result = server._cli(
            ["AlpacaService", "GetLatestTrade", "-r", '{"symbol":"AAPL"}']
        )
        assert result["symbol"] == "AAPL"
        assert result["price"] == 182.28

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["AlpacaService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "AlpacaService" in result
        assert "GetAccount" in result

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

    def test_get_account(self):
        result = self._post("/alpaca.v1.AlpacaService/GetAccount")
        assert result.get("buyingPower") == 50000.0 or result.get("buying_power") == 50000.0

    def test_get_positions(self):
        result = self._post("/alpaca.v1.AlpacaService/GetPositions")
        assert "positions" in result
        assert len(result["positions"]) == 2

    def test_place_order(self):
        result = self._post(
            "/alpaca.v1.AlpacaService/PlaceOrder",
            {"symbol": "AAPL", "qty": 10, "side": "buy", "type": "market", "time_in_force": "day"},
        )
        assert result["symbol"] == "AAPL"
        assert result["status"] == "accepted"

    def test_cancel_order(self):
        result = self._post(
            "/alpaca.v1.AlpacaService/CancelOrder",
            {"order_id": "abc-123"},
        )
        assert result["success"] is True

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
        """Spawn MCP server subprocess, pipe JSON-RPC messages, collect responses."""
        import subprocess
        import sys

        stdin_data = "\n".join(messages) + "\n"

        script = f"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb
from alpaca_mcp.service import AlpacaService
from invariant import Server

# Build mocked service.
http = MagicMock()

def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/v2/account" in url:
        resp.json.return_value = {{
            "id": "904837e3", "status": "ACTIVE", "currency": "USD",
            "buying_power": "50000.00", "cash": "25000.00", "portfolio_value": "75000.00",
            "equity": "75000.00", "last_equity": "74500.00",
            "long_market_value": "50000.00", "short_market_value": "0.00",
            "pattern_day_trader": False, "trading_blocked": False, "account_blocked": False,
        }}
    elif "/v2/positions" in url and "/v2/positions/" not in url:
        resp.json.return_value = [{{
            "symbol": "AAPL", "qty": "10", "avg_entry_price": "175.50",
            "current_price": "182.30", "market_value": "1823.00",
            "unrealized_pl": "68.00", "unrealized_plpc": "0.0387",
            "asset_class": "us_equity", "side": "long", "exchange": "NASDAQ",
            "cost_basis": "1755.00",
        }}]
    elif "/v2/orders" in url:
        resp.json.return_value = [{{
            "id": "abc-123", "symbol": "AAPL", "qty": "10", "filled_qty": "0",
            "side": "buy", "type": "limit", "time_in_force": "day",
            "limit_price": "180.00", "stop_price": None, "filled_avg_price": None,
            "status": "new", "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T10:00:01Z", "submitted_at": "2025-01-15T10:00:00Z",
            "filled_at": None, "asset_class": "us_equity",
        }}]
    elif "/v2/stocks/" in url and "/quotes/latest" in url:
        resp.json.return_value = {{
            "quote": {{"bp": 182.25, "bs": 3, "ap": 182.30, "as": 5,
                "t": "2025-01-15T15:30:00.123Z"}},
            "symbol": "AAPL",
        }}
    elif "/v2/stocks/" in url and "/trades/latest" in url:
        resp.json.return_value = {{
            "trade": {{"p": 182.28, "s": 100, "x": "V",
                "t": "2025-01-15T15:30:00.456Z"}},
            "symbol": "AAPL",
        }}
    elif "/v2/stocks/" in url and "/bars" in url:
        resp.json.return_value = {{
            "bars": [{{
                "t": "2025-01-13T05:00:00Z", "o": 178.50, "h": 182.00,
                "l": 177.80, "c": 181.20, "v": 65000000, "vw": 180.10, "n": 850000,
            }}],
            "symbol": "AAPL",
        }}
    else:
        resp.json.return_value = {{}}
    return resp

def mock_post(url, json=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/v2/orders" in url:
        resp.json.return_value = {{
            "id": "order-123", "status": "accepted", "symbol": "AAPL",
            "qty": "10", "side": "buy", "type": "market",
            "time_in_force": "day", "created_at": "2025-01-15T10:00:00Z",
        }}
    else:
        resp.json.return_value = {{}}
    return resp

def mock_delete(url):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    return resp

http.get = MagicMock(side_effect=mock_get)
http.post = MagicMock(side_effect=mock_post)
http.delete = MagicMock(side_effect=mock_delete)

svc = AlpacaService.__new__(AlpacaService)
svc._http = http
svc._base_url = "https://paper-api.alpaca.markets"
svc._data_url = "https://data.alpaca.markets"
svc._api_key = "test"
svc._secret_key = "test"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-alpaca", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-alpaca"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) == 10
        names = {t["name"] for t in tools}
        assert "AlpacaService.GetAccount" in names
        assert "AlpacaService.PlaceOrder" in names
        assert "AlpacaService.GetBars" in names

    def test_tools_have_descriptions_and_schemas(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        for tool in responses[1]["result"]["tools"]:
            assert tool["description"], f"{tool['name']} missing description"
            assert tool["inputSchema"]["type"] == "object"

    def test_tool_call_get_account(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlpacaService.GetAccount",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        result = json.loads(content[0]["text"])
        assert result["id"] == "904837e3"

    def test_tool_call_place_order(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlpacaService.PlaceOrder",
                "arguments": {
                    "symbol": "AAPL",
                    "qty": 10,
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "day",
                },
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["status"] == "accepted"
        assert result["symbol"] == "AAPL"

    def test_tool_call_get_latest_quote(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "AlpacaService.GetLatestQuote",
                "arguments": {"symbol": "AAPL"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["symbol"] == "AAPL"
        assert result.get("bidPrice") == 182.25 or result.get("bid_price") == 182.25

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

    def test_unknown_method(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "unknown/method", {}),
        ])
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_notification_ignored(self):
        """Notifications (no id) should not produce a response."""
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            # Notification — no id field.
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
        # Should only get responses for id=0 and id=2, not the notification.
        ids = [r.get("id") for r in responses]
        assert 0 in ids
        assert 2 in ids
        assert len(responses) == 2


class TestInterceptor:
    def test_interceptor_fires(self, server):
        calls = []

        def logging_interceptor(request, context, info, handler):
            calls.append(info.full_method)
            return handler(request, context)

        server.use(logging_interceptor)
        server._cli(["AlpacaService", "GetAccount"])
        assert len(calls) == 1
        assert calls[0] == "/alpaca.v1.AlpacaService/GetAccount"

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
        server._cli(["AlpacaService", "GetPositions"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

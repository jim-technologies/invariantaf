"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from curve_mcp.gen.curve.v1 import curve_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 8

    def test_tool_names(self, server):
        expected = {
            "CurveService.GetPools",
            "CurveService.GetApys",
            "CurveService.GetVolumes",
            "CurveService.GetTVL",
            "CurveService.GetFactoryTVL",
            "CurveService.GetWeeklyFees",
            "CurveService.GetETHPrice",
            "CurveService.GetSubgraphData",
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
    def test_get_pools(self, server):
        result = server._cli(["CurveService", "GetPools"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_pools_with_params(self, server):
        result = server._cli(
            [
                "CurveService",
                "GetPools",
                "-r",
                json.dumps({"blockchainId": "ethereum", "registryId": "main"}),
            ]
        )
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_apys(self, server):
        result = server._cli(["CurveService", "GetApys"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_volumes(self, server):
        result = server._cli(["CurveService", "GetVolumes"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_tvl(self, server):
        result = server._cli(["CurveService", "GetTVL"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_factory_tvl(self, server):
        result = server._cli(["CurveService", "GetFactoryTVL"])
        key = "factoryBalances" if "factoryBalances" in result else "factory_balances"
        assert key in result

    def test_get_weekly_fees(self, server):
        result = server._cli(["CurveService", "GetWeeklyFees"])
        key = "weeklyFees" if "weeklyFees" in result else "weekly_fees"
        assert key in result

    def test_get_eth_price(self, server):
        result = server._cli(["CurveService", "GetETHPrice"])
        assert "price" in result
        assert isinstance(result["price"], (int, float))

    def test_get_subgraph_data(self, server):
        result = server._cli(["CurveService", "GetSubgraphData"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["CurveService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "CurveService" in result
        assert "GetPools" in result

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

    def test_get_pools(self):
        result = self._post("/curve.v1.CurveService/GetPools")
        assert "pools" in result

    def test_get_eth_price(self):
        result = self._post("/curve.v1.CurveService/GetETHPrice")
        assert "price" in result

    def test_get_factory_tvl(self):
        result = self._post("/curve.v1.CurveService/GetFactoryTVL")
        assert result.get("factoryBalances") or result.get("factory_balances")

    def test_get_weekly_fees(self):
        result = self._post("/curve.v1.CurveService/GetWeeklyFees")
        assert result.get("weeklyFees") or result.get("weekly_fees")

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

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from curve_mcp.gen.curve.v1 import curve_pb2 as pb
from curve_mcp.service import CurveService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None, follow_redirects=True):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/getPools/" in url:
        resp.json.return_value = {{"success": True, "data": {{"poolData": [
            {{"id": "0", "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
              "coinsAddresses": ["0x6B175474E89094C44Da98b954EedeAC495271d0F"],
              "decimals": ["18"], "virtualPrice": "1039823717130252926",
              "amplificationCoefficient": "4000", "totalSupply": "156223868197810822899967769",
              "name": "Curve.fi DAI/USDC/USDT", "assetType": "0",
              "lpTokenAddress": "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
              "symbol": "3Crv", "implementation": "", "assetTypeName": "usd",
              "coins": [{{"address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                "usdPrice": 1.0, "decimals": "18", "isBasePoolLpToken": False,
                "symbol": "DAI", "name": "Dai Stablecoin",
                "poolBalance": "58523366064329938326677617"}}],
              "poolUrls": {{"swap": [], "deposit": [], "withdraw": []}},
              "usdTotal": 162456848.37, "isMetaPool": False,
              "gaugeAddress": "", "gaugeRewards": [], "gaugeCrvApy": [],
              "isBroken": False, "creationTs": 1600000000, "creationBlockNumber": 10809473}}
        ]}}}}
    elif "/getSubgraphData/" in url:
        resp.json.return_value = {{"success": True, "data": {{"poolList": [
            {{"address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
              "latestDailyApy": 1.49, "latestWeeklyApy": 1.47,
              "type": "main", "virtualPrice": 1039823717130228200,
              "volumeUSD": 396294.19}}
        ]}}}}
    elif "/getVolumes" in url:
        resp.json.return_value = {{"success": True, "data": {{"pools": [
            {{"address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
              "type": "main", "volumeUSD": 396294.19,
              "latestDailyApyPcent": 1.49, "latestWeeklyApyPcent": 1.47,
              "includedApyPcentFromLsts": 0, "virtualPrice": 1039823717130228200}}
        ]}}}}
    elif "/getTVL" in url:
        resp.json.return_value = {{"success": True, "data": {{"poolData": [
            {{"id": "0", "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
              "name": "3pool", "symbol": "3Crv", "assetTypeName": "usd",
              "coins": [], "usdTotal": 162456848.37, "isMetaPool": False,
              "amplificationCoefficient": "4000", "virtualPrice": "1039823717130252926",
              "lpTokenAddress": "", "implementation": "", "gaugeAddress": "",
              "gaugeRewards": [], "gaugeCrvApy": [], "poolUrls": {{"swap": [], "deposit": [], "withdraw": []}},
              "totalSupply": "0", "coinsAddresses": [], "decimals": [],
              "isBroken": False, "creationTs": 0, "creationBlockNumber": 0}}
        ]}}}}
    elif "/getFactoryTVL" in url:
        resp.json.return_value = {{"success": True, "data": {{"factoryBalances": 81615253.25}}}}
    elif "/getWeeklyFees" in url:
        resp.json.return_value = {{"success": True, "data": {{
            "weeklyFeesTable": [{{"date": "Thu Mar 12 2026", "ts": 1773273600000, "rawFees": 0}}],
            "totalFees": {{"fees": 170504253.43}}
        }}}}
    elif "/getETHprice" in url:
        resp.json.return_value = {{"success": True, "data": {{"price": 2028.76}}}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = CurveService.__new__(CurveService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-curve", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-curve"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 8
        names = {t["name"] for t in tools}
        assert "CurveService.GetPools" in names
        assert "CurveService.GetETHPrice" in names
        assert "CurveService.GetWeeklyFees" in names

    def test_tool_call_get_pools(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CurveService.GetPools",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "pools" in result
        assert result["pools"][0]["name"] == "Curve.fi DAI/USDC/USDT"

    def test_tool_call_get_eth_price(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CurveService.GetETHPrice",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "price" in result
        assert result["price"] == 2028.76

    def test_tool_call_get_factory_tvl(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CurveService.GetFactoryTVL",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("factoryBalances") or result.get("factory_balances")

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
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
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
        server._cli(["CurveService", "GetETHPrice"])
        assert len(calls) == 1
        assert calls[0] == "/curve.v1.CurveService/GetETHPrice"

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
        server._cli(["CurveService", "GetPools"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

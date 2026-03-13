"""Integration tests -- verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from yearn_mcp.gen.yearn.v1 import yearn_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 3

    def test_tool_names(self, server):
        expected = {
            "YearnService.ListVaults",
            "YearnService.GetVault",
            "YearnService.ListAllVaults",
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
    def test_list_vaults(self, server):
        result = server._cli(["YearnService", "ListVaults"])
        assert "vaults" in result
        assert len(result["vaults"]) == 2

    def test_list_vaults_with_chain(self, server):
        result = server._cli(
            ["YearnService", "ListVaults", "-r", '{"chainId": 10}']
        )
        assert "vaults" in result
        assert len(result["vaults"]) == 1

    def test_get_vault(self, server):
        result = server._cli(
            [
                "YearnService",
                "GetVault",
                "-r",
                json.dumps({
                    "chainId": 1,
                    "address": "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
                }),
            ]
        )
        assert "vault" in result
        v = result["vault"]
        assert v["address"] == "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213"

    def test_list_all_vaults(self, server):
        result = server._cli(["YearnService", "ListAllVaults"])
        assert "vaults" in result
        assert len(result["vaults"]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["YearnService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "YearnService" in result
        assert "ListVaults" in result

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

    def test_list_vaults(self):
        result = self._post("/yearn.v1.YearnService/ListVaults")
        assert "vaults" in result

    def test_get_vault(self):
        result = self._post(
            "/yearn.v1.YearnService/GetVault",
            {"chainId": 1, "address": "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213"},
        )
        assert "vault" in result

    def test_list_all_vaults(self):
        result = self._post("/yearn.v1.YearnService/ListAllVaults")
        assert "vaults" in result

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

from yearn_mcp.gen.yearn.v1 import yearn_pb2 as pb
from yearn_mcp.service import YearnService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/1/vaults/all" in url:
        resp.json.return_value = [
            {{"address": "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
              "type": "Yearn Vault", "kind": "Legacy",
              "symbol": "yvCurve-YFIETH-f", "displaySymbol": "yvCurve-YFIETH-f",
              "name": "Curve YFIETH Factory yVault", "displayName": "Curve YFIETH Factory yVault",
              "icon": "", "version": "0.4.6", "category": "Curve",
              "decimals": 18, "chainID": 1, "endorsed": True, "boosted": False,
              "emergency_shutdown": False,
              "token": {{"address": "0x29059568bB40344487d62f7450E78b8E6C74e0e5",
                "underlyingTokensAddresses": [], "name": "Curve YFI/ETH",
                "symbol": "YFIETH-f", "type": "Curve", "decimals": 18}},
              "tvl": {{"totalAssets": "11605289578737060000", "tvl": 15234567.89, "price": 1312.45}},
              "apr": {{"type": "v2:averaged", "netAPR": 0.0523,
                "fees": {{"performance": 0.1, "management": 0.02}},
                "points": {{"weekAgo": 0.0498, "monthAgo": 0.0612, "inception": 0.0445}},
                "forwardAPR": {{"type": "crv", "netAPR": 0.0678,
                  "composite": {{"boost": 2.5, "poolAPY": 0.01, "boostedAPR": 0.05,
                    "baseAPR": 0.02, "cvxAPR": 0.005, "rewardsAPR": 0.003}}}}}},
              "strategies": [{{"address": "0xABC123def456",
                "name": "StrategyCurveBoostedFactory-YFIETH", "status": "Active",
                "details": {{"totalDebt": "10000000000000000000", "totalLoss": "0",
                  "totalGain": "500000000000000000", "performanceFee": 0,
                  "lastReport": 1700000000, "debtRatio": 10000}}}}],
              "details": {{"isRetired": False, "isHidden": False, "isBoosted": False,
                "isAutomated": False, "isPool": True, "poolProvider": "Curve",
                "stability": "Volatile", "category": "Volatile"}},
              "featuringScore": 7890123.45, "pricePerShare": "1050000000000000000"}}
        ]
    elif "/1/vaults/0x823976" in url:
        resp.json.return_value = {{
            "address": "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
            "type": "Yearn Vault", "kind": "Legacy",
            "symbol": "yvCurve-YFIETH-f", "displaySymbol": "yvCurve-YFIETH-f",
            "name": "Curve YFIETH Factory yVault", "displayName": "Curve YFIETH Factory yVault",
            "icon": "", "version": "0.4.6", "category": "Curve",
            "decimals": 18, "chainID": 1, "endorsed": True, "boosted": False,
            "emergency_shutdown": False,
            "token": {{"address": "0x29059568bB40344487d62f7450E78b8E6C74e0e5",
              "underlyingTokensAddresses": [], "name": "Curve YFI/ETH",
              "symbol": "YFIETH-f", "type": "Curve", "decimals": 18}},
            "tvl": {{"totalAssets": "11605289578737060000", "tvl": 15234567.89, "price": 1312.45}},
            "apr": {{"type": "v2:averaged", "netAPR": 0.0523,
              "fees": {{"performance": 0.1, "management": 0.02}},
              "points": {{"weekAgo": 0.0498, "monthAgo": 0.0612, "inception": 0.0445}},
              "forwardAPR": {{"type": "crv", "netAPR": 0.0678,
                "composite": {{"boost": 2.5, "poolAPY": 0.01, "boostedAPR": 0.05,
                  "baseAPR": 0.02, "cvxAPR": 0.005, "rewardsAPR": 0.003}}}}}},
            "strategies": [],
            "details": {{"isRetired": False, "isHidden": False, "isBoosted": False,
              "isAutomated": False, "isPool": True, "poolProvider": "Curve",
              "stability": "Volatile", "category": "Volatile"}},
            "featuringScore": 7890123.45, "pricePerShare": "1050000000000000000"}}
    else:
        resp.json.return_value = []
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = YearnService.__new__(YearnService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-yearn", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-yearn"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 3
        names = {t["name"] for t in tools}
        assert "YearnService.ListVaults" in names
        assert "YearnService.GetVault" in names
        assert "YearnService.ListAllVaults" in names

    def test_tool_call_list_vaults(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "YearnService.ListVaults",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "vaults" in result
        assert result["vaults"][0]["address"] == "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213"

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
        server._cli(["YearnService", "ListVaults"])
        assert len(calls) == 1
        assert calls[0] == "/yearn.v1.YearnService/ListVaults"

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
        server._cli(["YearnService", "ListVaults"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

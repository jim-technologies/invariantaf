"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from defillama_mcp.gen.defillama.v1 import defillama_pb2 as pb
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
            "DefiLlamaService.GetProtocols",
            "DefiLlamaService.GetProtocol",
            "DefiLlamaService.GetTVL",
            "DefiLlamaService.GetChains",
            "DefiLlamaService.GetGlobalTVL",
            "DefiLlamaService.GetStablecoins",
            "DefiLlamaService.GetYieldPools",
            "DefiLlamaService.GetDexVolumes",
            "DefiLlamaService.GetFees",
            "DefiLlamaService.GetStablecoinChains",
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
    def test_get_protocols(self, server):
        result = server._cli(["DefiLlamaService", "GetProtocols"])
        assert "protocols" in result
        assert len(result["protocols"]) == 2

    def test_get_protocol(self, server):
        result = server._cli(
            ["DefiLlamaService", "GetProtocol", "-r", '{"slug":"aave"}']
        )
        assert "protocol" in result
        p = result["protocol"]
        assert p["name"] == "Aave"

    def test_get_tvl(self, server):
        result = server._cli(
            ["DefiLlamaService", "GetTVL", "-r", '{"slug":"aave"}']
        )
        assert result.get("tvl") == 26446474028

    def test_get_chains(self, server):
        result = server._cli(["DefiLlamaService", "GetChains"])
        assert "chains" in result
        assert len(result["chains"]) == 2

    def test_get_global_tvl(self, server):
        result = server._cli(["DefiLlamaService", "GetGlobalTVL"])
        key = "dataPoints" if "dataPoints" in result else "data_points"
        assert key in result
        assert len(result[key]) == 3

    def test_get_stablecoins(self, server):
        result = server._cli(["DefiLlamaService", "GetStablecoins"])
        assert "stablecoins" in result
        assert len(result["stablecoins"]) == 2

    def test_get_yield_pools(self, server):
        result = server._cli(["DefiLlamaService", "GetYieldPools"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_dex_volumes(self, server):
        result = server._cli(["DefiLlamaService", "GetDexVolumes"])
        assert result.get("total24h") or result.get("total_24h")
        assert "protocols" in result

    def test_get_fees(self, server):
        result = server._cli(["DefiLlamaService", "GetFees"])
        assert result.get("total24h") or result.get("total_24h")
        assert "protocols" in result

    def test_get_stablecoin_chains(self, server):
        result = server._cli(["DefiLlamaService", "GetStablecoinChains"])
        assert "chains" in result
        assert len(result["chains"]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["DefiLlamaService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "DefiLlamaService" in result
        assert "GetProtocols" in result

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

    def test_get_protocols(self):
        result = self._post("/defillama.v1.DefiLlamaService/GetProtocols")
        assert "protocols" in result

    def test_get_tvl(self):
        result = self._post(
            "/defillama.v1.DefiLlamaService/GetTVL",
            {"slug": "aave"},
        )
        assert "tvl" in result

    def test_get_chains(self):
        result = self._post("/defillama.v1.DefiLlamaService/GetChains")
        assert "chains" in result

    def test_get_dex_volumes(self):
        result = self._post("/defillama.v1.DefiLlamaService/GetDexVolumes")
        assert "protocols" in result

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

from defillama_mcp.gen.defillama.v1 import defillama_pb2 as pb
from defillama_mcp.service import DefiLlamaService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/protocols" in url and "/protocol/" not in url:
        resp.json.return_value = [
            {{"id": "111", "name": "Aave", "symbol": "AAVE", "url": "https://aave.com",
              "description": "Lending protocol", "chain": "Multi-Chain",
              "logo": "", "category": "Lending", "chains": ["Ethereum"],
              "tvl": 26000000000, "change_1h": 0.1, "change_1d": 1.5,
              "change_7d": 5.2, "slug": "aave", "twitter": "AaveAave", "mcap": 4500000000}}
        ]
    elif "/protocol/" in url:
        resp.json.return_value = {{
            "id": "111", "name": "Aave", "url": "https://aave.com",
            "description": "Lending", "logo": "", "symbol": "AAVE",
            "chains": ["Ethereum"], "gecko_id": "aave", "twitter": "AaveAave",
            "tvl": [{{"date": 1589932800, "totalLiquidityUSD": 54026260}}],
            "currentChainTvls": {{"Ethereum": 20000000000}},
            "mcap": 4500000000, "category": "Lending"}}
    elif "/tvl/" in url:
        resp.json.return_value = 26446474028
    elif "/v2/chains" in url:
        resp.json.return_value = [
            {{"gecko_id": "ethereum", "tvl": 60000000000, "tokenSymbol": "ETH",
              "name": "Ethereum", "chainId": 1}}
        ]
    elif "/v2/historicalChainTvl" in url:
        resp.json.return_value = [
            {{"date": 1506470400, "tvl": 0}},
            {{"date": 1506556800, "tvl": 100000}}
        ]
    elif "/stablecoins" in url and "/stablecoinchains" not in url:
        resp.json.return_value = {{"peggedAssets": [
            {{"id": "1", "name": "Tether", "symbol": "USDT", "gecko_id": "tether",
              "pegType": "peggedUSD", "pegMechanism": "fiat-backed",
              "circulating": {{"peggedUSD": 183620774070.14}},
              "circulatingPrevDay": {{"peggedUSD": 183458165919.49}},
              "circulatingPrevWeek": {{"peggedUSD": 183576475732.69}},
              "circulatingPrevMonth": {{"peggedUSD": 185318552614.40}}}}
        ]}}
    elif "/pools" in url:
        resp.json.return_value = {{"status": "success", "data": [
            {{"chain": "Ethereum", "project": "lido", "symbol": "STETH",
              "tvlUsd": 18312039691, "apyBase": 2.501, "apyReward": None,
              "apy": 2.501, "pool": "747c1d2a", "apyPct1D": 0.122,
              "apyPct7D": 0.134, "apyPct30D": -1.116, "stablecoin": False,
              "ilRisk": "no", "exposure": "single",
              "predictions": {{"predictedClass": "Stable/Up", "predictedProbability": 73}}}}
        ]}}
    elif "/overview/dexs" in url:
        resp.json.return_value = {{
            "total24h": 9702385010, "total7d": 59826406024, "total30d": 200000000000,
            "change_1d": 17.74, "change_7d": 5.2, "change_1m": -10.3,
            "allChains": ["Ethereum", "Solana"],
            "protocols": [{{"name": "Uniswap", "slug": "uniswap", "logo": "",
              "category": "Dexes", "chains": ["Ethereum"],
              "total24h": 3000000000, "total7d": 20000000000, "total30d": 80000000000,
              "change_1d": 10.5, "change_7d": 3.2, "change_1m": -5.1}}]}}
    elif "/overview/fees" in url:
        resp.json.return_value = {{
            "total24h": 50000000, "total7d": 350000000, "total30d": 1500000000,
            "change_1d": 5.5, "change_7d": -2.3, "change_1m": 12.0,
            "protocols": [{{"name": "Ethereum", "slug": "ethereum", "logo": "",
              "category": "Chain", "chains": ["Ethereum"],
              "total24h": 20000000, "total7d": 140000000, "total30d": 600000000,
              "change_1d": 3.0, "change_7d": -1.5, "change_1m": 8.0}}]}}
    elif "/stablecoinchains" in url:
        resp.json.return_value = [
            {{"gecko_id": "ethereum", "totalCirculatingUSD": {{"peggedUSD": 100000000000}},
              "tokenSymbol": "ETH", "name": "Ethereum"}}
        ]
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = DefiLlamaService.__new__(DefiLlamaService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-dl", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-dl"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "DefiLlamaService.GetProtocols" in names
        assert "DefiLlamaService.GetChains" in names
        assert "DefiLlamaService.GetDexVolumes" in names

    def test_tool_call_get_protocols(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DefiLlamaService.GetProtocols",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "protocols" in result
        assert result["protocols"][0]["name"] == "Aave"

    def test_tool_call_get_chains(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DefiLlamaService.GetChains",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "chains" in result
        assert result["chains"][0]["name"] == "Ethereum"

    def test_tool_call_get_dex_volumes(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DefiLlamaService.GetDexVolumes",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("total24h") or result.get("total_24h")

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
            # notification — no id field
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
        server._cli(["DefiLlamaService", "GetChains"])
        assert len(calls) == 1
        assert calls[0] == "/defillama.v1.DefiLlamaService/GetChains"

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
        server._cli(["DefiLlamaService", "GetProtocols"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

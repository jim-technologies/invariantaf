"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from orca_mcp.gen.orca.v1 import orca_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 9

    def test_tool_names(self, server):
        expected = {
            "OrcaService.ListPools",
            "OrcaService.GetPool",
            "OrcaService.SearchPools",
            "OrcaService.ListTokens",
            "OrcaService.GetToken",
            "OrcaService.SearchTokens",
            "OrcaService.GetProtocolStats",
            "OrcaService.GetProtocolToken",
            "OrcaService.GetLockedLiquidity",
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
    def test_list_pools(self, server):
        result = server._cli(["OrcaService", "ListPools"])
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_get_pool(self, server):
        result = server._cli(
            ["OrcaService", "GetPool", "-r", '{"address":"Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"}']
        )
        assert "pool" in result
        p = result["pool"]
        assert p["address"] == "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

    def test_search_pools(self, server):
        result = server._cli(
            ["OrcaService", "SearchPools", "-r", '{"query":"SOL-USDC"}']
        )
        assert "pools" in result
        assert len(result["pools"]) == 2

    def test_list_tokens(self, server):
        result = server._cli(["OrcaService", "ListTokens"])
        assert "tokens" in result
        assert len(result["tokens"]) == 2

    def test_get_token(self, server):
        result = server._cli(
            ["OrcaService", "GetToken", "-r", '{"mintAddress":"orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"}']
        )
        assert "token" in result
        t = result["token"]
        assert t["metadata"]["symbol"] == "ORCA"

    def test_search_tokens(self, server):
        result = server._cli(
            ["OrcaService", "SearchTokens", "-r", '{"query":"ORCA"}']
        )
        assert "tokens" in result
        assert len(result["tokens"]) == 2

    def test_get_protocol_stats(self, server):
        result = server._cli(["OrcaService", "GetProtocolStats"])
        assert "tvl" in result
        assert result.get("volume24hUsdc") or result.get("volume_24h_usdc")

    def test_get_protocol_token(self, server):
        result = server._cli(["OrcaService", "GetProtocolToken"])
        assert result.get("symbol") == "ORCA"
        assert result.get("name") == "Orca"

    def test_get_locked_liquidity(self, server):
        result = server._cli(
            ["OrcaService", "GetLockedLiquidity", "-r", '{"address":"Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"}']
        )
        assert "entries" in result
        assert len(result["entries"]) == 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OrcaService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "OrcaService" in result
        assert "ListPools" in result

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

    def test_list_pools(self):
        result = self._post("/orca.v1.OrcaService/ListPools")
        assert "pools" in result

    def test_get_pool(self):
        result = self._post(
            "/orca.v1.OrcaService/GetPool",
            {"address": "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"},
        )
        assert "pool" in result

    def test_get_protocol_stats(self):
        result = self._post("/orca.v1.OrcaService/GetProtocolStats")
        assert "tvl" in result

    def test_get_protocol_token(self):
        result = self._post("/orca.v1.OrcaService/GetProtocolToken")
        assert "symbol" in result

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

from orca_mcp.gen.orca.v1 import orca_pb2 as pb
from orca_mcp.service import OrcaService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/pools/search" in url:
        resp.json.return_value = {{"data": [
            {{"address": "pool1", "whirlpoolsConfig": "", "tickSpacing": 64,
              "feeRate": 2000, "protocolFeeRate": 300, "liquidity": "1000",
              "sqrtPrice": "1000", "tickCurrentIndex": 0,
              "tokenMintA": "mint_a", "tokenMintB": "mint_b",
              "tokenA": {{"address": "mint_a", "programId": "", "imageUrl": "",
                "name": "SOL", "symbol": "SOL", "decimals": 9, "tags": []}},
              "tokenB": {{"address": "mint_b", "programId": "", "imageUrl": "",
                "name": "USDC", "symbol": "USDC", "decimals": 6, "tags": []}},
              "price": "135.50", "tvlUsdc": "10000000", "yieldOverTvl": "0.05",
              "tokenBalanceA": "100", "tokenBalanceB": "13550",
              "stats": {{"24h": {{"volume": "1000000", "fees": "2000",
                "rewards": None, "yieldOverTvl": "0.002"}},
                "7d": {{"volume": "7000000", "fees": "14000",
                  "rewards": None, "yieldOverTvl": "0.014"}},
                "30d": {{"volume": "30000000", "fees": "60000",
                  "rewards": None, "yieldOverTvl": "0.06"}}}},
              "rewards": [], "lockedLiquidityPercent": [],
              "hasWarning": False, "poolType": "concentrated",
              "updatedAt": "2026-01-01T00:00:00Z"}}
        ]}}
    elif "/pools/" in url and "/pools" != url.split("?")[0].split("/")[-1]:
        resp.json.return_value = {{"data": {{
            "address": "pool1", "whirlpoolsConfig": "", "tickSpacing": 64,
            "feeRate": 2000, "protocolFeeRate": 300, "liquidity": "1000",
            "sqrtPrice": "1000", "tickCurrentIndex": 0,
            "tokenMintA": "mint_a", "tokenMintB": "mint_b",
            "tokenA": {{"address": "mint_a", "programId": "", "imageUrl": "",
              "name": "SOL", "symbol": "SOL", "decimals": 9, "tags": []}},
            "tokenB": {{"address": "mint_b", "programId": "", "imageUrl": "",
              "name": "USDC", "symbol": "USDC", "decimals": 6, "tags": []}},
            "price": "135.50", "tvlUsdc": "10000000", "yieldOverTvl": "0.05",
            "tokenBalanceA": "100", "tokenBalanceB": "13550",
            "stats": {{"24h": {{"volume": "1000000", "fees": "2000",
              "rewards": None, "yieldOverTvl": "0.002"}},
              "7d": {{"volume": "7000000", "fees": "14000",
                "rewards": None, "yieldOverTvl": "0.014"}},
              "30d": {{"volume": "30000000", "fees": "60000",
                "rewards": None, "yieldOverTvl": "0.06"}}}},
            "rewards": [], "lockedLiquidityPercent": [],
            "hasWarning": False, "poolType": "concentrated",
            "updatedAt": "2026-01-01T00:00:00Z"}}}}
    elif "/pools" in url:
        resp.json.return_value = {{"data": [
            {{"address": "pool1", "whirlpoolsConfig": "", "tickSpacing": 64,
              "feeRate": 2000, "protocolFeeRate": 300, "liquidity": "1000",
              "sqrtPrice": "1000", "tickCurrentIndex": 0,
              "tokenMintA": "mint_a", "tokenMintB": "mint_b",
              "tokenA": {{"address": "mint_a", "programId": "", "imageUrl": "",
                "name": "SOL", "symbol": "SOL", "decimals": 9, "tags": []}},
              "tokenB": {{"address": "mint_b", "programId": "", "imageUrl": "",
                "name": "USDC", "symbol": "USDC", "decimals": 6, "tags": []}},
              "price": "135.50", "tvlUsdc": "10000000", "yieldOverTvl": "0.05",
              "tokenBalanceA": "100", "tokenBalanceB": "13550",
              "stats": {{"24h": {{"volume": "1000000", "fees": "2000",
                "rewards": None, "yieldOverTvl": "0.002"}},
                "7d": {{"volume": "7000000", "fees": "14000",
                  "rewards": None, "yieldOverTvl": "0.014"}},
                "30d": {{"volume": "30000000", "fees": "60000",
                  "rewards": None, "yieldOverTvl": "0.06"}}}},
              "rewards": [], "lockedLiquidityPercent": [],
              "hasWarning": False, "poolType": "concentrated",
              "updatedAt": "2026-01-01T00:00:00Z"}}
        ]}}
    elif "/tokens/search" in url:
        resp.json.return_value = {{"data": [
            {{"address": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
              "supply": 74999565293160, "decimals": 6, "isInitialized": True,
              "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
              "priceUsdc": "3.45",
              "metadata": {{"name": "Orca", "symbol": "ORCA", "risk": 2, "image": ""}},
              "stats": {{"24h": {{"volume": 433016.17}}}},
              "updatedAt": "2026-01-01T00:00:00Z"}}
        ]}}
    elif "/tokens/" in url and "/tokens" != url.split("?")[0].split("/")[-1]:
        resp.json.return_value = {{"data": {{
            "address": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
            "supply": 74999565293160, "decimals": 6, "isInitialized": True,
            "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "priceUsdc": "3.45",
            "metadata": {{"name": "Orca", "symbol": "ORCA", "risk": 2, "image": ""}},
            "stats": {{"24h": {{"volume": 433016.17}}}},
            "updatedAt": "2026-01-01T00:00:00Z"}}}}
    elif "/tokens" in url:
        resp.json.return_value = {{"data": [
            {{"address": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
              "supply": 74999565293160, "decimals": 6, "isInitialized": True,
              "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
              "priceUsdc": "3.45",
              "metadata": {{"name": "Orca", "symbol": "ORCA", "risk": 2, "image": ""}},
              "stats": {{"24h": {{"volume": 433016.17}}}},
              "updatedAt": "2026-01-01T00:00:00Z"}}
        ]}}
    elif "/protocol/token" in url:
        resp.json.return_value = {{
            "symbol": "ORCA", "name": "Orca", "description": "",
            "imageUrl": "", "price": "3.45",
            "circulatingSupply": "50000000", "totalSupply": "100000000",
            "stats": {{"24h": {{"volume": "433016.17"}}}}}}
    elif "/protocol" in url:
        resp.json.return_value = {{
            "tvl": "1250000000.00", "volume24hUsdc": "350000000.00",
            "fees24hUsdc": "700000.00", "revenue24hUsdc": "210000.00"}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = OrcaService.__new__(OrcaService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-orca", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-orca"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 9
        names = {t["name"] for t in tools}
        assert "OrcaService.ListPools" in names
        assert "OrcaService.GetPool" in names
        assert "OrcaService.GetProtocolStats" in names

    def test_tool_call_list_pools(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OrcaService.ListPools",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "pools" in result
        pool = result["pools"][0]
        token_a = pool.get("tokenA") or pool.get("token_a")
        assert token_a["symbol"] == "SOL"

    def test_tool_call_get_protocol_stats(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OrcaService.GetProtocolStats",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "tvl" in result

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
        server._cli(["OrcaService", "ListPools"])
        assert len(calls) == 1
        assert calls[0] == "/orca.v1.OrcaService/ListPools"

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
        server._cli(["OrcaService", "ListPools"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

"""Integration tests -- verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from lifi_mcp.gen.lifi.v1 import lifi_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 6

    def test_tool_names(self, server):
        expected = {
            "LifiService.GetQuote",
            "LifiService.ListChains",
            "LifiService.ListTokens",
            "LifiService.GetConnections",
            "LifiService.ListTools",
            "LifiService.GetStatus",
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
    def test_list_chains(self, server):
        result = server._cli(["LifiService", "ListChains"])
        assert "chains" in result
        assert len(result["chains"]) == 2

    def test_list_tokens(self, server):
        result = server._cli(["LifiService", "ListTokens"])
        key = "chainTokens" if "chainTokens" in result else "chain_tokens"
        assert key in result
        assert len(result[key]) == 2

    def test_get_connections(self, server):
        result = server._cli(
            [
                "LifiService",
                "GetConnections",
                "-r",
                json.dumps({"fromChain": "1", "toChain": "42161"}),
            ]
        )
        assert "connections" in result
        assert len(result["connections"]) == 1

    def test_list_tools(self, server):
        result = server._cli(["LifiService", "ListTools"])
        assert "bridges" in result
        assert "exchanges" in result
        assert len(result["bridges"]) == 2
        assert len(result["exchanges"]) == 2

    def test_get_quote(self, server):
        result = server._cli(
            [
                "LifiService",
                "GetQuote",
                "-r",
                json.dumps(
                    {
                        "fromChain": "ETH",
                        "toChain": "ARB",
                        "fromToken": "ETH",
                        "toToken": "ETH",
                        "fromAmount": "1000000000000000000",
                        "fromAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                    }
                ),
            ]
        )
        assert result.get("tool") == "stargate"
        assert "action" in result
        assert "estimate" in result

    def test_get_status(self, server):
        result = server._cli(
            [
                "LifiService",
                "GetStatus",
                "-r",
                json.dumps({"txHash": "0xabc123"}),
            ]
        )
        assert result.get("status") == "DONE"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["LifiService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "LifiService" in result
        assert "GetQuote" in result

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

    def test_list_chains(self):
        result = self._post("/lifi.v1.LifiService/ListChains")
        assert "chains" in result

    def test_list_tools(self):
        result = self._post("/lifi.v1.LifiService/ListTools")
        assert "bridges" in result
        assert "exchanges" in result

    def test_get_quote(self):
        result = self._post(
            "/lifi.v1.LifiService/GetQuote",
            {
                "fromChain": "ETH",
                "toChain": "ARB",
                "fromToken": "ETH",
                "toToken": "ETH",
                "fromAmount": "1000000000000000000",
                "fromAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            },
        )
        assert result.get("tool") == "stargate"

    def test_get_status(self):
        result = self._post(
            "/lifi.v1.LifiService/GetStatus",
            {"txHash": "0xabc123"},
        )
        assert result.get("status") == "DONE"

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

from lifi_mcp.gen.lifi.v1 import lifi_pb2 as pb
from lifi_mcp.service import LifiService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/chains" in url and "/connections" not in url:
        resp.json.return_value = {{"chains": [
            {{"key": "eth", "chainType": "EVM", "name": "Ethereum", "coin": "ETH",
              "id": 1, "mainnet": True, "logoURI": "",
              "nativeToken": {{"address": "0x0000", "chainId": 1, "symbol": "ETH",
                "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                "logoURI": "", "priceUSD": "3500.00"}}}}
        ]}}
    elif "/tools" in url:
        resp.json.return_value = {{
            "bridges": [{{"key": "stargate", "name": "Stargate", "logoURI": "",
                "supportedChains": [{{"fromChainId": 1, "toChainId": 42161}}]}}],
            "exchanges": [{{"key": "uniswap", "name": "Uniswap", "logoURI": ""}}]
        }}
    elif "/quote" in url:
        resp.json.return_value = {{
            "type": "lifi", "id": "q1", "tool": "stargate",
            "toolDetails": {{"name": "Stargate", "logoURI": ""}},
            "action": {{
                "fromToken": {{"address": "0x0000", "chainId": 1, "symbol": "ETH",
                    "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                    "logoURI": "", "priceUSD": "3500.00"}},
                "fromAmount": "1000000000000000000",
                "toToken": {{"address": "0x0000", "chainId": 42161, "symbol": "ETH",
                    "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                    "logoURI": "", "priceUSD": "3500.00"}},
                "fromChainId": 1, "toChainId": 42161, "slippage": 0.03,
                "fromAddress": "0xABC", "toAddress": "0xABC"
            }},
            "estimate": {{
                "tool": "stargate", "approvalAddress": "0x123",
                "toAmountMin": "990000000000000000",
                "toAmount": "999000000000000000",
                "fromAmount": "1000000000000000000",
                "feeCosts": [], "gasCosts": [],
                "executionDuration": 120,
                "fromAmountUSD": "3500.00", "toAmountUSD": "3496.50"
            }},
            "includedSteps": [],
            "transactionRequest": {{
                "value": "0xde0b6b3a7640000", "to": "0x123",
                "data": "0xabcdef", "from": "0xABC",
                "chainId": 1, "gasPrice": "0x6fc23ac00", "gasLimit": "0x3d090"
            }}
        }}
    elif "/status" in url:
        resp.json.return_value = {{
            "transactionId": "0xabc123",
            "sending": {{"txHash": "0xsend123", "chainId": 1}},
            "receiving": {{"txHash": "0xrecv456", "chainId": 42161,
                "amount": "999000000000000000",
                "token": {{"address": "0x0000", "chainId": 42161, "symbol": "ETH",
                    "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                    "logoURI": "", "priceUSD": "3500.00"}}}},
            "status": "DONE", "substatus": "COMPLETED",
            "substatusMessage": "Done", "bridge": "stargate"
        }}
    elif "/tokens" in url:
        resp.json.return_value = {{"tokens": {{"1": [
            {{"address": "0x0000", "chainId": 1, "symbol": "ETH",
              "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
              "logoURI": "", "priceUSD": "3500.00"}}
        ]}}}}
    elif "/connections" in url:
        resp.json.return_value = {{"connections": [
            {{"fromChainId": 1, "toChainId": 42161,
              "fromTokens": [{{"address": "0x0000", "chainId": 1, "symbol": "ETH",
                "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                "logoURI": "", "priceUSD": "3500.00"}}],
              "toTokens": [{{"address": "0x0000", "chainId": 42161, "symbol": "ETH",
                "decimals": 18, "name": "Ethereum", "coinKey": "ETH",
                "logoURI": "", "priceUSD": "3500.00"}}]}}
        ]}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = LifiService.__new__(LifiService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-lifi", version="0.0.1")
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
        responses = self._run_mcp_session(
            [
                self._mcp_request(
                    0,
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                ),
            ]
        )
        assert len(responses) == 1
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["result"]["serverInfo"]["name"] == "test-lifi"

    def test_tools_list(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "tools/list", {}),
            ]
        )
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 6
        names = {t["name"] for t in tools}
        assert "LifiService.GetQuote" in names
        assert "LifiService.ListChains" in names
        assert "LifiService.ListTools" in names

    def test_tool_call_list_chains(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {
                        "name": "LifiService.ListChains",
                        "arguments": {},
                    },
                ),
            ]
        )
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "chains" in result
        assert result["chains"][0]["name"] == "Ethereum"

    def test_tool_call_get_quote(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {
                        "name": "LifiService.GetQuote",
                        "arguments": {
                            "fromChain": "ETH",
                            "toChain": "ARB",
                            "fromToken": "ETH",
                            "toToken": "ETH",
                            "fromAmount": "1000000000000000000",
                            "fromAddress": "0xABC",
                        },
                    },
                ),
            ]
        )
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("tool") == "stargate"

    def test_unknown_tool(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(
                    1,
                    "tools/call",
                    {
                        "name": "DoesNotExist",
                        "arguments": {},
                    },
                ),
            ]
        )
        resp = responses[1]
        assert "error" in resp or resp.get("result", {}).get("isError") is True

    def test_ping(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "ping", {}),
            ]
        )
        assert responses[1]["result"] == {}

    def test_unknown_method(self):
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                self._mcp_request(1, "unknown/method", {}),
            ]
        )
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_notification_ignored(self):
        """Notifications (no id) should not produce a response."""
        responses = self._run_mcp_session(
            [
                self._mcp_request(0, "initialize", {}),
                json.dumps(
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}
                ),
                self._mcp_request(2, "ping", {}),
            ]
        )
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
        server._cli(["LifiService", "ListChains"])
        assert len(calls) == 1
        assert calls[0] == "/lifi.v1.LifiService/ListChains"

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
        server._cli(["LifiService", "ListChains"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

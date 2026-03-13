"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from oneinch_mcp.gen.oneinch.v1 import oneinch_pb2 as pb
from tests.conftest import (
    DESCRIPTOR_PATH,
    USDC_ADDRESS,
    WALLET_ADDRESS,
    WETH_ADDRESS,
)


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 6

    def test_tool_names(self, server):
        expected = {
            "OneInchService.GetQuote",
            "OneInchService.GetSwap",
            "OneInchService.GetTokenPrice",
            "OneInchService.GetTokenInfo",
            "OneInchService.SearchTokens",
            "OneInchService.GetBalances",
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
    def test_get_quote(self, server):
        result = server._cli(
            [
                "OneInchService",
                "GetQuote",
                "-r",
                json.dumps(
                    {
                        "chainId": 1,
                        "src": WETH_ADDRESS,
                        "dst": USDC_ADDRESS,
                        "amount": "1000000000000000000",
                    }
                ),
            ]
        )
        assert "srcToken" in result or "src_token" in result
        assert "dstAmount" in result or "dst_amount" in result

    def test_get_swap(self, server):
        result = server._cli(
            [
                "OneInchService",
                "GetSwap",
                "-r",
                json.dumps(
                    {
                        "chainId": 1,
                        "src": WETH_ADDRESS,
                        "dst": USDC_ADDRESS,
                        "amount": "1000000000000000000",
                        "from": WALLET_ADDRESS,
                        "slippage": 1.0,
                    }
                ),
            ]
        )
        assert "tx" in result
        tx = result["tx"]
        assert "to" in tx
        assert "data" in tx

    def test_get_token_price(self, server):
        result = server._cli(
            [
                "OneInchService",
                "GetTokenPrice",
                "-r",
                json.dumps(
                    {
                        "chainId": 1,
                        "tokens": f"{WETH_ADDRESS},{USDC_ADDRESS}",
                    }
                ),
            ]
        )
        assert "prices" in result
        assert len(result["prices"]) == 2

    def test_get_token_info(self, server):
        result = server._cli(
            [
                "OneInchService",
                "GetTokenInfo",
                "-r",
                json.dumps({"chainId": 1, "address": WETH_ADDRESS}),
            ]
        )
        assert "token" in result
        token = result["token"]
        assert token.get("symbol") == "WETH"

    def test_search_tokens(self, server):
        result = server._cli(
            [
                "OneInchService",
                "SearchTokens",
                "-r",
                json.dumps({"chainId": 1, "query": "USD"}),
            ]
        )
        assert "tokens" in result
        assert len(result["tokens"]) == 2

    def test_get_balances(self, server):
        result = server._cli(
            [
                "OneInchService",
                "GetBalances",
                "-r",
                json.dumps({"chainId": 1, "address": WALLET_ADDRESS}),
            ]
        )
        assert "balances" in result
        assert len(result["balances"]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OneInchService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "OneInchService" in result
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

    def test_get_quote(self):
        result = self._post(
            "/oneinch.v1.OneInchService/GetQuote",
            {
                "chainId": 1,
                "src": WETH_ADDRESS,
                "dst": USDC_ADDRESS,
                "amount": "1000000000000000000",
            },
        )
        assert "srcToken" in result or "src_token" in result

    def test_get_token_price(self):
        result = self._post(
            "/oneinch.v1.OneInchService/GetTokenPrice",
            {"chainId": 1, "tokens": WETH_ADDRESS},
        )
        assert "prices" in result

    def test_search_tokens(self):
        result = self._post(
            "/oneinch.v1.OneInchService/SearchTokens",
            {"chainId": 1, "query": "USD"},
        )
        assert "tokens" in result

    def test_get_balances(self):
        result = self._post(
            "/oneinch.v1.OneInchService/GetBalances",
            {"chainId": 1, "address": WALLET_ADDRESS},
        )
        assert "balances" in result

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

from oneinch_mcp.gen.oneinch.v1 import oneinch_pb2 as pb
from oneinch_mcp.service import OneInchService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/search" in url:
        resp.json.return_value = [
            {{"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
              "symbol": "USDC", "name": "USD Coin", "decimals": 6,
              "logoURI": "https://tokens.1inch.io/usdc.png",
              "tags": ["tokens", "stablecoin"]}}
        ]
    elif "/quote" in url:
        resp.json.return_value = {{
            "srcToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "dstToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "srcAmount": "1000000000000000000",
            "dstAmount": "3500000000",
            "gas": 250000}}
    elif "/swap" in url:
        resp.json.return_value = {{
            "srcToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "dstToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "srcAmount": "1000000000000000000",
            "dstAmount": "3480000000",
            "tx": {{"to": "0x1111111254EEB25477B68fb85Ed929f73A960582",
                   "data": "0xabcdef", "value": "0", "gas": 250000,
                   "gasPrice": "30000000000"}}}}
    elif "/price/" in url:
        resp.json.return_value = {{
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 3500.42}}
    elif "/balances/" in url:
        resp.json.return_value = {{
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "500000000000000000",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "10000000000"}}
    elif "/token/" in url:
        resp.json.return_value = {{
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18,
            "logoURI": "https://tokens.1inch.io/weth.png",
            "tags": ["tokens"]}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = OneInchService.__new__(OneInchService)
svc._api_key = "test-key"
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-oneinch", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-oneinch"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 6
        names = {t["name"] for t in tools}
        assert "OneInchService.GetQuote" in names
        assert "OneInchService.GetSwap" in names
        assert "OneInchService.GetTokenPrice" in names
        assert "OneInchService.GetBalances" in names

    def test_tool_call_get_quote(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OneInchService.GetQuote",
                "arguments": {
                    "chainId": 1,
                    "src": WETH_ADDRESS,
                    "dst": USDC_ADDRESS,
                    "amount": "1000000000000000000",
                },
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "srcToken" in result or "src_token" in result

    def test_tool_call_search_tokens(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OneInchService.SearchTokens",
                "arguments": {"chainId": 1, "query": "USD"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "tokens" in result
        assert len(result["tokens"]) >= 1

    def test_tool_call_get_balances(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OneInchService.GetBalances",
                "arguments": {
                    "chainId": 1,
                    "address": WALLET_ADDRESS,
                },
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "balances" in result

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
        server._cli([
            "OneInchService",
            "GetQuote",
            "-r",
            json.dumps({
                "chainId": 1,
                "src": WETH_ADDRESS,
                "dst": USDC_ADDRESS,
                "amount": "1000000000000000000",
            }),
        ])
        assert len(calls) == 1
        assert calls[0] == "/oneinch.v1.OneInchService/GetQuote"

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
        server._cli([
            "OneInchService",
            "SearchTokens",
            "-r",
            json.dumps({"chainId": 1, "query": "USD"}),
        ])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

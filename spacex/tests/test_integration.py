"""Integration tests -- verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from spacex_mcp.gen.spacex.v1 import spacex_pb2 as pb
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
            "SpaceXService.GetLatestLaunch",
            "SpaceXService.GetLaunches",
            "SpaceXService.GetLaunch",
            "SpaceXService.GetRockets",
            "SpaceXService.GetRocket",
            "SpaceXService.GetCrew",
            "SpaceXService.GetStarlink",
            "SpaceXService.GetLaunchpads",
            "SpaceXService.GetCompanyInfo",
            "SpaceXService.GetUpcomingLaunches",
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
    def test_get_latest_launch(self, server):
        result = server._cli(["SpaceXService", "GetLatestLaunch"])
        assert "launch" in result
        assert result["launch"]["name"] == "Starlink Group 6-14"

    def test_get_launches(self, server):
        result = server._cli(["SpaceXService", "GetLaunches"])
        assert "launches" in result
        assert len(result["launches"]) == 2

    def test_get_launch(self, server):
        result = server._cli(
            ["SpaceXService", "GetLaunch", "-r", '{"id":"5eb87d46ffd86e000604b388"}']
        )
        assert "launch" in result
        assert result["launch"]["name"] == "Starlink Group 6-14"

    def test_get_rockets(self, server):
        result = server._cli(["SpaceXService", "GetRockets"])
        assert "rockets" in result
        assert result["rockets"][0]["name"] == "Falcon 9"

    def test_get_rocket(self, server):
        result = server._cli(
            ["SpaceXService", "GetRocket", "-r", '{"id":"5e9d0d95eda69973a809d1ec"}']
        )
        assert "rocket" in result
        assert result["rocket"]["name"] == "Falcon 9"

    def test_get_crew(self, server):
        result = server._cli(["SpaceXService", "GetCrew"])
        assert "crew" in result
        assert result["crew"][0]["name"] == "Robert Behnken"

    def test_get_starlink(self, server):
        result = server._cli(["SpaceXService", "GetStarlink"])
        assert "satellites" in result
        assert len(result["satellites"]) == 1

    def test_get_launchpads(self, server):
        result = server._cli(["SpaceXService", "GetLaunchpads"])
        assert "launchpads" in result
        assert result["launchpads"][0]["name"] == "KSC LC 39A"

    def test_get_company_info(self, server):
        result = server._cli(["SpaceXService", "GetCompanyInfo"])
        assert result.get("name") == "SpaceX"
        assert result.get("founder") == "Elon Musk"

    def test_get_upcoming_launches(self, server):
        result = server._cli(["SpaceXService", "GetUpcomingLaunches"])
        assert "launches" in result
        assert len(result["launches"]) == 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["SpaceXService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "SpaceXService" in result
        assert "GetLatestLaunch" in result

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

    def test_get_latest_launch(self):
        result = self._post("/spacex.v1.SpaceXService/GetLatestLaunch")
        assert "launch" in result

    def test_get_rockets(self):
        result = self._post("/spacex.v1.SpaceXService/GetRockets")
        assert "rockets" in result

    def test_get_company_info(self):
        result = self._post("/spacex.v1.SpaceXService/GetCompanyInfo")
        assert result.get("name") == "SpaceX" or result.get("name") == "SpaceX"

    def test_get_crew(self):
        result = self._post("/spacex.v1.SpaceXService/GetCrew")
        assert "crew" in result

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

from spacex_mcp.gen.spacex.v1 import spacex_pb2 as pb
from spacex_mcp.service import SpaceXService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/v4/launches/latest" in url:
        resp.json.return_value = {{
            "id": "5eb87d46ffd86e000604b388",
            "name": "Starlink Group 6-14",
            "date_utc": "2024-01-15T12:00:00.000Z",
            "date_unix": 1705320000,
            "success": True,
            "flight_number": 250,
            "rocket": "5e9d0d95eda69973a809d1ec",
            "details": "SpaceX launched 23 Starlink satellites.",
            "upcoming": False,
            "launchpad": "5e9e4502f509094188566f88",
            "payloads": [],
            "crew": [],
            "links": {{
                "patch": {{"small": "https://img/s.png", "large": "https://img/l.png"}},
                "webcast": "https://youtube.com/abc",
                "wikipedia": "https://en.wikipedia.org/wiki/Starlink",
                "article": "https://spacex.com/starlink",
            }},
        }}
    elif "/v4/rockets" in url:
        resp.json.return_value = [{{
            "id": "5e9d0d95eda69973a809d1ec",
            "name": "Falcon 9",
            "type": "rocket",
            "active": True,
            "stages": 2,
            "boosters": 0,
            "cost_per_launch": 50000000,
            "first_flight": "2010-06-04",
            "country": "United States",
            "company": "SpaceX",
            "height": {{"meters": 70}},
            "diameter": {{"meters": 3.7}},
            "mass": {{"kg": 549054}},
            "payload_weights": [{{"id": "leo", "kg": 22800}}, {{"id": "gto", "kg": 8300}}],
            "engines": {{"number": 9, "type": "merlin", "propellant_1": "LOX", "propellant_2": "RP-1"}},
            "description": "Falcon 9 is a reusable two-stage rocket.",
            "wikipedia": "https://en.wikipedia.org/wiki/Falcon_9",
            "success_rate_pct": 98,
        }}]
    elif "/v4/company" in url:
        resp.json.return_value = {{
            "name": "SpaceX",
            "founder": "Elon Musk",
            "founded": 2002,
            "employees": 12000,
            "vehicles": 4,
            "launch_sites": 3,
            "test_sites": 3,
            "ceo": "Elon Musk",
            "cto": "Elon Musk",
            "coo": "Gwynne Shotwell",
            "cto_propulsion": "Tom Mueller",
            "valuation": 74000000000,
            "summary": "SpaceX designs rockets.",
            "headquarters": {{"city": "Hawthorne", "state": "California"}},
            "links": {{"website": "https://spacex.com", "flickr": "", "twitter": "", "elon_twitter": ""}},
        }}
    elif "/v4/crew" in url:
        resp.json.return_value = [{{
            "id": "5ebf1b7323a9a60006e03a7b",
            "name": "Robert Behnken",
            "status": "active",
            "agency": "NASA",
            "image": "https://img/behnken.png",
            "wikipedia": "https://en.wikipedia.org/wiki/Behnken",
            "launches": [],
        }}]
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = SpaceXService.__new__(SpaceXService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-spacex", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-spacex"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "SpaceXService.GetLatestLaunch" in names
        assert "SpaceXService.GetRockets" in names
        assert "SpaceXService.GetCompanyInfo" in names

    def test_tool_call_get_latest_launch(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SpaceXService.GetLatestLaunch",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "launch" in result
        assert result["launch"]["name"] == "Starlink Group 6-14"

    def test_tool_call_get_rockets(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SpaceXService.GetRockets",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "rockets" in result
        assert result["rockets"][0]["name"] == "Falcon 9"

    def test_tool_call_get_company_info(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SpaceXService.GetCompanyInfo",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("name") == "SpaceX"

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
            # notification -- no id field
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
        server._cli(["SpaceXService", "GetCompanyInfo"])
        assert len(calls) == 1
        assert calls[0] == "/spacex.v1.SpaceXService/GetCompanyInfo"

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
        server._cli(["SpaceXService", "GetLatestLaunch"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

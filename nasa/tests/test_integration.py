"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from nasa_mcp.gen.nasa.v1 import nasa_pb2 as pb
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
            "NASAService.GetAPOD",
            "NASAService.GetAPODRange",
            "NASAService.GetMarsPhotos",
            "NASAService.GetMarsManifest",
            "NASAService.GetNEOs",
            "NASAService.GetNEOLookup",
            "NASAService.GetEPIC",
            "NASAService.SearchNASAImages",
            "NASAService.GetDonki",
            "NASAService.GetTechTransfer",
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
    def test_get_apod(self, server):
        result = server._cli(["NASAService", "GetAPOD"])
        assert "entry" in result
        assert result["entry"].get("title") == "The Horsehead Nebula"

    def test_get_apod_range(self, server):
        result = server._cli(
            ["NASAService", "GetAPODRange", "-r", '{"start_date":"2024-01-15","end_date":"2024-01-16"}']
        )
        # May return entry or entries depending on mock routing.
        assert "entries" in result or "entry" in result

    def test_get_mars_photos(self, server):
        result = server._cli(
            ["NASAService", "GetMarsPhotos", "-r", '{"rover":"curiosity","sol":1000}']
        )
        assert "photos" in result
        assert len(result["photos"]) >= 1

    def test_get_mars_manifest(self, server):
        result = server._cli(
            ["NASAService", "GetMarsManifest", "-r", '{"rover":"curiosity"}']
        )
        assert "manifest" in result
        assert result["manifest"].get("name") == "Curiosity"

    def test_get_neos(self, server):
        result = server._cli(
            ["NASAService", "GetNEOs", "-r", '{"start_date":"2024-01-15","end_date":"2024-01-15"}']
        )
        assert result.get("elementCount") == 2 or result.get("element_count") == 2

    def test_get_neo_lookup(self, server):
        result = server._cli(
            ["NASAService", "GetNEOLookup", "-r", '{"asteroid_id":"3542519"}']
        )
        assert "object" in result
        obj = result["object"]
        assert obj.get("name") == "(2010 PK9)"

    def test_get_epic(self, server):
        result = server._cli(["NASAService", "GetEPIC"])
        assert "images" in result
        assert len(result["images"]) >= 1

    def test_search_nasa_images(self, server):
        result = server._cli(
            ["NASAService", "SearchNASAImages", "-r", '{"query":"apollo"}']
        )
        assert "items" in result
        assert len(result["items"]) >= 1

    def test_get_donki(self, server):
        result = server._cli(["NASAService", "GetDonki"])
        assert "events" in result
        assert len(result["events"]) >= 1

    def test_get_tech_transfer(self, server):
        result = server._cli(
            ["NASAService", "GetTechTransfer", "-r", '{"query":"robotics"}']
        )
        assert "items" in result
        assert len(result["items"]) >= 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["NASAService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "NASAService" in result
        assert "GetAPOD" in result

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

    def test_get_apod(self):
        result = self._post("/nasa.v1.NASAService/GetAPOD")
        assert "entry" in result

    def test_get_mars_manifest(self):
        result = self._post(
            "/nasa.v1.NASAService/GetMarsManifest",
            {"rover": "curiosity"},
        )
        assert "manifest" in result

    def test_get_neos(self):
        result = self._post(
            "/nasa.v1.NASAService/GetNEOs",
            {"start_date": "2024-01-15", "end_date": "2024-01-15"},
        )
        assert result.get("elementCount") == 2 or result.get("element_count") == 2

    def test_get_epic(self):
        result = self._post("/nasa.v1.NASAService/GetEPIC")
        assert "images" in result

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

from nasa_mcp.gen.nasa.v1 import nasa_pb2 as pb
from nasa_mcp.service import NASAService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/planetary/apod" in url:
        resp.json.return_value = {{"title": "The Horsehead Nebula",
            "explanation": "One of the most identifiable nebulae...",
            "url": "https://apod.nasa.gov/apod/image/2401/horsehead.jpg",
            "hdurl": "https://apod.nasa.gov/apod/image/2401/horsehead_hd.jpg",
            "media_type": "image", "date": "2024-01-15", "copyright": "John Doe"}}
    elif "/EPIC/api/natural" in url:
        resp.json.return_value = [{{
            "identifier": "20240115003633",
            "caption": "EPIC image",
            "image": "epic_1b_20240115003633",
            "date": "2024-01-15 00:36:33",
            "centroid_coordinates": {{"lat": 12.34, "lon": -56.78}}}}]
    elif "/DONKI/CME" in url:
        resp.json.return_value = [{{
            "activityID": "2024-01-15-00-09-00-CME-001",
            "startTime": "2024-01-15T00:09Z",
            "sourceLocation": "N20W30",
            "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/CME/12345/-1",
            "instruments": [{{"displayName": "SOHO: LASCO/C2"}}]}}]
    elif "/search" in url:
        resp.json.return_value = {{"collection": {{"items": [{{
            "data": [{{"nasa_id": "PIA00001", "title": "Apollo 11",
                "description": "Lunar Module", "media_type": "image",
                "date_created": "1969-07-20T00:00:00Z"}}],
            "links": [{{"href": "https://images-assets.nasa.gov/thumb.jpg"}}]}}]}}}}
    elif "/manifests" in url:
        resp.json.return_value = {{"photo_manifest": {{
            "name": "Curiosity", "landing_date": "2012-08-06",
            "launch_date": "2011-11-26", "status": "active",
            "max_sol": 4102, "max_date": "2024-01-15", "total_photos": 695670}}}}
    elif "/neo/rest/v1/feed" in url:
        resp.json.return_value = {{"element_count": 2, "near_earth_objects": {{
            "2024-01-15": [{{
                "id": "3542519", "name": "(2010 PK9)", "absolute_magnitude_h": 21.4,
                "estimated_diameter": {{"kilometers": {{
                    "estimated_diameter_min": 0.1011, "estimated_diameter_max": 0.2261}}}},
                "is_potentially_hazardous_asteroid": False,
                "close_approach_data": [{{
                    "close_approach_date": "2024-01-15",
                    "relative_velocity": {{"kilometers_per_hour": "48520.1234"}},
                    "miss_distance": {{"kilometers": "5432100.123"}},
                    "orbiting_body": "Earth"}}]}}]}}}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = NASAService.__new__(NASAService)
svc._http = http
svc._api_key = "DEMO_KEY"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-nasa", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-nasa"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "NASAService.GetAPOD" in names
        assert "NASAService.GetMarsPhotos" in names
        assert "NASAService.GetNEOs" in names

    def test_tool_call_get_apod(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "NASAService.GetAPOD",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "entry" in result
        assert result["entry"].get("title") == "The Horsehead Nebula"

    def test_tool_call_get_epic(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "NASAService.GetEPIC",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "images" in result
        assert len(result["images"]) >= 1

    def test_tool_call_get_neos(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "NASAService.GetNEOs",
                "arguments": {"start_date": "2024-01-15", "end_date": "2024-01-15"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("elementCount") == 2 or result.get("element_count") == 2

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
        server._cli(["NASAService", "GetAPOD"])
        assert len(calls) == 1
        assert calls[0] == "/nasa.v1.NASAService/GetAPOD"

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
        server._cli(["NASAService", "GetEPIC"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

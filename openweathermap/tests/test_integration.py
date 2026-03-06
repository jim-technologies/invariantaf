"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from openweathermap_mcp.gen.openweathermap.v1 import openweathermap_pb2 as pb
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
            "OpenWeatherMapService.GetCurrentWeather",
            "OpenWeatherMapService.GetCurrentWeatherByCoords",
            "OpenWeatherMapService.GetForecast",
            "OpenWeatherMapService.GetAirQuality",
            "OpenWeatherMapService.GetUVIndex",
            "OpenWeatherMapService.GetGeocode",
            "OpenWeatherMapService.GetReverseGeocode",
            "OpenWeatherMapService.GetOneCall",
            "OpenWeatherMapService.GetHistoricalWeather",
            "OpenWeatherMapService.GetWeatherMap",
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
    def test_get_current_weather(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetCurrentWeather", "-r", '{"city":"London"}']
        )
        assert "weather" in result

    def test_get_current_weather_by_coords(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetCurrentWeatherByCoords", "-r", '{"lat":51.5074,"lon":-0.1278}']
        )
        assert "weather" in result

    def test_get_forecast(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetForecast", "-r", '{"city":"London"}']
        )
        assert "items" in result

    def test_get_air_quality(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetAirQuality", "-r", '{"lat":51.5074,"lon":-0.1278}']
        )
        assert "data" in result

    def test_get_uv_index(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetUVIndex", "-r", '{"lat":51.5074,"lon":-0.1278}']
        )
        assert "uvIndex" in result or "uv_index" in result

    def test_get_geocode(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetGeocode", "-r", '{"city":"London"}']
        )
        assert "locations" in result

    def test_get_reverse_geocode(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetReverseGeocode", "-r", '{"lat":51.5074,"lon":-0.1278}']
        )
        assert "locations" in result

    def test_get_one_call(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetOneCall", "-r", '{"lat":51.5074,"lon":-0.1278}']
        )
        assert "current" in result

    def test_get_historical_weather(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetHistoricalWeather", "-r", '{"lat":51.5074,"lon":-0.1278,"dt":1700020000}']
        )
        assert "data" in result

    def test_get_weather_map(self, server):
        result = server._cli(
            ["OpenWeatherMapService", "GetWeatherMap", "-r", '{"layer":"clouds_new","z":5,"x":15,"y":10}']
        )
        assert "url" in result
        assert "tile.openweathermap.org" in result["url"]

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OpenWeatherMapService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "OpenWeatherMapService" in result
        assert "GetCurrentWeather" in result

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

    def test_get_current_weather(self):
        result = self._post(
            "/openweathermap.v1.OpenWeatherMapService/GetCurrentWeather",
            {"city": "London"},
        )
        assert "weather" in result

    def test_get_forecast(self):
        result = self._post(
            "/openweathermap.v1.OpenWeatherMapService/GetForecast",
            {"city": "London"},
        )
        assert "items" in result

    def test_get_geocode(self):
        result = self._post(
            "/openweathermap.v1.OpenWeatherMapService/GetGeocode",
            {"city": "London"},
        )
        assert "locations" in result

    def test_get_weather_map(self):
        result = self._post(
            "/openweathermap.v1.OpenWeatherMapService/GetWeatherMap",
            {"layer": "clouds_new", "z": 5, "x": 15, "y": 10},
        )
        assert "url" in result

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

from openweathermap_mcp.gen.openweathermap.v1 import openweathermap_pb2 as pb
from openweathermap_mcp.service import OpenWeatherMapService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/data/2.5/weather" in url:
        resp.json.return_value = {{
            "coord": {{"lat": 51.5074, "lon": -0.1278}},
            "weather": [{{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}}],
            "main": {{"temp": 18.5, "feels_like": 17.2, "temp_min": 16.0, "temp_max": 20.0, "humidity": 65, "pressure": 1013}},
            "wind": {{"speed": 3.5, "deg": 220}},
            "clouds": {{"all": 10}},
            "visibility": 10000,
            "sys": {{"country": "GB", "sunrise": 1700000000, "sunset": 1700040000}},
            "name": "London",
            "dt": 1700020000,
        }}
    elif "/geo/1.0/direct" in url:
        resp.json.return_value = [
            {{"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB", "state": "England"}}
        ]
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = OpenWeatherMapService.__new__(OpenWeatherMapService)
svc._http = http
svc._api_key = "test-key"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-owm", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-owm"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "OpenWeatherMapService.GetCurrentWeather" in names
        assert "OpenWeatherMapService.GetForecast" in names
        assert "OpenWeatherMapService.GetWeatherMap" in names

    def test_tool_call_get_current_weather(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OpenWeatherMapService.GetCurrentWeather",
                "arguments": {"city": "London"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "weather" in result

    def test_tool_call_get_geocode(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OpenWeatherMapService.GetGeocode",
                "arguments": {"city": "London"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "locations" in result

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
        server._cli(["OpenWeatherMapService", "GetGeocode", "-r", '{"city":"London"}'])
        assert len(calls) == 1
        assert calls[0] == "/openweathermap.v1.OpenWeatherMapService/GetGeocode"

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
        server._cli(["OpenWeatherMapService", "GetGeocode", "-r", '{"city":"London"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as pb
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
            "PackageRegistryService.SearchNPM",
            "PackageRegistryService.GetNPMPackage",
            "PackageRegistryService.GetNPMDownloads",
            "PackageRegistryService.GetNPMVersions",
            "PackageRegistryService.GetNPMDependencies",
            "PackageRegistryService.GetPyPIPackage",
            "PackageRegistryService.GetPyPIVersion",
            "PackageRegistryService.GetPyPIReleases",
            "PackageRegistryService.GetPyPIDownloads",
            "PackageRegistryService.GetPyPIDependencies",
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
    def test_search_npm(self, server):
        result = server._cli(
            ["PackageRegistryService", "SearchNPM", "-r", '{"query":"react"}']
        )
        assert "results" in result
        assert len(result["results"]) >= 1

    def test_get_npm_package(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetNPMPackage", "-r", '{"name":"express"}']
        )
        assert result["name"] == "express"
        assert result.get("latestVersion") == "4.18.2" or result.get("latest_version") == "4.18.2"

    def test_get_npm_downloads(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetNPMDownloads", "-r", '{"name":"express"}']
        )
        # int64 fields are serialized as strings in proto3 JSON.
        assert int(result.get("downloads", 0)) == 25000000

    def test_get_npm_versions(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetNPMVersions", "-r", '{"name":"express"}']
        )
        assert "versions" in result
        assert len(result["versions"]) == 2

    def test_get_npm_dependencies(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetNPMDependencies", "-r", '{"name":"express"}']
        )
        assert "dependencies" in result
        assert len(result["dependencies"]) >= 1

    def test_get_pypi_package(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetPyPIPackage", "-r", '{"name":"requests"}']
        )
        assert result["name"] == "requests"
        assert result["version"] == "2.31.0"

    def test_get_pypi_version(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetPyPIVersion", "-r", '{"name":"requests","version":"2.30.0"}']
        )
        assert result["version"] == "2.30.0"

    def test_get_pypi_releases(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetPyPIReleases", "-r", '{"name":"requests"}']
        )
        assert "releases" in result
        assert len(result["releases"]) == 2

    def test_get_pypi_downloads(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetPyPIDownloads", "-r", '{"name":"requests"}']
        )
        # int64 fields are serialized as strings in proto3 JSON.
        val = result.get("lastDay") or result.get("last_day")
        assert int(val) == 5000000

    def test_get_pypi_dependencies(self, server):
        result = server._cli(
            ["PackageRegistryService", "GetPyPIDependencies", "-r", '{"name":"requests"}']
        )
        requires = result.get("requiresDist") or result.get("requires_dist")
        assert len(requires) == 4

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["PackageRegistryService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "PackageRegistryService" in result
        assert "SearchNPM" in result

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

    def test_search_npm(self):
        result = self._post(
            "/packageregistry.v1.PackageRegistryService/SearchNPM",
            {"query": "react"},
        )
        assert "results" in result

    def test_get_npm_package(self):
        result = self._post(
            "/packageregistry.v1.PackageRegistryService/GetNPMPackage",
            {"name": "express"},
        )
        assert result["name"] == "express"

    def test_get_pypi_package(self):
        result = self._post(
            "/packageregistry.v1.PackageRegistryService/GetPyPIPackage",
            {"name": "requests"},
        )
        assert result["name"] == "requests"

    def test_get_pypi_downloads(self):
        result = self._post(
            "/packageregistry.v1.PackageRegistryService/GetPyPIDownloads",
            {"name": "requests"},
        )
        # int64 fields are serialized as strings in proto3 JSON.
        val = result.get("lastDay") or result.get("last_day")
        assert int(val) == 5000000

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

from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as pb
from packageregistry_mcp.service import PackageRegistryService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/-/v1/search" in url:
        resp.json.return_value = {{"total": 1, "objects": [
            {{"package": {{"name": "react", "version": "18.2.0",
                "description": "UI lib", "keywords": ["react"],
                "date": "2022-06-14", "publisher": {{"username": "gaearon"}},
                "links": {{"homepage": "https://react.dev", "repository": ""}}
            }}}}
        ]}}
    elif "/downloads/point/last-week/" in url:
        resp.json.return_value = {{"package": "express", "downloads": 25000000,
            "start": "2025-01-08", "end": "2025-01-14"}}
    elif "/pypi/requests/json" in url:
        resp.json.return_value = {{"info": {{"name": "requests", "version": "2.31.0",
            "summary": "HTTP lib", "description": "", "author": "KR",
            "author_email": "", "license": "Apache-2.0", "home_page": "",
            "project_urls": {{}}, "requires_python": ">=3.7",
            "requires_dist": ["urllib3"], "classifiers": []}},
            "releases": {{"2.31.0": [{{"upload_time": "2023-05-22"}}]}}}}
    elif "/api/packages/" in url:
        resp.json.return_value = {{"package": "requests",
            "data": {{"last_day": 5000000, "last_week": 35000000, "last_month": 150000000}}}}
    elif url.endswith("/express") or "/express" in url:
        resp.json.return_value = {{"name": "express", "description": "Web framework",
            "dist-tags": {{"latest": "4.18.2"}}, "license": "MIT",
            "homepage": "", "repository": {{}},
            "maintainers": [], "time": {{"created": "", "modified": ""}},
            "versions": {{"4.18.2": {{"dependencies": {{"accepts": "~1.3.8"}},
                "devDependencies": {{}}, "peerDependencies": {{}}}}}}}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = PackageRegistryService.__new__(PackageRegistryService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-pkgreg", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-pkgreg"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "PackageRegistryService.SearchNPM" in names
        assert "PackageRegistryService.GetNPMPackage" in names
        assert "PackageRegistryService.GetPyPIPackage" in names

    def test_tool_call_search_npm(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PackageRegistryService.SearchNPM",
                "arguments": {"query": "react"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "results" in result
        assert result["results"][0].get("name") == "react"

    def test_tool_call_get_pypi_package(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PackageRegistryService.GetPyPIPackage",
                "arguments": {"name": "requests"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["name"] == "requests"

    def test_tool_call_get_pypi_downloads(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PackageRegistryService.GetPyPIDownloads",
                "arguments": {"name": "requests"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        # int64 fields are serialized as strings in proto3 JSON.
        val = result.get("lastDay") or result.get("last_day")
        assert int(val) == 5000000

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
        server._cli(["PackageRegistryService", "GetNPMDownloads", "-r", '{"name":"express"}'])
        assert len(calls) == 1
        assert calls[0] == "/packageregistry.v1.PackageRegistryService/GetNPMDownloads"

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
        server._cli(["PackageRegistryService", "SearchNPM", "-r", '{"query":"react"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

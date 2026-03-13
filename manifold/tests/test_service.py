"""Unit tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "ManifoldService.ListMarkets",
    "ManifoldService.GetMarket",
    "ManifoldService.GetMarketBySlug",
    "ManifoldService.SearchMarkets",
    "ManifoldService.GetMarketPositions",
    "ManifoldService.GetUser",
    "ManifoldService.GetUserByUsername",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 7

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_list_markets(self, server):
        result = server._cli(["ManifoldService", "ListMarkets", "-r", '{"limit": 2}'])
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == "mkt-abc123"

    def test_list_markets_with_sort(self, server):
        result = server._cli(
            [
                "ManifoldService",
                "ListMarkets",
                "-r",
                '{"limit": 1, "sort": "created-time", "order": "desc"}',
            ]
        )
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1

    def test_get_market(self, server):
        result = server._cli(
            ["ManifoldService", "GetMarket", "-r", '{"market_id": "mkt-abc123"}']
        )
        assert result["data"]["id"] == "mkt-abc123"
        assert result["data"]["question"] == "Will AI pass the Turing test by 2030?"
        assert result["data"]["mechanism"] == "cpmm-1"
        assert result["data"]["outcome_type"] == "BINARY"
        assert result["data"]["probability"] == 0.65

    def test_get_market_pool(self, server):
        result = server._cli(
            ["ManifoldService", "GetMarket", "-r", '{"market_id": "mkt-abc123"}']
        )
        pool = result["data"]["pool"]
        assert pool["YES"] == 1200.0
        assert pool["NO"] == 800.0

    def test_get_market_by_slug(self, server):
        result = server._cli(
            ["ManifoldService", "GetMarketBySlug", "-r", '{"slug": "will-ai-pass-turing-test"}']
        )
        assert result["data"]["id"] == "mkt-abc123"
        # is_resolved defaults to false, so protobuf omits it from JSON output
        assert result["data"].get("is_resolved", False) is False

    def test_search_markets(self, server):
        result = server._cli(
            [
                "ManifoldService",
                "SearchMarkets",
                "-r",
                '{"term": "AI", "filter": "open", "limit": 5}',
            ]
        )
        assert isinstance(result["data"], list)
        assert result["data"][0]["id"] == "mkt-abc123"

    def test_get_market_positions(self, server):
        result = server._cli(
            [
                "ManifoldService",
                "GetMarketPositions",
                "-r",
                '{"market_id": "mkt-abc123", "order": "shares", "top": 10}',
            ]
        )
        assert isinstance(result["data"], list)
        assert result["data"][0]["has_yes_shares"] is True
        assert result["data"][0]["yes_shares"] == 150.0
        assert result["data"][0]["profit"] == 42.5
        assert result["data"][0]["user_name"] == "bettor99"

    def test_get_user(self, server):
        result = server._cli(
            ["ManifoldService", "GetUser", "-r", '{"user_id": "user-abc"}']
        )
        assert result["data"]["id"] == "user-abc"
        assert result["data"]["name"] == "Alice Forecaster"
        assert result["data"]["username"] == "aliceforecaster"
        assert result["data"]["balance"] == 1500.0

    def test_get_user_by_username(self, server):
        result = server._cli(
            [
                "ManifoldService",
                "GetUserByUsername",
                "-r",
                '{"username": "aliceforecaster"}',
            ]
        )
        assert result["data"]["id"] == "user-abc"
        assert result["data"]["profit"] == 500.0

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["ManifoldService", "DoesNotExist"])


_HTTP_CASES = [
    ("/manifold.v1.ManifoldService/ListMarkets", {"limit": 2}),
    ("/manifold.v1.ManifoldService/GetMarket", {"market_id": "mkt-abc123"}),
    ("/manifold.v1.ManifoldService/GetMarketBySlug", {"slug": "test-slug"}),
    ("/manifold.v1.ManifoldService/SearchMarkets", {"term": "AI", "limit": 5}),
    (
        "/manifold.v1.ManifoldService/GetMarketPositions",
        {"market_id": "mkt-abc123", "top": 10},
    ),
    ("/manifold.v1.ManifoldService/GetUser", {"user_id": "user-abc"}),
    ("/manifold.v1.ManifoldService/GetUserByUsername", {"username": "aliceforecaster"}),
]


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path: str, body: dict | None = None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    @pytest.mark.parametrize(("path", "body"), _HTTP_CASES)
    def test_all_routes(self, path: str, body: dict):
        result = self._post(path, body)
        assert "data" in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


class TestSchemaIntegrity:
    def test_proto_no_struct_or_value_fields(self):
        from gen.manifold.v1 import manifold_pb2

        disallowed = {"google.protobuf.Struct", "google.protobuf.Value", "google.protobuf.Any"}

        file_desc = manifold_pb2.DESCRIPTOR
        for message in file_desc.message_types_by_name.values():
            for field in message.fields:
                msg_type = field.message_type
                if msg_type is None:
                    continue
                assert msg_type.full_name not in disallowed, (
                    f"{message.full_name}.{field.name} still uses untyped payload {msg_type.full_name}"
                )

    def test_rpc_method_count_is_stable(self):
        from gen.manifold.v1 import manifold_pb2

        total = 0
        for service in manifold_pb2.DESCRIPTOR.services_by_name.values():
            total += len(service.methods)
        assert total == 7

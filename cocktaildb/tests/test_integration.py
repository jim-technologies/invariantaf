"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as pb
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
            "CocktailDBService.SearchCocktails",
            "CocktailDBService.GetCocktail",
            "CocktailDBService.GetRandomCocktail",
            "CocktailDBService.FilterByIngredient",
            "CocktailDBService.FilterByCategory",
            "CocktailDBService.FilterByGlass",
            "CocktailDBService.ListCategories",
            "CocktailDBService.ListGlasses",
            "CocktailDBService.ListIngredients",
            "CocktailDBService.SearchIngredient",
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
    def test_search_cocktails(self, server):
        result = server._cli(
            ["CocktailDBService", "SearchCocktails", "-r", '{"name":"margarita"}']
        )
        assert "cocktails" in result
        assert len(result["cocktails"]) >= 1

    def test_get_cocktail(self, server):
        result = server._cli(
            ["CocktailDBService", "GetCocktail", "-r", '{"id":"11007"}']
        )
        assert "cocktail" in result
        assert result["cocktail"]["name"] == "Margarita"

    def test_get_random_cocktail(self, server):
        result = server._cli(["CocktailDBService", "GetRandomCocktail"])
        assert "cocktail" in result
        assert result["cocktail"]["name"] == "A1"

    def test_filter_by_ingredient(self, server):
        result = server._cli(
            ["CocktailDBService", "FilterByIngredient", "-r", '{"ingredient":"Tequila"}']
        )
        assert "cocktails" in result
        assert len(result["cocktails"]) >= 1

    def test_filter_by_category(self, server):
        result = server._cli(
            ["CocktailDBService", "FilterByCategory", "-r", '{"category":"Cocktail"}']
        )
        assert "cocktails" in result
        assert len(result["cocktails"]) >= 1

    def test_filter_by_glass(self, server):
        result = server._cli(
            ["CocktailDBService", "FilterByGlass", "-r", '{"glass":"Cocktail glass"}']
        )
        assert "cocktails" in result

    def test_list_categories(self, server):
        result = server._cli(["CocktailDBService", "ListCategories"])
        assert "categories" in result
        assert len(result["categories"]) == 3

    def test_list_glasses(self, server):
        result = server._cli(["CocktailDBService", "ListGlasses"])
        assert "glasses" in result
        assert len(result["glasses"]) == 3

    def test_list_ingredients(self, server):
        result = server._cli(["CocktailDBService", "ListIngredients"])
        assert "ingredients" in result
        assert len(result["ingredients"]) == 3

    def test_search_ingredient(self, server):
        result = server._cli(
            ["CocktailDBService", "SearchIngredient", "-r", '{"name":"Vodka"}']
        )
        assert "ingredient" in result
        assert result["ingredient"]["name"] == "Vodka"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["CocktailDBService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "CocktailDBService" in result
        assert "SearchCocktails" in result

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

    def test_search_cocktails(self):
        result = self._post(
            "/cocktaildb.v1.CocktailDBService/SearchCocktails",
            {"name": "margarita"},
        )
        assert "cocktails" in result

    def test_get_random_cocktail(self):
        result = self._post("/cocktaildb.v1.CocktailDBService/GetRandomCocktail")
        assert "cocktail" in result

    def test_list_categories(self):
        result = self._post("/cocktaildb.v1.CocktailDBService/ListCategories")
        assert "categories" in result

    def test_search_ingredient(self):
        result = self._post(
            "/cocktaildb.v1.CocktailDBService/SearchIngredient",
            {"name": "Vodka"},
        )
        assert "ingredient" in result

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

from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as pb
from cocktaildb_mcp.service import CocktailDBService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if params:
        query = "&".join(f"{{k}}={{v}}" for k, v in params.items())
        full_url = f"{{url}}?{{query}}"
    else:
        full_url = url
    if "search.php" in full_url and "s=" in full_url:
        resp.json.return_value = {{"drinks": [{{
            "idDrink": "11007", "strDrink": "Margarita",
            "strCategory": "Ordinary Drink", "strGlass": "Cocktail glass",
            "strInstructions": "Shake and serve.", "strDrinkThumb": "https://img/m.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Tequila", "strIngredient2": "Lime juice",
            "strIngredient3": None, "strIngredient4": None, "strIngredient5": None,
            "strIngredient6": None, "strIngredient7": None, "strIngredient8": None,
            "strIngredient9": None, "strIngredient10": None, "strIngredient11": None,
            "strIngredient12": None, "strIngredient13": None, "strIngredient14": None,
            "strIngredient15": None,
            "strMeasure1": "1 oz", "strMeasure2": "1/2 oz",
            "strMeasure3": None, "strMeasure4": None, "strMeasure5": None,
            "strMeasure6": None, "strMeasure7": None, "strMeasure8": None,
            "strMeasure9": None, "strMeasure10": None, "strMeasure11": None,
            "strMeasure12": None, "strMeasure13": None, "strMeasure14": None,
            "strMeasure15": None,
        }}]}}
    elif "random.php" in full_url:
        resp.json.return_value = {{"drinks": [{{
            "idDrink": "17222", "strDrink": "A1",
            "strCategory": "Cocktail", "strGlass": "Cocktail glass",
            "strInstructions": "Pour and serve.", "strDrinkThumb": "https://img/a1.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Gin", "strIngredient2": None, "strIngredient3": None,
            "strIngredient4": None, "strIngredient5": None, "strIngredient6": None,
            "strIngredient7": None, "strIngredient8": None, "strIngredient9": None,
            "strIngredient10": None, "strIngredient11": None, "strIngredient12": None,
            "strIngredient13": None, "strIngredient14": None, "strIngredient15": None,
            "strMeasure1": "2 oz", "strMeasure2": None, "strMeasure3": None,
            "strMeasure4": None, "strMeasure5": None, "strMeasure6": None,
            "strMeasure7": None, "strMeasure8": None, "strMeasure9": None,
            "strMeasure10": None, "strMeasure11": None, "strMeasure12": None,
            "strMeasure13": None, "strMeasure14": None, "strMeasure15": None,
        }}]}}
    elif "list.php" in full_url and "c=" in full_url:
        resp.json.return_value = {{"drinks": [
            {{"strCategory": "Cocktail"}}, {{"strCategory": "Shot"}}
        ]}}
    elif "search.php" in full_url and "i=" in full_url:
        resp.json.return_value = {{"ingredients": [{{
            "idIngredient": "1", "strIngredient": "Vodka",
            "strDescription": "Distilled spirit.", "strType": "Vodka",
            "strAlcohol": "Yes", "strABV": "40"
        }}]}}
    else:
        resp.json.return_value = {{"drinks": None}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = CocktailDBService.__new__(CocktailDBService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-cocktaildb", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-cocktaildb"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "CocktailDBService.SearchCocktails" in names
        assert "CocktailDBService.GetRandomCocktail" in names
        assert "CocktailDBService.ListCategories" in names

    def test_tool_call_search_cocktails(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CocktailDBService.SearchCocktails",
                "arguments": {"name": "margarita"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "cocktails" in result
        assert result["cocktails"][0]["name"] == "Margarita"

    def test_tool_call_get_random_cocktail(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CocktailDBService.GetRandomCocktail",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "cocktail" in result
        assert result["cocktail"]["name"] == "A1"

    def test_tool_call_list_categories(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "CocktailDBService.ListCategories",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "categories" in result
        assert "Cocktail" in result["categories"]

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
        server._cli(["CocktailDBService", "ListCategories"])
        assert len(calls) == 1
        assert calls[0] == "/cocktaildb.v1.CocktailDBService/ListCategories"

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
        server._cli(["CocktailDBService", "GetRandomCocktail"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as pb
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
            "PokeAPIService.GetPokemon",
            "PokeAPIService.GetPokemonSpecies",
            "PokeAPIService.GetAbility",
            "PokeAPIService.GetMove",
            "PokeAPIService.GetType",
            "PokeAPIService.GetEvolutionChain",
            "PokeAPIService.GetGeneration",
            "PokeAPIService.GetItem",
            "PokeAPIService.GetNature",
            "PokeAPIService.ListPokemon",
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
    def test_get_pokemon(self, server):
        result = server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id":"pikachu"}']
        )
        assert result["name"] == "pikachu"
        assert result["id"] == 25

    def test_get_pokemon_species(self, server):
        result = server._cli(
            ["PokeAPIService", "GetPokemonSpecies", "-r", '{"name_or_id":"pikachu"}']
        )
        assert result["name"] == "pikachu"
        # Proto JSON omits false booleans (default value), so check not True.
        assert result.get("isLegendary") is not True and result.get("is_legendary") is not True

    def test_get_ability(self, server):
        result = server._cli(
            ["PokeAPIService", "GetAbility", "-r", '{"name_or_id":"static"}']
        )
        assert result["name"] == "static"

    def test_get_move(self, server):
        result = server._cli(
            ["PokeAPIService", "GetMove", "-r", '{"name_or_id":"thunderbolt"}']
        )
        assert result["name"] == "thunderbolt"
        assert result.get("power") == 90

    def test_get_type(self, server):
        result = server._cli(
            ["PokeAPIService", "GetType", "-r", '{"name_or_id":"electric"}']
        )
        assert result["name"] == "electric"

    def test_get_evolution_chain(self, server):
        result = server._cli(
            ["PokeAPIService", "GetEvolutionChain", "-r", '{"id":10}']
        )
        chain = result.get("chain", {})
        species = chain.get("speciesName") or chain.get("species_name")
        assert species == "pichu"

    def test_get_generation(self, server):
        result = server._cli(
            ["PokeAPIService", "GetGeneration", "-r", '{"name_or_id":"generation-i"}']
        )
        assert result["name"] == "generation-i"

    def test_get_item(self, server):
        result = server._cli(
            ["PokeAPIService", "GetItem", "-r", '{"name_or_id":"potion"}']
        )
        assert result["name"] == "potion"
        assert result.get("cost") == 200

    def test_get_nature(self, server):
        result = server._cli(
            ["PokeAPIService", "GetNature", "-r", '{"name_or_id":"adamant"}']
        )
        assert result["name"] == "adamant"

    def test_list_pokemon(self, server):
        result = server._cli(["PokeAPIService", "ListPokemon"])
        assert "results" in result
        assert len(result["results"]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["PokeAPIService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "PokeAPIService" in result
        assert "GetPokemon" in result

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

    def test_get_pokemon(self):
        result = self._post(
            "/pokeapi.v1.PokeAPIService/GetPokemon",
            {"name_or_id": "pikachu"},
        )
        assert result["name"] == "pikachu"

    def test_get_move(self):
        result = self._post(
            "/pokeapi.v1.PokeAPIService/GetMove",
            {"name_or_id": "thunderbolt"},
        )
        assert result["name"] == "thunderbolt"

    def test_list_pokemon(self):
        result = self._post("/pokeapi.v1.PokeAPIService/ListPokemon")
        assert "results" in result

    def test_get_nature(self):
        result = self._post(
            "/pokeapi.v1.PokeAPIService/GetNature",
            {"name_or_id": "adamant"},
        )
        assert result["name"] == "adamant"

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

from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as pb
from pokeapi_mcp.service import PokeAPIService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/pokemon-species/" in url:
        resp.json.return_value = {{
            "id": 25, "name": "pikachu",
            "flavor_text_entries": [{{"flavor_text": "Electric mouse.", "language": {{"name": "en"}}}}],
            "genera": [{{"genus": "Mouse Pokemon", "language": {{"name": "en"}}}}],
            "generation": {{"name": "generation-i"}}, "habitat": {{"name": "forest"}},
            "is_legendary": False, "is_mythical": False,
            "evolution_chain": {{"url": "https://pokeapi.co/api/v2/evolution-chain/10/"}},
            "capture_rate": 190, "base_happiness": 70,
            "color": {{"name": "yellow"}}, "shape": {{"name": "quadruped"}}}}
    elif "/pokemon/" in url or url.endswith("/pokemon/pikachu"):
        resp.json.return_value = {{
            "id": 25, "name": "pikachu",
            "types": [{{"type": {{"name": "electric"}}, "slot": 1}}],
            "stats": [{{"stat": {{"name": "hp"}}, "base_stat": 35, "effort": 0}}],
            "abilities": [{{"ability": {{"name": "static"}}, "is_hidden": False, "slot": 1}}],
            "height": 4, "weight": 60,
            "sprites": {{"front_default": "https://sprites/25.png", "front_shiny": "", "back_default": "", "back_shiny": ""}},
            "base_experience": 112, "order": 35}}
    elif url.endswith("/pokemon"):
        resp.json.return_value = {{
            "count": 1302, "next": "https://pokeapi.co/api/v2/pokemon?offset=20&limit=20",
            "previous": None,
            "results": [{{"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"}}]}}
    elif "/nature/" in url:
        resp.json.return_value = {{
            "id": 2, "name": "adamant",
            "increased_stat": {{"name": "attack"}}, "decreased_stat": {{"name": "special-attack"}}}}
    elif "/move/" in url:
        resp.json.return_value = {{
            "id": 85, "name": "thunderbolt", "power": 90, "accuracy": 100, "pp": 15,
            "type": {{"name": "electric"}}, "damage_class": {{"name": "special"}},
            "effect_entries": [{{"effect": "Paralyze chance.", "short_effect": "May paralyze.", "language": {{"name": "en"}}}}],
            "priority": 0}}
    elif "/type/" in url:
        resp.json.return_value = {{
            "id": 13, "name": "electric",
            "damage_relations": {{
                "double_damage_to": [{{"name": "water"}}], "half_damage_to": [{{"name": "grass"}}],
                "no_damage_to": [{{"name": "ground"}}], "double_damage_from": [{{"name": "ground"}}],
                "half_damage_from": [{{"name": "steel"}}], "no_damage_from": []}},
            "pokemon": [{{"pokemon": {{"name": "pikachu"}}}}],
            "moves": [{{"name": "thunderbolt"}}]}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = PokeAPIService.__new__(PokeAPIService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-pokeapi", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-pokeapi"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "PokeAPIService.GetPokemon" in names
        assert "PokeAPIService.GetMove" in names
        assert "PokeAPIService.ListPokemon" in names

    def test_tool_call_get_pokemon(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PokeAPIService.GetPokemon",
                "arguments": {"name_or_id": "pikachu"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert result["name"] == "pikachu"
        assert result["id"] == 25

    def test_tool_call_list_pokemon(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PokeAPIService.ListPokemon",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "results" in result
        assert result["count"] == 1302

    def test_tool_call_get_nature(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "PokeAPIService.GetNature",
                "arguments": {"name_or_id": "adamant"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result["name"] == "adamant"

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
        server._cli(["PokeAPIService", "GetNature", "-r", '{"name_or_id":"adamant"}'])
        assert len(calls) == 1
        assert calls[0] == "/pokeapi.v1.PokeAPIService/GetNature"

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
        server._cli(["PokeAPIService", "ListPokemon"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]

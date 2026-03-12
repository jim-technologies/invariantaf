"""Live integration tests for PokeAPI -- hits the real API.

Run with:
    POKEAPI_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) PokeAPI v2 endpoints.
No API key or authentication is required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("POKEAPI_RUN_LIVE_TESTS") != "1",
    reason="Set POKEAPI_RUN_LIVE_TESTS=1 to run live PokeAPI tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as _pb  # noqa: F401
    from pokeapi_mcp.service import PokeAPIService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-pokeapi-live", version="0.0.1"
    )
    svc = PokeAPIService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Pokemon ---


class TestLiveGetPokemon:
    def test_get_pokemon_by_name(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "pikachu"}']
        )
        assert result["name"] == "pikachu"
        assert result["id"] == 25

    def test_get_pokemon_has_types(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "pikachu"}']
        )
        assert "types" in result
        types = result["types"]
        assert len(types) > 0
        type_names = [t["name"] for t in types]
        assert "electric" in type_names

    def test_get_pokemon_has_stats(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "pikachu"}']
        )
        assert "stats" in result
        stats = result["stats"]
        assert len(stats) == 6  # HP, Atk, Def, SpA, SpD, Spe
        stat_names = [s["name"] for s in stats]
        assert "hp" in stat_names
        assert "attack" in stat_names

    def test_get_pokemon_has_abilities(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "pikachu"}']
        )
        assert "abilities" in result
        abilities = result["abilities"]
        assert len(abilities) > 0
        ability_names = [a["name"] for a in abilities]
        assert "static" in ability_names

    def test_get_pokemon_has_sprites(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "pikachu"}']
        )
        assert "sprites" in result
        sprites = result["sprites"]
        front = sprites.get("frontDefault") or sprites.get("front_default")
        assert front
        assert front.startswith("http")

    def test_get_pokemon_by_id(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemon", "-r", '{"name_or_id": "25"}']
        )
        assert result["name"] == "pikachu"
        assert result["id"] == 25


# --- Pokemon species ---


class TestLiveGetPokemonSpecies:
    def test_get_pokemon_species(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemonSpecies", "-r", '{"name_or_id": "pikachu"}']
        )
        assert result["name"] == "pikachu"
        assert result["id"] == 25

    def test_get_pokemon_species_has_flavor_text(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemonSpecies", "-r", '{"name_or_id": "pikachu"}']
        )
        flavor = result.get("flavorText") or result.get("flavor_text")
        assert flavor
        assert len(flavor) > 10

    def test_get_pokemon_species_has_generation(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemonSpecies", "-r", '{"name_or_id": "pikachu"}']
        )
        assert result.get("generation") == "generation-i"

    def test_get_pokemon_species_legendary(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetPokemonSpecies", "-r", '{"name_or_id": "mewtwo"}']
        )
        assert result["name"] == "mewtwo"
        is_legendary = result.get("isLegendary") or result.get("is_legendary")
        assert is_legendary is True


# --- Ability ---


class TestLiveGetAbility:
    def test_get_ability(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetAbility", "-r", '{"name_or_id": "static"}']
        )
        assert result["name"] == "static"
        assert result.get("id") > 0

    def test_get_ability_has_effect(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetAbility", "-r", '{"name_or_id": "overgrow"}']
        )
        assert result["name"] == "overgrow"
        effect = result.get("effect") or result.get("shortEffect") or result.get("short_effect")
        assert effect
        assert len(effect) > 10

    def test_get_ability_has_pokemon(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetAbility", "-r", '{"name_or_id": "static"}']
        )
        assert "pokemon" in result
        pokemon = result["pokemon"]
        assert len(pokemon) > 0
        names = [p["name"] for p in pokemon]
        assert "pikachu" in names


# --- Move ---


class TestLiveGetMove:
    def test_get_move(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetMove", "-r", '{"name_or_id": "thunderbolt"}']
        )
        assert result["name"] == "thunderbolt"
        assert result.get("power") == 90
        assert result.get("accuracy") == 100
        assert result.get("pp") == 15

    def test_get_move_has_type(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetMove", "-r", '{"name_or_id": "thunderbolt"}']
        )
        assert result.get("type") == "electric"
        damage_class = result.get("damageClass") or result.get("damage_class")
        assert damage_class == "special"


# --- Type ---


class TestLiveGetType:
    def test_get_type(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetType", "-r", '{"name_or_id": "electric"}']
        )
        assert result["name"] == "electric"
        assert result.get("id") > 0

    def test_get_type_has_damage_relations(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetType", "-r", '{"name_or_id": "fire"}']
        )
        dr = result.get("damageRelations") or result.get("damage_relations")
        assert dr is not None
        ddt = dr.get("doubleDamageTo") or dr.get("double_damage_to")
        assert isinstance(ddt, list)
        assert len(ddt) > 0
        # Fire is super effective against grass
        assert "grass" in ddt

    def test_get_type_has_pokemon(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetType", "-r", '{"name_or_id": "electric"}']
        )
        assert "pokemon" in result
        pokemon = result["pokemon"]
        assert isinstance(pokemon, list)
        assert len(pokemon) > 0
        assert "pikachu" in pokemon


# --- Evolution chain ---


class TestLiveGetEvolutionChain:
    def test_get_evolution_chain(self, live_server):
        # Chain 10 is the pichu -> pikachu -> raichu chain
        result = live_server._cli(
            ["PokeAPIService", "GetEvolutionChain", "-r", '{"id": 10}']
        )
        assert result.get("id") == 10
        chain = result.get("chain")
        assert chain is not None
        species = chain.get("speciesName") or chain.get("species_name")
        assert species == "pichu"

    def test_evolution_chain_has_evolves_to(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetEvolutionChain", "-r", '{"id": 10}']
        )
        chain = result["chain"]
        evolves = chain.get("evolvesTo") or chain.get("evolves_to")
        assert isinstance(evolves, list)
        assert len(evolves) > 0
        # pichu -> pikachu
        next_species = evolves[0].get("speciesName") or evolves[0].get("species_name")
        assert next_species == "pikachu"


# --- Generation ---


class TestLiveGetGeneration:
    def test_get_generation(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetGeneration", "-r", '{"name_or_id": "generation-i"}']
        )
        assert result["name"] == "generation-i"
        assert result.get("id") == 1
        main_region = result.get("mainRegion") or result.get("main_region")
        assert main_region == "kanto"

    def test_get_generation_has_pokemon(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetGeneration", "-r", '{"name_or_id": "1"}']
        )
        species = result.get("pokemonSpecies") or result.get("pokemon_species")
        assert isinstance(species, list)
        assert len(species) > 100  # Gen 1 has 151 Pokemon
        assert "bulbasaur" in species


# --- Item ---


class TestLiveGetItem:
    def test_get_item(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetItem", "-r", '{"name_or_id": "potion"}']
        )
        assert result["name"] == "potion"
        assert result.get("cost") == 200

    def test_get_item_has_effect(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetItem", "-r", '{"name_or_id": "master-ball"}']
        )
        assert result["name"] == "master-ball"
        effect = result.get("effect") or result.get("shortEffect") or result.get("short_effect")
        assert effect
        assert len(effect) > 10


# --- Nature ---


class TestLiveGetNature:
    def test_get_nature(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "GetNature", "-r", '{"name_or_id": "adamant"}']
        )
        assert result["name"] == "adamant"
        increased = result.get("increasedStat") or result.get("increased_stat")
        decreased = result.get("decreasedStat") or result.get("decreased_stat")
        assert increased == "attack"
        assert decreased == "special-attack"


# --- List Pokemon ---


class TestLiveListPokemon:
    def test_list_pokemon(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "ListPokemon", "-r", '{"limit": 5}']
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) == 5
        assert results[0].get("name") == "bulbasaur"

    def test_list_pokemon_pagination(self, live_server):
        result = live_server._cli(
            ["PokeAPIService", "ListPokemon", "-r", '{"limit": 3, "offset": 3}']
        )
        results = result["results"]
        assert len(results) == 3
        # Offset 3 should start with charmander (4th Pokemon)
        assert results[0].get("name") == "charmander"

    def test_list_pokemon_has_count(self, live_server):
        result = live_server._cli(["PokeAPIService", "ListPokemon"])
        assert result.get("count") > 1000  # There are 1000+ Pokemon

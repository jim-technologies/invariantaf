"""Shared fixtures for PokeAPI MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pokeapi_mcp.gen.pokeapi.v1 import pokeapi_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real PokeAPI v2 return shapes
# ---------------------------------------------------------------------------

FAKE_POKEMON = {
    "id": 25,
    "name": "pikachu",
    "types": [
        {"type": {"name": "electric"}, "slot": 1},
    ],
    "stats": [
        {"stat": {"name": "hp"}, "base_stat": 35, "effort": 0},
        {"stat": {"name": "attack"}, "base_stat": 55, "effort": 0},
        {"stat": {"name": "defense"}, "base_stat": 40, "effort": 0},
        {"stat": {"name": "special-attack"}, "base_stat": 50, "effort": 0},
        {"stat": {"name": "special-defense"}, "base_stat": 50, "effort": 0},
        {"stat": {"name": "speed"}, "base_stat": 90, "effort": 2},
    ],
    "abilities": [
        {"ability": {"name": "static"}, "is_hidden": False, "slot": 1},
        {"ability": {"name": "lightning-rod"}, "is_hidden": True, "slot": 3},
    ],
    "height": 4,
    "weight": 60,
    "sprites": {
        "front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png",
        "front_shiny": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/25.png",
        "back_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/25.png",
        "back_shiny": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/shiny/25.png",
    },
    "base_experience": 112,
    "order": 35,
}

FAKE_POKEMON_SPECIES = {
    "id": 25,
    "name": "pikachu",
    "flavor_text_entries": [
        {"flavor_text": "When several of\nthese Pokemon gather, their\nelectricity could\fbuild and cause\nlightning storms.", "language": {"name": "en"}},
        {"flavor_text": "Quand plusieurs de ces Pokemon se reunissent...", "language": {"name": "fr"}},
    ],
    "genera": [
        {"genus": "Mouse Pokemon", "language": {"name": "en"}},
        {"genus": "Souris", "language": {"name": "fr"}},
    ],
    "generation": {"name": "generation-i"},
    "habitat": {"name": "forest"},
    "is_legendary": False,
    "is_mythical": False,
    "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/10/"},
    "capture_rate": 190,
    "base_happiness": 70,
    "color": {"name": "yellow"},
    "shape": {"name": "quadruped"},
}

FAKE_ABILITY = {
    "id": 9,
    "name": "static",
    "effect_entries": [
        {
            "effect": "Has a 30% chance of paralyzing attacking Pokemon on contact.",
            "short_effect": "Has a 30% chance of paralyzing attacking Pokemon on contact.",
            "language": {"name": "en"},
        },
    ],
    "pokemon": [
        {"pokemon": {"name": "pikachu"}, "is_hidden": False},
        {"pokemon": {"name": "electabuzz"}, "is_hidden": False},
        {"pokemon": {"name": "emolga"}, "is_hidden": False},
    ],
}

FAKE_MOVE = {
    "id": 85,
    "name": "thunderbolt",
    "power": 90,
    "accuracy": 100,
    "pp": 15,
    "type": {"name": "electric"},
    "damage_class": {"name": "special"},
    "effect_entries": [
        {
            "effect": "Has a $effect_chance% chance of paralyzing the target.",
            "short_effect": "Has a $effect_chance% chance to paralyze the target.",
            "language": {"name": "en"},
        },
    ],
    "priority": 0,
}

FAKE_TYPE = {
    "id": 13,
    "name": "electric",
    "damage_relations": {
        "double_damage_to": [{"name": "water"}, {"name": "flying"}],
        "half_damage_to": [{"name": "electric"}, {"name": "grass"}, {"name": "dragon"}],
        "no_damage_to": [{"name": "ground"}],
        "double_damage_from": [{"name": "ground"}],
        "half_damage_from": [{"name": "electric"}, {"name": "flying"}, {"name": "steel"}],
        "no_damage_from": [],
    },
    "pokemon": [
        {"pokemon": {"name": "pikachu"}},
        {"pokemon": {"name": "raichu"}},
        {"pokemon": {"name": "electabuzz"}},
    ],
    "moves": [
        {"name": "thunderbolt"},
        {"name": "thunder"},
        {"name": "thunder-wave"},
    ],
}

FAKE_EVOLUTION_CHAIN = {
    "id": 10,
    "chain": {
        "species": {"name": "pichu"},
        "evolution_details": [],
        "evolves_to": [
            {
                "species": {"name": "pikachu"},
                "evolution_details": [
                    {"trigger": {"name": "level-up"}, "min_level": None, "item": None},
                ],
                "evolves_to": [
                    {
                        "species": {"name": "raichu"},
                        "evolution_details": [
                            {"trigger": {"name": "use-item"}, "min_level": None, "item": {"name": "thunder-stone"}},
                        ],
                        "evolves_to": [],
                    },
                ],
            },
        ],
    },
}

FAKE_GENERATION = {
    "id": 1,
    "name": "generation-i",
    "main_region": {"name": "kanto"},
    "pokemon_species": [
        {"name": "bulbasaur"},
        {"name": "charmander"},
        {"name": "squirtle"},
    ],
    "moves": [
        {"name": "pound"},
        {"name": "karate-chop"},
    ],
    "types": [
        {"name": "normal"},
        {"name": "fire"},
        {"name": "water"},
    ],
}

FAKE_ITEM = {
    "id": 17,
    "name": "potion",
    "effect_entries": [
        {
            "effect": "Used on a Pokemon. It restores the Pokemon's HP by 20 points.",
            "short_effect": "Restores 20 HP.",
            "language": {"name": "en"},
        },
    ],
    "category": {"name": "medicine"},
    "cost": 200,
    "sprites": {"default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/potion.png"},
}

FAKE_NATURE = {
    "id": 2,
    "name": "adamant",
    "increased_stat": {"name": "attack"},
    "decreased_stat": {"name": "special-attack"},
}

FAKE_LIST_POKEMON = {
    "count": 1302,
    "next": "https://pokeapi.co/api/v2/pokemon?offset=20&limit=20",
    "previous": None,
    "results": [
        {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"},
        {"name": "ivysaur", "url": "https://pokeapi.co/api/v2/pokemon/2/"},
        {"name": "venusaur", "url": "https://pokeapi.co/api/v2/pokemon/3/"},
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/pokemon/pikachu": FAKE_POKEMON,
        "/pokemon/25": FAKE_POKEMON,
        "/pokemon-species/pikachu": FAKE_POKEMON_SPECIES,
        "/pokemon-species/25": FAKE_POKEMON_SPECIES,
        "/ability/static": FAKE_ABILITY,
        "/ability/9": FAKE_ABILITY,
        "/move/thunderbolt": FAKE_MOVE,
        "/move/85": FAKE_MOVE,
        "/type/electric": FAKE_TYPE,
        "/type/13": FAKE_TYPE,
        "/evolution-chain/10": FAKE_EVOLUTION_CHAIN,
        "/generation/generation-i": FAKE_GENERATION,
        "/generation/1": FAKE_GENERATION,
        "/item/potion": FAKE_ITEM,
        "/item/17": FAKE_ITEM,
        "/nature/adamant": FAKE_NATURE,
        "/nature/2": FAKE_NATURE,
        "/pokemon": FAKE_LIST_POKEMON,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """PokeAPIService with mocked HTTP client."""
    from pokeapi_mcp.service import PokeAPIService

    svc = PokeAPIService.__new__(PokeAPIService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked PokeAPIService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-pokeapi", version="0.0.1")
    srv.register(service)
    return srv

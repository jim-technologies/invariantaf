"""Live integration tests for TheCocktailDB API -- hits the real API.

Run with:
    COCKTAILDB_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) TheCocktailDB API endpoints.
No API key or authentication is required (uses the free "1" API key).
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
    os.getenv("COCKTAILDB_RUN_LIVE_TESTS") != "1",
    reason="Set COCKTAILDB_RUN_LIVE_TESTS=1 to run live CocktailDB API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as _pb  # noqa: F401
    from cocktaildb_mcp.service import CocktailDBService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-cocktaildb-live", version="0.0.1"
    )
    svc = CocktailDBService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def first_cocktail(live_server):
    """Search for a well-known cocktail to get its ID."""
    result = live_server._cli(
        ["CocktailDBService", "SearchCocktails", "-r", '{"name": "margarita"}']
    )
    cocktails = result.get("cocktails", [])
    assert cocktails, "expected at least one cocktail for 'margarita'"
    return cocktails[0]


@pytest.fixture(scope="module")
def categories(live_server):
    """Fetch categories once for filter tests."""
    result = live_server._cli(["CocktailDBService", "ListCategories"])
    cats = result.get("categories", [])
    assert cats, "expected at least one category"
    return cats


@pytest.fixture(scope="module")
def glasses(live_server):
    """Fetch glass types once for filter tests."""
    result = live_server._cli(["CocktailDBService", "ListGlasses"])
    glass_list = result.get("glasses", [])
    assert glass_list, "expected at least one glass type"
    return glass_list


# --- Search ---


class TestLiveSearch:
    def test_search_cocktails(self, live_server):
        result = live_server._cli(
            ["CocktailDBService", "SearchCocktails", "-r", '{"name": "margarita"}']
        )
        assert "cocktails" in result
        cocktails = result["cocktails"]
        assert isinstance(cocktails, list)
        assert len(cocktails) > 0
        c = cocktails[0]
        assert "name" in c
        assert "margarita" in c["name"].lower()

    def test_search_returns_ingredients(self, live_server):
        result = live_server._cli(
            ["CocktailDBService", "SearchCocktails", "-r", '{"name": "margarita"}']
        )
        cocktails = result["cocktails"]
        assert len(cocktails) > 0
        c = cocktails[0]
        assert "ingredients" in c
        assert len(c["ingredients"]) > 0
        ing = c["ingredients"][0]
        assert "name" in ing


# --- Get by ID ---


class TestLiveGetCocktail:
    def test_get_cocktail_by_id(self, live_server, first_cocktail):
        cocktail_id = first_cocktail["id"]
        result = live_server._cli(
            ["CocktailDBService", "GetCocktail", "-r", json.dumps({"id": cocktail_id})]
        )
        assert "cocktail" in result
        cocktail = result["cocktail"]
        assert cocktail["id"] == cocktail_id
        assert cocktail.get("name")
        assert cocktail.get("instructions")

    def test_get_cocktail_has_full_recipe(self, live_server, first_cocktail):
        cocktail_id = first_cocktail["id"]
        result = live_server._cli(
            ["CocktailDBService", "GetCocktail", "-r", json.dumps({"id": cocktail_id})]
        )
        cocktail = result["cocktail"]
        assert cocktail.get("category")
        assert cocktail.get("glass")
        assert cocktail.get("ingredients")
        assert len(cocktail["ingredients"]) > 0


# --- Random ---


class TestLiveRandom:
    def test_get_random_cocktail(self, live_server):
        result = live_server._cli(["CocktailDBService", "GetRandomCocktail"])
        assert "cocktail" in result
        cocktail = result["cocktail"]
        assert cocktail.get("id")
        assert cocktail.get("name")
        assert cocktail.get("instructions")
        assert cocktail.get("ingredients")


# --- Filter by ingredient ---


class TestLiveFilterByIngredient:
    def test_filter_by_ingredient(self, live_server):
        result = live_server._cli(
            ["CocktailDBService", "FilterByIngredient", "-r", '{"ingredient": "Vodka"}']
        )
        assert "cocktails" in result
        cocktails = result["cocktails"]
        assert isinstance(cocktails, list)
        assert len(cocktails) > 0
        c = cocktails[0]
        assert "id" in c
        assert "name" in c


# --- Filter by category ---


class TestLiveFilterByCategory:
    def test_filter_by_category(self, live_server, categories):
        category = categories[0]
        result = live_server._cli(
            ["CocktailDBService", "FilterByCategory", "-r", json.dumps({"category": category})]
        )
        assert "cocktails" in result
        cocktails = result["cocktails"]
        assert isinstance(cocktails, list)
        assert len(cocktails) > 0


# --- Filter by glass ---


class TestLiveFilterByGlass:
    def test_filter_by_glass(self, live_server, glasses):
        glass = glasses[0]
        result = live_server._cli(
            ["CocktailDBService", "FilterByGlass", "-r", json.dumps({"glass": glass})]
        )
        assert "cocktails" in result
        cocktails = result["cocktails"]
        assert isinstance(cocktails, list)
        assert len(cocktails) > 0


# --- List endpoints ---


class TestLiveLists:
    def test_list_categories(self, live_server):
        result = live_server._cli(["CocktailDBService", "ListCategories"])
        assert "categories" in result
        categories = result["categories"]
        assert isinstance(categories, list)
        assert len(categories) > 3
        assert "Cocktail" in categories or "Ordinary Drink" in categories

    def test_list_glasses(self, live_server):
        result = live_server._cli(["CocktailDBService", "ListGlasses"])
        assert "glasses" in result
        glasses = result["glasses"]
        assert isinstance(glasses, list)
        assert len(glasses) > 3

    def test_list_ingredients(self, live_server):
        result = live_server._cli(["CocktailDBService", "ListIngredients"])
        assert "ingredients" in result
        ingredients = result["ingredients"]
        assert isinstance(ingredients, list)
        assert len(ingredients) > 10


# --- Search ingredient ---


class TestLiveSearchIngredient:
    def test_search_ingredient(self, live_server):
        result = live_server._cli(
            ["CocktailDBService", "SearchIngredient", "-r", '{"name": "Vodka"}']
        )
        assert "ingredient" in result
        ingredient = result["ingredient"]
        assert ingredient.get("name") == "Vodka"
        assert ingredient.get("id")
        assert ingredient.get("description")

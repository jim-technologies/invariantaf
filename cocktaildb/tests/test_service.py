"""Unit tests — every CocktailDBService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as pb
from tests.conftest import (
    FAKE_FILTER_BY_CATEGORY,
    FAKE_FILTER_BY_GLASS,
    FAKE_FILTER_BY_INGREDIENT,
    FAKE_LIST_CATEGORIES,
    FAKE_LIST_GLASSES,
    FAKE_LIST_INGREDIENTS,
    FAKE_LOOKUP,
    FAKE_RANDOM,
    FAKE_SEARCH_COCKTAILS,
    FAKE_SEARCH_INGREDIENT,
)


class TestSearchCocktails:
    def test_returns_cocktails(self, service):
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="margarita"))
        assert len(resp.cocktails) == 2

    def test_first_cocktail_fields(self, service):
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="margarita"))
        c = resp.cocktails[0]
        assert c.id == "11007"
        assert c.name == "Margarita"
        assert c.category == "Ordinary Drink"
        assert c.glass == "Cocktail glass"
        assert c.alcoholic == "Alcoholic"

    def test_ingredients_parsed(self, service):
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="margarita"))
        c = resp.cocktails[0]
        assert len(c.ingredients) == 4
        assert c.ingredients[0].name == "Tequila"
        assert c.ingredients[0].measure == "1 1/2 oz"
        assert c.ingredients[1].name == "Triple sec"
        assert c.ingredients[2].name == "Lime juice"
        assert c.ingredients[3].name == "Salt"

    def test_null_ingredients_skipped(self, service):
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="margarita"))
        c = resp.cocktails[0]
        # Only 4 non-null ingredients, not 15
        assert len(c.ingredients) == 4

    def test_second_cocktail(self, service):
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="margarita"))
        c = resp.cocktails[1]
        assert c.id == "11118"
        assert c.name == "Blue Margarita"

    def test_empty_search(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"drinks": None})
        )
        resp = service.SearchCocktails(pb.SearchCocktailsRequest(name="zzzznonexistent"))
        assert len(resp.cocktails) == 0


class TestGetCocktail:
    def test_returns_cocktail(self, service):
        resp = service.GetCocktail(pb.GetCocktailRequest(id="11007"))
        assert resp.cocktail.id == "11007"
        assert resp.cocktail.name == "Margarita"

    def test_cocktail_has_instructions(self, service):
        resp = service.GetCocktail(pb.GetCocktailRequest(id="11007"))
        assert "rim" in resp.cocktail.instructions.lower()

    def test_cocktail_has_image(self, service):
        resp = service.GetCocktail(pb.GetCocktailRequest(id="11007"))
        assert resp.cocktail.image.startswith("https://")

    def test_cocktail_ingredients(self, service):
        resp = service.GetCocktail(pb.GetCocktailRequest(id="11007"))
        assert len(resp.cocktail.ingredients) == 4
        names = [i.name for i in resp.cocktail.ingredients]
        assert "Tequila" in names
        assert "Triple sec" in names

    def test_not_found(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"drinks": None})
        )
        resp = service.GetCocktail(pb.GetCocktailRequest(id="99999999"))
        assert not resp.HasField("cocktail")


class TestGetRandomCocktail:
    def test_returns_cocktail(self, service):
        resp = service.GetRandomCocktail(pb.GetRandomCocktailRequest())
        assert resp.cocktail.id == "17222"
        assert resp.cocktail.name == "A1"

    def test_has_ingredients(self, service):
        resp = service.GetRandomCocktail(pb.GetRandomCocktailRequest())
        assert len(resp.cocktail.ingredients) == 4
        assert resp.cocktail.ingredients[0].name == "Gin"

    def test_has_category(self, service):
        resp = service.GetRandomCocktail(pb.GetRandomCocktailRequest())
        assert resp.cocktail.category == "Cocktail"


class TestFilterByIngredient:
    def test_returns_summaries(self, service):
        resp = service.FilterByIngredient(pb.FilterByIngredientRequest(ingredient="Tequila"))
        assert len(resp.cocktails) == 2

    def test_summary_fields(self, service):
        resp = service.FilterByIngredient(pb.FilterByIngredientRequest(ingredient="Tequila"))
        assert resp.cocktails[0].id == "11007"
        assert resp.cocktails[0].name == "Margarita"
        assert resp.cocktails[0].image.startswith("https://")

    def test_second_result(self, service):
        resp = service.FilterByIngredient(pb.FilterByIngredientRequest(ingredient="Tequila"))
        assert resp.cocktails[1].id == "11403"
        assert resp.cocktails[1].name == "Tequila Sunrise"


class TestFilterByCategory:
    def test_returns_summaries(self, service):
        resp = service.FilterByCategory(pb.FilterByCategoryRequest(category="Cocktail"))
        assert len(resp.cocktails) == 2

    def test_summary_fields(self, service):
        resp = service.FilterByCategory(pb.FilterByCategoryRequest(category="Cocktail"))
        assert resp.cocktails[0].id == "17222"
        assert resp.cocktails[0].name == "A1"


class TestFilterByGlass:
    def test_returns_summaries(self, service):
        resp = service.FilterByGlass(pb.FilterByGlassRequest(glass="Cocktail glass"))
        assert len(resp.cocktails) == 1

    def test_summary_fields(self, service):
        resp = service.FilterByGlass(pb.FilterByGlassRequest(glass="Cocktail glass"))
        assert resp.cocktails[0].id == "11007"
        assert resp.cocktails[0].name == "Margarita"


class TestListCategories:
    def test_returns_categories(self, service):
        resp = service.ListCategories(pb.ListCategoriesRequest())
        assert len(resp.categories) == 3
        assert "Ordinary Drink" in resp.categories
        assert "Cocktail" in resp.categories
        assert "Shot" in resp.categories


class TestListGlasses:
    def test_returns_glasses(self, service):
        resp = service.ListGlasses(pb.ListGlassesRequest())
        assert len(resp.glasses) == 3
        assert "Cocktail glass" in resp.glasses
        assert "Highball glass" in resp.glasses
        assert "Old-fashioned glass" in resp.glasses


class TestListIngredients:
    def test_returns_ingredients(self, service):
        resp = service.ListIngredients(pb.ListIngredientsRequest())
        assert len(resp.ingredients) == 3
        assert "Light rum" in resp.ingredients
        assert "Applejack" in resp.ingredients
        assert "Gin" in resp.ingredients


class TestSearchIngredient:
    def test_returns_ingredient(self, service):
        resp = service.SearchIngredient(pb.SearchIngredientRequest(name="Vodka"))
        assert resp.ingredient.id == "1"
        assert resp.ingredient.name == "Vodka"

    def test_ingredient_description(self, service):
        resp = service.SearchIngredient(pb.SearchIngredientRequest(name="Vodka"))
        assert "distilled" in resp.ingredient.description.lower()

    def test_ingredient_type(self, service):
        resp = service.SearchIngredient(pb.SearchIngredientRequest(name="Vodka"))
        assert resp.ingredient.type == "Vodka"

    def test_ingredient_alcohol_info(self, service):
        resp = service.SearchIngredient(pb.SearchIngredientRequest(name="Vodka"))
        assert resp.ingredient.is_alcoholic is True
        assert resp.ingredient.abv == "40"

    def test_not_found(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"ingredients": None})
        )
        resp = service.SearchIngredient(pb.SearchIngredientRequest(name="zzzzz"))
        assert not resp.HasField("ingredient")

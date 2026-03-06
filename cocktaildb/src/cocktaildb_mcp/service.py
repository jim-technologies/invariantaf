"""CocktailDBService — wraps TheCocktailDB free API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as pb

_BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"


class CocktailDBService:
    """Implements CocktailDBService RPCs via the free TheCocktailDB API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _parse_cocktail(self, raw: dict) -> pb.Cocktail:
        """Parse a TheCocktailDB drink dict into a Cocktail proto."""
        ingredients = []
        for i in range(1, 16):
            ing = raw.get(f"strIngredient{i}")
            measure = raw.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredients.append(pb.Ingredient(
                    name=ing.strip(),
                    measure=(measure or "").strip(),
                ))
        return pb.Cocktail(
            id=raw.get("idDrink", ""),
            name=raw.get("strDrink", ""),
            category=raw.get("strCategory", ""),
            glass=raw.get("strGlass", ""),
            instructions=raw.get("strInstructions", "") or "",
            image=raw.get("strDrinkThumb", "") or "",
            alcoholic=raw.get("strAlcoholic", "") or "",
            ingredients=ingredients,
        )

    def _parse_summary(self, raw: dict) -> pb.CocktailSummary:
        """Parse a TheCocktailDB filter result into a CocktailSummary proto."""
        return pb.CocktailSummary(
            id=raw.get("idDrink", ""),
            name=raw.get("strDrink", ""),
            image=raw.get("strDrinkThumb", "") or "",
        )

    def SearchCocktails(self, request: Any, context: Any = None) -> pb.SearchCocktailsResponse:
        raw = self._get("/search.php", params={"s": request.name})
        resp = pb.SearchCocktailsResponse()
        for drink in raw.get("drinks") or []:
            resp.cocktails.append(self._parse_cocktail(drink))
        return resp

    def GetCocktail(self, request: Any, context: Any = None) -> pb.GetCocktailResponse:
        raw = self._get("/lookup.php", params={"i": request.id})
        drinks = raw.get("drinks") or []
        if not drinks:
            return pb.GetCocktailResponse()
        return pb.GetCocktailResponse(cocktail=self._parse_cocktail(drinks[0]))

    def GetRandomCocktail(self, request: Any, context: Any = None) -> pb.GetRandomCocktailResponse:
        raw = self._get("/random.php")
        drinks = raw.get("drinks") or []
        if not drinks:
            return pb.GetRandomCocktailResponse()
        return pb.GetRandomCocktailResponse(cocktail=self._parse_cocktail(drinks[0]))

    def FilterByIngredient(self, request: Any, context: Any = None) -> pb.FilterByIngredientResponse:
        raw = self._get("/filter.php", params={"i": request.ingredient})
        resp = pb.FilterByIngredientResponse()
        for drink in raw.get("drinks") or []:
            resp.cocktails.append(self._parse_summary(drink))
        return resp

    def FilterByCategory(self, request: Any, context: Any = None) -> pb.FilterByCategoryResponse:
        raw = self._get("/filter.php", params={"c": request.category})
        resp = pb.FilterByCategoryResponse()
        for drink in raw.get("drinks") or []:
            resp.cocktails.append(self._parse_summary(drink))
        return resp

    def FilterByGlass(self, request: Any, context: Any = None) -> pb.FilterByGlassResponse:
        raw = self._get("/filter.php", params={"g": request.glass})
        resp = pb.FilterByGlassResponse()
        for drink in raw.get("drinks") or []:
            resp.cocktails.append(self._parse_summary(drink))
        return resp

    def ListCategories(self, request: Any, context: Any = None) -> pb.ListCategoriesResponse:
        raw = self._get("/list.php", params={"c": "list"})
        resp = pb.ListCategoriesResponse()
        for item in raw.get("drinks") or []:
            name = item.get("strCategory", "")
            if name:
                resp.categories.append(name)
        return resp

    def ListGlasses(self, request: Any, context: Any = None) -> pb.ListGlassesResponse:
        raw = self._get("/list.php", params={"g": "list"})
        resp = pb.ListGlassesResponse()
        for item in raw.get("drinks") or []:
            name = item.get("strGlass", "")
            if name:
                resp.glasses.append(name)
        return resp

    def ListIngredients(self, request: Any, context: Any = None) -> pb.ListIngredientsResponse:
        raw = self._get("/list.php", params={"i": "list"})
        resp = pb.ListIngredientsResponse()
        for item in raw.get("drinks") or []:
            name = item.get("strIngredient1", "")
            if name:
                resp.ingredients.append(name)
        return resp

    def SearchIngredient(self, request: Any, context: Any = None) -> pb.SearchIngredientResponse:
        raw = self._get("/search.php", params={"i": request.name})
        items = raw.get("ingredients") or []
        if not items:
            return pb.SearchIngredientResponse()
        ing = items[0]
        return pb.SearchIngredientResponse(
            ingredient=pb.IngredientDetail(
                id=str(ing.get("idIngredient", "")),
                name=ing.get("strIngredient", ""),
                description=ing.get("strDescription", "") or "",
                type=ing.get("strType", "") or "",
                is_alcoholic=ing.get("strAlcohol", "No") == "Yes",
                abv=ing.get("strABV", "") or "",
            )
        )

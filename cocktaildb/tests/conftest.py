"""Shared fixtures for CocktailDB MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cocktaildb_mcp.gen.cocktaildb.v1 import cocktaildb_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real TheCocktailDB API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH_COCKTAILS = {
    "drinks": [
        {
            "idDrink": "11007",
            "strDrink": "Margarita",
            "strCategory": "Ordinary Drink",
            "strGlass": "Cocktail glass",
            "strInstructions": "Rub the rim of the glass with the lime slice to make the salt stick to it. Take care to moisten only the outer rim and sprinkle the salt on it. The게 게lass has to be completely dry. Shake the other ingredients with ice, then carefully pour into the glass.",
            "strDrinkThumb": "https://www.thecocktaildb.com/images/media/drink/5noda61702672620.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Tequila",
            "strIngredient2": "Triple sec",
            "strIngredient3": "Lime juice",
            "strIngredient4": "Salt",
            "strIngredient5": None,
            "strIngredient6": None,
            "strIngredient7": None,
            "strIngredient8": None,
            "strIngredient9": None,
            "strIngredient10": None,
            "strIngredient11": None,
            "strIngredient12": None,
            "strIngredient13": None,
            "strIngredient14": None,
            "strIngredient15": None,
            "strMeasure1": "1 1/2 oz ",
            "strMeasure2": "1/2 oz ",
            "strMeasure3": "1 oz ",
            "strMeasure4": None,
            "strMeasure5": None,
            "strMeasure6": None,
            "strMeasure7": None,
            "strMeasure8": None,
            "strMeasure9": None,
            "strMeasure10": None,
            "strMeasure11": None,
            "strMeasure12": None,
            "strMeasure13": None,
            "strMeasure14": None,
            "strMeasure15": None,
        },
        {
            "idDrink": "11118",
            "strDrink": "Blue Margarita",
            "strCategory": "Ordinary Drink",
            "strGlass": "Cocktail glass",
            "strInstructions": "Rub rim of cocktail glass with lime juice. Dip rim in coarse salt. Shake tequila, blue curacao, and lime juice with ice, strain into the salt-rimmed glass, and serve.",
            "strDrinkThumb": "https://www.thecocktaildb.com/images/media/drink/bry4qh1582751040.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Tequila",
            "strIngredient2": "Blue Curacao",
            "strIngredient3": "Lime juice",
            "strIngredient4": "Salt",
            "strIngredient5": None,
            "strIngredient6": None,
            "strIngredient7": None,
            "strIngredient8": None,
            "strIngredient9": None,
            "strIngredient10": None,
            "strIngredient11": None,
            "strIngredient12": None,
            "strIngredient13": None,
            "strIngredient14": None,
            "strIngredient15": None,
            "strMeasure1": "1 1/2 oz ",
            "strMeasure2": "1 oz ",
            "strMeasure3": "1 oz ",
            "strMeasure4": "Coarse ",
            "strMeasure5": None,
            "strMeasure6": None,
            "strMeasure7": None,
            "strMeasure8": None,
            "strMeasure9": None,
            "strMeasure10": None,
            "strMeasure11": None,
            "strMeasure12": None,
            "strMeasure13": None,
            "strMeasure14": None,
            "strMeasure15": None,
        },
    ],
}

FAKE_LOOKUP = {
    "drinks": [
        {
            "idDrink": "11007",
            "strDrink": "Margarita",
            "strCategory": "Ordinary Drink",
            "strGlass": "Cocktail glass",
            "strInstructions": "Rub the rim of the glass with the lime slice.",
            "strDrinkThumb": "https://www.thecocktaildb.com/images/media/drink/5noda61702672620.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Tequila",
            "strIngredient2": "Triple sec",
            "strIngredient3": "Lime juice",
            "strIngredient4": "Salt",
            "strIngredient5": None,
            "strIngredient6": None,
            "strIngredient7": None,
            "strIngredient8": None,
            "strIngredient9": None,
            "strIngredient10": None,
            "strIngredient11": None,
            "strIngredient12": None,
            "strIngredient13": None,
            "strIngredient14": None,
            "strIngredient15": None,
            "strMeasure1": "1 1/2 oz ",
            "strMeasure2": "1/2 oz ",
            "strMeasure3": "1 oz ",
            "strMeasure4": None,
            "strMeasure5": None,
            "strMeasure6": None,
            "strMeasure7": None,
            "strMeasure8": None,
            "strMeasure9": None,
            "strMeasure10": None,
            "strMeasure11": None,
            "strMeasure12": None,
            "strMeasure13": None,
            "strMeasure14": None,
            "strMeasure15": None,
        },
    ],
}

FAKE_RANDOM = {
    "drinks": [
        {
            "idDrink": "17222",
            "strDrink": "A1",
            "strCategory": "Cocktail",
            "strGlass": "Cocktail glass",
            "strInstructions": "Pour all ingredients into a cocktail shaker, mix and serve over ice into a chilled glass.",
            "strDrinkThumb": "https://www.thecocktaildb.com/images/media/drink/2x8thr1504816928.jpg",
            "strAlcoholic": "Alcoholic",
            "strIngredient1": "Gin",
            "strIngredient2": "Grand Marnier",
            "strIngredient3": "Lemon Juice",
            "strIngredient4": "Grenadine",
            "strIngredient5": None,
            "strIngredient6": None,
            "strIngredient7": None,
            "strIngredient8": None,
            "strIngredient9": None,
            "strIngredient10": None,
            "strIngredient11": None,
            "strIngredient12": None,
            "strIngredient13": None,
            "strIngredient14": None,
            "strIngredient15": None,
            "strMeasure1": "1 3/4 shot ",
            "strMeasure2": "1 Shot ",
            "strMeasure3": "1/4 Shot",
            "strMeasure4": "1/8 Shot",
            "strMeasure5": None,
            "strMeasure6": None,
            "strMeasure7": None,
            "strMeasure8": None,
            "strMeasure9": None,
            "strMeasure10": None,
            "strMeasure11": None,
            "strMeasure12": None,
            "strMeasure13": None,
            "strMeasure14": None,
            "strMeasure15": None,
        },
    ],
}

FAKE_FILTER_BY_INGREDIENT = {
    "drinks": [
        {"strDrink": "Margarita", "strDrinkThumb": "https://img/margarita.jpg", "idDrink": "11007"},
        {"strDrink": "Tequila Sunrise", "strDrinkThumb": "https://img/sunrise.jpg", "idDrink": "11403"},
    ],
}

FAKE_FILTER_BY_CATEGORY = {
    "drinks": [
        {"strDrink": "A1", "strDrinkThumb": "https://img/a1.jpg", "idDrink": "17222"},
        {"strDrink": "ABC", "strDrinkThumb": "https://img/abc.jpg", "idDrink": "13501"},
    ],
}

FAKE_FILTER_BY_GLASS = {
    "drinks": [
        {"strDrink": "Margarita", "strDrinkThumb": "https://img/margarita.jpg", "idDrink": "11007"},
    ],
}

FAKE_LIST_CATEGORIES = {
    "drinks": [
        {"strCategory": "Ordinary Drink"},
        {"strCategory": "Cocktail"},
        {"strCategory": "Shot"},
    ],
}

FAKE_LIST_GLASSES = {
    "drinks": [
        {"strGlass": "Cocktail glass"},
        {"strGlass": "Highball glass"},
        {"strGlass": "Old-fashioned glass"},
    ],
}

FAKE_LIST_INGREDIENTS = {
    "drinks": [
        {"strIngredient1": "Light rum"},
        {"strIngredient1": "Applejack"},
        {"strIngredient1": "Gin"},
    ],
}

FAKE_SEARCH_INGREDIENT = {
    "ingredients": [
        {
            "idIngredient": "1",
            "strIngredient": "Vodka",
            "strDescription": "Vodka is a distilled beverage composed primarily of water and ethanol.",
            "strType": "Vodka",
            "strAlcohol": "Yes",
            "strABV": "40",
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        # Route by query param patterns
        "search.php?s=": FAKE_SEARCH_COCKTAILS,
        "lookup.php?i=": FAKE_LOOKUP,
        "random.php": FAKE_RANDOM,
        "filter.php?i=": FAKE_FILTER_BY_INGREDIENT,
        "filter.php?c=": FAKE_FILTER_BY_CATEGORY,
        "filter.php?g=": FAKE_FILTER_BY_GLASS,
        "list.php?c=": FAKE_LIST_CATEGORIES,
        "list.php?g=": FAKE_LIST_GLASSES,
        "list.php?i=": FAKE_LIST_INGREDIENTS,
        "search.php?i=": FAKE_SEARCH_INGREDIENT,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Build the full URL with params for matching.
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{url}?{query}"
        else:
            full_url = url

        # Match on URL patterns.
        for pattern, data in defaults.items():
            if pattern in full_url:
                resp.json.return_value = data
                return resp
        resp.json.return_value = {"drinks": None}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """CocktailDBService with mocked HTTP client."""
    from cocktaildb_mcp.service import CocktailDBService

    svc = CocktailDBService.__new__(CocktailDBService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked CocktailDBService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-cocktaildb", version="0.0.1")
    srv.register(service)
    return srv

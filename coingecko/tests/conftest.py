"""Shared fixtures for CoinGecko MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from coingecko_mcp.gen.coingecko.v1 import coingecko_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real CoinGecko API return shapes
# ---------------------------------------------------------------------------

FAKE_SIMPLE_PRICE = {
    "bitcoin": {
        "usd": 67000.0,
        "usd_market_cap": 1320000000000,
        "usd_24h_vol": 35000000000,
        "usd_24h_change": 2.5,
        "last_updated_at": 1700000000,
    },
    "ethereum": {
        "usd": 3500.0,
        "usd_market_cap": 420000000000,
        "usd_24h_vol": 15000000000,
        "usd_24h_change": -1.2,
        "last_updated_at": 1700000000,
    },
}

FAKE_SEARCH = {
    "coins": [
        {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1, "thumb": "https://thumb.btc", "large": "https://large.btc"},
        {"id": "bitcoin-cash", "name": "Bitcoin Cash", "symbol": "bch", "market_cap_rank": 20, "thumb": "https://thumb.bch", "large": "https://large.bch"},
    ],
    "exchanges": [
        {"id": "binance", "name": "Binance", "market_type": "spot", "thumb": "https://thumb.binance"},
    ],
    "categories": [
        {"id": 1, "name": "Smart Contract Platform"},
    ],
}

FAKE_TRENDING = {
    "coins": [
        {"item": {"id": "pepe", "name": "Pepe", "symbol": "pepe", "market_cap_rank": 30, "thumb": "https://thumb.pepe", "price_btc": 0.0000001, "score": 0}},
        {"item": {"id": "dogecoin", "name": "Dogecoin", "symbol": "doge", "market_cap_rank": 8, "thumb": "https://thumb.doge", "price_btc": 0.000002, "score": 1}},
    ],
    "nfts": [
        {"id": "bored-ape", "name": "Bored Ape Yacht Club", "symbol": "BAYC", "thumb": "https://thumb.bayc"},
    ],
    "categories": [
        {"id": 1, "name": "Meme Tokens", "coins_count": 500},
    ],
}

FAKE_MARKETS = [
    {
        "id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
        "image": "https://img.btc",
        "current_price": 67000.0, "market_cap": 1320000000000,
        "market_cap_rank": 1, "total_volume": 35000000000,
        "high_24h": 68000.0, "low_24h": 66000.0,
        "price_change_24h": 1500.0, "price_change_percentage_24h": 2.3,
        "circulating_supply": 19700000, "total_supply": 21000000,
        "max_supply": 21000000,
        "ath": 73000.0, "ath_change_percentage": -8.2, "ath_date": "2024-03-14",
        "atl": 67.81, "atl_change_percentage": 98700.0, "atl_date": "2013-07-06",
        "last_updated": "2025-01-15T10:00:00Z",
    },
]

FAKE_COIN = {
    "id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
    "description": {"en": "Bitcoin is the first decentralized cryptocurrency."},
    "image": {"large": "https://img.btc/large.png"},
    "market_cap_rank": 1,
    "market_data": {
        "current_price": {"usd": 67000.0},
        "market_cap": {"usd": 1320000000000},
        "total_volume": {"usd": 35000000000},
        "high_24h": {"usd": 68000.0},
        "low_24h": {"usd": 66000.0},
        "price_change_percentage_24h": 2.3,
        "price_change_percentage_7d": 5.1,
        "price_change_percentage_30d": 15.2,
        "circulating_supply": 19700000,
        "total_supply": 21000000,
        "max_supply": 21000000,
        "ath": {"usd": 73000.0},
        "ath_change_percentage": {"usd": -8.2},
        "ath_date": {"usd": "2024-03-14"},
    },
    "genesis_date": "2009-01-03",
    "links": {
        "homepage": ["https://bitcoin.org"],
        "blockchain_site": ["https://blockchair.com/bitcoin", ""],
        "subreddit_url": "https://reddit.com/r/bitcoin",
    },
    "categories": ["Cryptocurrency", "Layer 1"],
    "sentiment_votes_up_percentage": 85.0,
    "watchlist_portfolio_users": 1500000,
}

FAKE_MARKET_CHART = {
    "prices": [[1700000000000, 65000.0], [1700003600000, 65500.0], [1700007200000, 67000.0]],
    "market_caps": [[1700000000000, 1280000000000], [1700003600000, 1290000000000], [1700007200000, 1320000000000]],
    "total_volumes": [[1700000000000, 30000000000], [1700003600000, 32000000000], [1700007200000, 35000000000]],
}

FAKE_OHLC = [
    [1700000000000, 65000.0, 66000.0, 64500.0, 65500.0],
    [1700086400000, 65500.0, 68000.0, 65000.0, 67000.0],
]

FAKE_GLOBAL = {
    "data": {
        "active_cryptocurrencies": 15000,
        "markets": 1100,
        "total_market_cap": {"usd": 2500000000000},
        "total_volume": {"usd": 100000000000},
        "market_cap_percentage": {"btc": 52.3, "eth": 16.8},
        "market_cap_change_percentage_24h_usd": 1.5,
        "updated_at": 1700000000,
    }
}

FAKE_CATEGORIES = [
    {
        "id": "decentralized-finance-defi", "name": "DeFi",
        "market_cap": 80000000000, "market_cap_change_24h": 3.2,
        "volume_24h": 5000000000,
        "top_3_coins": ["https://img1", "https://img2", "https://img3"],
        "updated_at": "2025-01-15T10:00:00Z",
    },
    {
        "id": "meme-token", "name": "Meme Tokens",
        "market_cap": 50000000000, "market_cap_change_24h": -2.1,
        "volume_24h": 8000000000,
        "top_3_coins": ["https://img4", "https://img5", "https://img6"],
        "updated_at": "2025-01-15T10:00:00Z",
    },
]

FAKE_EXCHANGE_RATES = {
    "rates": {
        "btc": {"name": "Bitcoin", "unit": "BTC", "value": 1.0, "type": "crypto"},
        "usd": {"name": "US Dollar", "unit": "$", "value": 67000.0, "type": "fiat"},
        "eur": {"name": "Euro", "unit": "\u20ac", "value": 62000.0, "type": "fiat"},
    }
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/simple/price": FAKE_SIMPLE_PRICE,
        "/search": FAKE_SEARCH,
        "/search/trending": FAKE_TRENDING,
        "/coins/markets": FAKE_MARKETS,
        "/coins/bitcoin": FAKE_COIN,
        "/coins/bitcoin/market_chart": FAKE_MARKET_CHART,
        "/coins/bitcoin/ohlc": FAKE_OHLC,
        "/global": FAKE_GLOBAL,
        "/coins/categories": FAKE_CATEGORIES,
        "/exchange_rates": FAKE_EXCHANGE_RATES,
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
    """CoinGeckoService with mocked HTTP client."""
    from coingecko_mcp.service import CoinGeckoService

    svc = CoinGeckoService.__new__(CoinGeckoService)
    svc._http = mock_http
    svc._api_key = None
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked CoinGeckoService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-cg", version="0.0.1")
    srv.register(service)
    return srv

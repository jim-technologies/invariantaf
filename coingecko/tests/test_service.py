"""Unit tests — every CoinGeckoService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from coingecko_mcp.gen.coingecko.v1 import coingecko_pb2 as pb
from tests.conftest import (
    FAKE_CATEGORIES,
    FAKE_COIN,
    FAKE_EXCHANGE_RATES,
    FAKE_GLOBAL,
    FAKE_MARKET_CHART,
    FAKE_MARKETS,
    FAKE_OHLC,
    FAKE_SEARCH,
    FAKE_SIMPLE_PRICE,
    FAKE_TRENDING,
)


class TestGetPrice:
    def test_returns_prices(self, service):
        resp = service.GetPrice(pb.GetPriceRequest(
            ids="bitcoin,ethereum", vs_currency="usd",
            include_market_cap=True, include_24h_vol=True, include_24h_change=True,
        ))
        assert len(resp.prices) == 2
        ids = {p.coin_id for p in resp.prices}
        assert "bitcoin" in ids
        assert "ethereum" in ids

    def test_bitcoin_price(self, service):
        resp = service.GetPrice(pb.GetPriceRequest(ids="bitcoin"))
        btc = [p for p in resp.prices if p.coin_id == "bitcoin"][0]
        assert btc.price == 67000.0
        assert btc.market_cap == 1320000000000
        assert btc.volume_24h == 35000000000
        assert btc.change_24h == 2.5
        assert btc.last_updated == 1700000000

    def test_ethereum_price(self, service):
        resp = service.GetPrice(pb.GetPriceRequest(ids="ethereum"))
        eth = [p for p in resp.prices if p.coin_id == "ethereum"][0]
        assert eth.price == 3500.0
        assert eth.change_24h == -1.2

    def test_default_vs_currency(self, service, mock_http):
        service.GetPrice(pb.GetPriceRequest(ids="bitcoin"))
        call_args = mock_http.get.call_args
        assert "usd" in call_args[1].get("params", {}).get("vs_currencies", "")

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetPrice(pb.GetPriceRequest(ids="nonexistent"))
        assert len(resp.prices) == 0


class TestSearch:
    def test_returns_coins(self, service):
        resp = service.Search(pb.SearchRequest(query="bitcoin"))
        assert len(resp.coins) == 2
        assert resp.coins[0].id == "bitcoin"
        assert resp.coins[0].name == "Bitcoin"
        assert resp.coins[0].symbol == "btc"
        assert resp.coins[0].market_cap_rank == 1

    def test_returns_exchanges(self, service):
        resp = service.Search(pb.SearchRequest(query="binance"))
        assert len(resp.exchanges) == 1
        assert resp.exchanges[0].id == "binance"
        assert resp.exchanges[0].name == "Binance"

    def test_returns_categories(self, service):
        resp = service.Search(pb.SearchRequest(query="smart"))
        assert len(resp.categories) == 1
        assert resp.categories[0].name == "Smart Contract Platform"


class TestGetTrending:
    def test_returns_trending_coins(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        assert len(resp.coins) == 2
        assert resp.coins[0].id == "pepe"
        assert resp.coins[0].name == "Pepe"
        assert resp.coins[0].score == 0

    def test_returns_trending_nfts(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        assert len(resp.nfts) == 1
        assert resp.nfts[0].id == "bored-ape"
        assert resp.nfts[0].name == "Bored Ape Yacht Club"

    def test_returns_trending_categories(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        assert len(resp.categories) == 1
        assert resp.categories[0].name == "Meme Tokens"
        assert resp.categories[0].coins_count == 500


class TestGetMarkets:
    def test_returns_market_list(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest())
        assert len(resp.coins) == 1
        btc = resp.coins[0]
        assert btc.id == "bitcoin"
        assert btc.symbol == "btc"
        assert btc.current_price == 67000.0
        assert btc.market_cap == 1320000000000
        assert btc.market_cap_rank == 1

    def test_24h_fields(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest())
        btc = resp.coins[0]
        assert btc.high_24h == 68000.0
        assert btc.low_24h == 66000.0
        assert btc.price_change_24h == 1500.0
        assert btc.price_change_percentage_24h == 2.3

    def test_supply_fields(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest())
        btc = resp.coins[0]
        assert btc.circulating_supply == 19700000
        assert btc.total_supply == 21000000
        assert btc.max_supply == 21000000

    def test_ath_atl_fields(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest())
        btc = resp.coins[0]
        assert btc.ath == 73000.0
        assert btc.atl == 67.81
        assert btc.ath_date == "2024-03-14"

    def test_with_category_filter(self, service, mock_http):
        service.GetMarkets(pb.GetMarketsRequest(category="defi"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("category") == "defi"


class TestGetCoin:
    def test_basic_fields(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.id == "bitcoin"
        assert resp.symbol == "btc"
        assert resp.name == "Bitcoin"
        assert resp.market_cap_rank == 1

    def test_description(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert "decentralized cryptocurrency" in resp.description

    def test_market_data(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.current_price_usd == 67000.0
        assert resp.market_cap_usd == 1320000000000
        assert resp.total_volume_usd == 35000000000
        assert resp.high_24h_usd == 68000.0
        assert resp.low_24h_usd == 66000.0

    def test_price_changes(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.price_change_percentage_24h == 2.3
        assert resp.price_change_percentage_7d == 5.1
        assert resp.price_change_percentage_30d == 15.2

    def test_supply(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.circulating_supply == 19700000
        assert resp.total_supply == 21000000
        assert resp.max_supply == 21000000

    def test_links(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.homepage == "https://bitcoin.org"
        assert resp.blockchain_site == "https://blockchair.com/bitcoin"
        assert resp.subreddit_url == "https://reddit.com/r/bitcoin"

    def test_categories_and_sentiment(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert "Cryptocurrency" in resp.categories
        assert "Layer 1" in resp.categories
        assert resp.sentiment_votes_up_percentage == 85.0
        assert resp.watchlist_users == 1500000

    def test_genesis_date(self, service):
        resp = service.GetCoin(pb.GetCoinRequest(coin_id="bitcoin"))
        assert resp.genesis_date == "2009-01-03"


class TestGetMarketChart:
    def test_returns_prices(self, service):
        resp = service.GetMarketChart(pb.GetMarketChartRequest(coin_id="bitcoin", days="1"))
        assert len(resp.prices) == 3
        assert resp.prices[0].timestamp == 1700000000000
        assert resp.prices[0].value == 65000.0
        assert resp.prices[2].value == 67000.0

    def test_returns_market_caps(self, service):
        resp = service.GetMarketChart(pb.GetMarketChartRequest(coin_id="bitcoin", days="1"))
        assert len(resp.market_caps) == 3
        assert resp.market_caps[0].value == 1280000000000

    def test_returns_volumes(self, service):
        resp = service.GetMarketChart(pb.GetMarketChartRequest(coin_id="bitcoin", days="1"))
        assert len(resp.total_volumes) == 3
        assert resp.total_volumes[2].value == 35000000000


class TestGetOHLC:
    def test_returns_candles(self, service):
        resp = service.GetOHLC(pb.GetOHLCRequest(coin_id="bitcoin", days="7"))
        assert len(resp.candles) == 2

    def test_candle_fields(self, service):
        resp = service.GetOHLC(pb.GetOHLCRequest(coin_id="bitcoin", days="7"))
        c = resp.candles[0]
        assert c.timestamp == 1700000000000
        assert c.open == 65000.0
        assert c.high == 66000.0
        assert c.low == 64500.0
        assert c.close == 65500.0


class TestGetGlobal:
    def test_basic_stats(self, service):
        resp = service.GetGlobal(pb.GetGlobalRequest())
        assert resp.active_cryptocurrencies == 15000
        assert resp.markets == 1100
        assert resp.total_market_cap_usd == 2500000000000
        assert resp.total_volume_usd == 100000000000

    def test_dominance(self, service):
        resp = service.GetGlobal(pb.GetGlobalRequest())
        assert resp.btc_dominance == 52.3
        assert resp.eth_dominance == 16.8

    def test_change_and_timestamp(self, service):
        resp = service.GetGlobal(pb.GetGlobalRequest())
        assert resp.market_cap_change_percentage_24h == 1.5
        assert resp.updated_at == 1700000000


class TestGetCategories:
    def test_returns_categories(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest())
        assert len(resp.categories) == 2
        assert resp.categories[0].id == "decentralized-finance-defi"
        assert resp.categories[0].name == "DeFi"
        assert resp.categories[0].market_cap == 80000000000

    def test_category_fields(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest())
        meme = resp.categories[1]
        assert meme.id == "meme-token"
        assert meme.market_cap_change_24h == -2.1
        assert meme.volume_24h == 8000000000
        assert len(meme.top_3_coins) == 3


class TestGetExchangeRates:
    def test_returns_rates(self, service):
        resp = service.GetExchangeRates(pb.GetExchangeRatesRequest())
        assert "btc" in resp.rates
        assert "usd" in resp.rates
        assert "eur" in resp.rates

    def test_rate_fields(self, service):
        resp = service.GetExchangeRates(pb.GetExchangeRatesRequest())
        usd = resp.rates["usd"]
        assert usd.name == "US Dollar"
        assert usd.unit == "$"
        assert usd.value == 67000.0
        assert usd.type == "fiat"

    def test_btc_rate(self, service):
        resp = service.GetExchangeRates(pb.GetExchangeRatesRequest())
        btc = resp.rates["btc"]
        assert btc.value == 1.0
        assert btc.type == "crypto"

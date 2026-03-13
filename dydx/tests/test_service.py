"""Unit tests — every DydxService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from dydx_mcp.gen.dydx.v1 import dydx_pb2 as pb
from tests.conftest import (
    FAKE_PERPETUAL_MARKETS,
    FAKE_ORDERBOOK,
    FAKE_TRADES,
    FAKE_CANDLES,
    FAKE_FUNDING_RATES,
)


class TestListMarkets:
    def test_returns_markets(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        assert len(resp.markets) == 2

    def test_btc_market_ticker(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        tickers = [m.ticker for m in resp.markets]
        assert "BTC-USD" in tickers

    def test_eth_market_ticker(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        tickers = [m.ticker for m in resp.markets]
        assert "ETH-USD" in tickers

    def test_market_status(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        btc = [m for m in resp.markets if m.ticker == "BTC-USD"][0]
        assert btc.status == "ACTIVE"

    def test_market_oracle_price(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        btc = [m for m in resp.markets if m.ticker == "BTC-USD"][0]
        assert btc.oracle_price == "97500.00"

    def test_market_funding_rate(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        btc = [m for m in resp.markets if m.ticker == "BTC-USD"][0]
        assert btc.next_funding_rate == "0.000125"

    def test_market_volume_24h(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        btc = [m for m in resp.markets if m.ticker == "BTC-USD"][0]
        assert btc.volume_24h == "1250000000.50"

    def test_market_open_interest(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        btc = [m for m in resp.markets if m.ticker == "BTC-USD"][0]
        assert btc.open_interest == "4500.123"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.ListMarkets(pb.ListMarketsRequest())
        assert len(resp.markets) == 0


class TestGetOrderbook:
    def test_returns_bids(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert len(resp.bids) == 3

    def test_returns_asks(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert len(resp.asks) == 3

    def test_best_bid_price(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert resp.bids[0].price == "97500.00"

    def test_best_bid_size(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert resp.bids[0].size == "1.5"

    def test_best_ask_price(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert resp.asks[0].price == "97501.00"

    def test_best_ask_size(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert resp.asks[0].size == "1.2"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetOrderbook(pb.GetOrderbookRequest(ticker="BTC-USD"))
        assert len(resp.bids) == 0
        assert len(resp.asks) == 0


class TestGetTrades:
    def test_returns_trades(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert len(resp.trades) == 3

    def test_first_trade_id(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[0].id == "trade-001"

    def test_trade_side_buy(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[0].side == pb.TRADE_SIDE_BUY

    def test_trade_side_sell(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[1].side == pb.TRADE_SIDE_SELL

    def test_trade_price(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[0].price == "97500.50"

    def test_trade_size(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[0].size == "0.5"

    def test_trade_created_at(self, service):
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert resp.trades[0].created_at == "2026-03-12T10:30:00.000Z"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetTrades(pb.GetTradesRequest(ticker="BTC-USD"))
        assert len(resp.trades) == 0


class TestGetCandles:
    def test_returns_candles(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert len(resp.candles) == 2

    def test_candle_open(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].open == "97400.00"

    def test_candle_high(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].high == "97600.00"

    def test_candle_low(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].low == "97350.00"

    def test_candle_close(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].close == "97500.00"

    def test_candle_volume(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].base_token_volume == "125.5"

    def test_candle_usd_volume(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].usd_volume == "12231250.00"

    def test_candle_trades_count(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].trades == 1542

    def test_candle_started_at(self, service):
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert resp.candles[0].started_at == "2026-03-12T10:00:00.000Z"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetCandles(pb.GetCandlesRequest(
            ticker="BTC-USD",
            resolution=pb.CANDLE_RESOLUTION_1HOUR,
        ))
        assert len(resp.candles) == 0


class TestGetFundingRates:
    def test_returns_funding_rates(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert len(resp.funding_rates) == 3

    def test_first_rate_ticker(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert resp.funding_rates[0].ticker == "BTC-USD"

    def test_first_rate_value(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert resp.funding_rates[0].rate == "0.000125"

    def test_first_rate_price(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert resp.funding_rates[0].price == "97500.00"

    def test_first_rate_effective_at(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert resp.funding_rates[0].effective_at == "2026-03-12T10:00:00.000Z"

    def test_negative_funding_rate(self, service):
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert resp.funding_rates[2].rate == "-0.000015"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetFundingRates(pb.GetFundingRatesRequest(ticker="BTC-USD"))
        assert len(resp.funding_rates) == 0

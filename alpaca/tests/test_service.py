"""Unit tests — every AlpacaService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

import httpx

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb
from tests.conftest import (
    FAKE_ACCOUNT,
    FAKE_ASSET,
    FAKE_BARS,
    FAKE_LATEST_QUOTE,
    FAKE_LATEST_TRADE,
    FAKE_ORDER_PLACED,
    FAKE_ORDERS,
    FAKE_POSITION_AAPL,
    FAKE_POSITIONS,
)


class TestGetAccount:
    def test_returns_account_info(self, service):
        resp = service.GetAccount(pb.GetAccountRequest())
        assert resp.id == "904837e3-3b76-47ec-b432-046db621571b"
        assert resp.status == "ACTIVE"
        assert resp.currency == "USD"

    def test_financial_fields(self, service):
        resp = service.GetAccount(pb.GetAccountRequest())
        assert resp.buying_power == 50000.0
        assert resp.cash == 25000.0
        assert resp.portfolio_value == 75000.0
        assert resp.equity == 75000.0
        assert resp.last_equity == 74500.0

    def test_market_values(self, service):
        resp = service.GetAccount(pb.GetAccountRequest())
        assert resp.long_market_value == 50000.0
        assert resp.short_market_value == 0.0

    def test_flags(self, service):
        resp = service.GetAccount(pb.GetAccountRequest())
        assert resp.pattern_day_trader is False
        assert resp.trading_blocked is False
        assert resp.account_blocked is False


class TestGetPositions:
    def test_returns_all_positions(self, service):
        resp = service.GetPositions(pb.GetPositionsRequest())
        assert len(resp.positions) == 2

    def test_aapl_position(self, service):
        resp = service.GetPositions(pb.GetPositionsRequest())
        aapl = resp.positions[0]
        assert aapl.symbol == "AAPL"
        assert aapl.qty == "10"
        assert aapl.avg_entry_price == "175.50"
        assert aapl.current_price == "182.30"
        assert aapl.market_value == "1823.00"
        assert aapl.unrealized_pl == "68.00"
        assert aapl.side == "long"

    def test_msft_position(self, service):
        resp = service.GetPositions(pb.GetPositionsRequest())
        msft = resp.positions[1]
        assert msft.symbol == "MSFT"
        assert msft.qty == "5"
        assert msft.avg_entry_price == "410.00"
        assert msft.exchange == "NASDAQ"

    def test_empty_positions(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        resp = service.GetPositions(pb.GetPositionsRequest())
        assert len(resp.positions) == 0


class TestGetPosition:
    def test_returns_single_position(self, service):
        resp = service.GetPosition(pb.GetPositionRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.qty == "10"
        assert resp.avg_entry_price == "175.50"
        assert resp.current_price == "182.30"
        assert resp.unrealized_pl == "68.00"
        assert resp.unrealized_plpc == "0.0387"
        assert resp.asset_class == "us_equity"

    def test_cost_basis(self, service):
        resp = service.GetPosition(pb.GetPositionRequest(symbol="AAPL"))
        assert resp.cost_basis == "1755.00"

    def test_calls_correct_url(self, service, mock_http):
        service.GetPosition(pb.GetPositionRequest(symbol="AAPL"))
        call_url = mock_http.get.call_args[0][0]
        assert "/v2/positions/AAPL" in call_url


class TestPlaceOrder:
    def test_limit_buy_order(self, service):
        req = pb.PlaceOrderRequest(
            symbol="AAPL",
            qty=10,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price=180.0,
        )
        resp = service.PlaceOrder(req)
        assert resp.id == "61e69015-8549-4baf-b96e-8c4c0c2a4bfc"
        assert resp.status == "accepted"
        assert resp.symbol == "AAPL"
        assert resp.side == "buy"
        assert resp.type == "limit"

    def test_market_order(self, service):
        req = pb.PlaceOrderRequest(
            symbol="AAPL",
            qty=5,
            side="buy",
            type="market",
            time_in_force="day",
        )
        resp = service.PlaceOrder(req)
        assert resp.id == "61e69015-8549-4baf-b96e-8c4c0c2a4bfc"
        assert resp.status == "accepted"

    def test_posts_to_correct_url(self, service, mock_http):
        service.PlaceOrder(pb.PlaceOrderRequest(
            symbol="AAPL", qty=10, side="buy", type="market", time_in_force="day",
        ))
        call_url = mock_http.post.call_args[0][0]
        assert "/v2/orders" in call_url

    def test_order_body_contains_symbol(self, service, mock_http):
        service.PlaceOrder(pb.PlaceOrderRequest(
            symbol="TSLA", qty=5, side="sell", type="market", time_in_force="gtc",
        ))
        call_kwargs = mock_http.post.call_args[1]
        body = call_kwargs.get("json", {})
        assert body["symbol"] == "TSLA"
        assert body["side"] == "sell"
        assert body["type"] == "market"

    def test_default_time_in_force(self, service, mock_http):
        service.PlaceOrder(pb.PlaceOrderRequest(
            symbol="AAPL", qty=1, side="buy", type="market",
        ))
        call_kwargs = mock_http.post.call_args[1]
        body = call_kwargs.get("json", {})
        assert body["time_in_force"] == "day"

    def test_created_at_field(self, service):
        resp = service.PlaceOrder(pb.PlaceOrderRequest(
            symbol="AAPL", qty=10, side="buy", type="market", time_in_force="day",
        ))
        assert resp.created_at == "2025-01-15T10:00:00Z"


class TestGetOrders:
    def test_returns_all_orders(self, service):
        resp = service.GetOrders(pb.GetOrdersRequest())
        assert len(resp.orders) == 2

    def test_limit_order_fields(self, service):
        resp = service.GetOrders(pb.GetOrdersRequest())
        o = resp.orders[0]
        assert o.id == "61e69015-8549-4baf-b96e-8c4c0c2a4bfc"
        assert o.symbol == "AAPL"
        assert o.qty == "10"
        assert o.side == "buy"
        assert o.type == "limit"
        assert o.status == "new"
        assert o.limit_price == "180.00"

    def test_filled_order_fields(self, service):
        resp = service.GetOrders(pb.GetOrdersRequest())
        o = resp.orders[1]
        assert o.symbol == "MSFT"
        assert o.status == "filled"
        assert o.filled_qty == "5"
        assert o.filled_avg_price == "420.50"
        assert o.filled_at == "2025-01-14T14:30:01Z"

    def test_status_filter(self, service, mock_http):
        service.GetOrders(pb.GetOrdersRequest(status="open"))
        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1].get("params", {})
        assert params.get("status") == "open"

    def test_limit_param(self, service, mock_http):
        service.GetOrders(pb.GetOrdersRequest(limit=10))
        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1].get("params", {})
        assert params.get("limit") == 10


class TestCancelOrder:
    def test_successful_cancel(self, service):
        resp = service.CancelOrder(pb.CancelOrderRequest(
            order_id="61e69015-8549-4baf-b96e-8c4c0c2a4bfc",
        ))
        assert resp.success is True
        assert resp.error == ""

    def test_delete_called_with_correct_url(self, service, mock_http):
        service.CancelOrder(pb.CancelOrderRequest(order_id="abc-123"))
        call_url = mock_http.delete.call_args[0][0]
        assert "/v2/orders/abc-123" in call_url

    def test_failed_cancel(self, service, mock_http):
        error_resp = MagicMock()
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_http.delete.side_effect = lambda url: error_resp
        resp = service.CancelOrder(pb.CancelOrderRequest(order_id="bad-id"))
        assert resp.success is False
        assert resp.error != ""


class TestGetAsset:
    def test_returns_asset_details(self, service):
        resp = service.GetAsset(pb.GetAssetRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.name == "Apple Inc."
        assert resp.asset_class == "us_equity"
        assert resp.exchange == "NASDAQ"

    def test_tradable_flags(self, service):
        resp = service.GetAsset(pb.GetAssetRequest(symbol="AAPL"))
        assert resp.tradable is True
        assert resp.fractionable is True
        assert resp.shortable is True
        assert resp.marginable is True

    def test_status(self, service):
        resp = service.GetAsset(pb.GetAssetRequest(symbol="AAPL"))
        assert resp.status == "active"


class TestGetBars:
    def test_returns_bars(self, service):
        resp = service.GetBars(pb.GetBarsRequest(
            symbol="AAPL", timeframe="1Day", start="2025-01-13",
        ))
        assert len(resp.bars) == 2
        assert resp.symbol == "AAPL"

    def test_bar_fields(self, service):
        resp = service.GetBars(pb.GetBarsRequest(
            symbol="AAPL", timeframe="1Day", start="2025-01-13",
        ))
        b = resp.bars[0]
        assert b.timestamp == "2025-01-13T05:00:00Z"
        assert b.open == 178.50
        assert b.high == 182.00
        assert b.low == 177.80
        assert b.close == 181.20
        assert b.volume == 65000000
        assert b.vwap == 180.10
        assert b.trade_count == 850000

    def test_second_bar(self, service):
        resp = service.GetBars(pb.GetBarsRequest(
            symbol="AAPL", timeframe="1Day", start="2025-01-13",
        ))
        b = resp.bars[1]
        assert b.open == 181.20
        assert b.close == 182.30

    def test_uses_data_url(self, service, mock_http):
        service.GetBars(pb.GetBarsRequest(symbol="AAPL", timeframe="1Day", start="2025-01-13"))
        call_url = mock_http.get.call_args[0][0]
        assert "data.alpaca.markets" in call_url

    def test_empty_bars(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"bars": [], "symbol": "AAPL"}),
        )
        resp = service.GetBars(pb.GetBarsRequest(symbol="AAPL", timeframe="1Day", start="2025-01-13"))
        assert len(resp.bars) == 0


class TestGetLatestQuote:
    def test_returns_quote(self, service):
        resp = service.GetLatestQuote(pb.GetLatestQuoteRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.bid_price == 182.25
        assert resp.bid_size == 3
        assert resp.ask_price == 182.30
        assert resp.ask_size == 5

    def test_timestamp(self, service):
        resp = service.GetLatestQuote(pb.GetLatestQuoteRequest(symbol="AAPL"))
        assert resp.timestamp == "2025-01-15T15:30:00.123Z"

    def test_uses_data_url(self, service, mock_http):
        service.GetLatestQuote(pb.GetLatestQuoteRequest(symbol="AAPL"))
        call_url = mock_http.get.call_args[0][0]
        assert "data.alpaca.markets" in call_url
        assert "/v2/stocks/AAPL/quotes/latest" in call_url


class TestGetLatestTrade:
    def test_returns_trade(self, service):
        resp = service.GetLatestTrade(pb.GetLatestTradeRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.price == 182.28
        assert resp.size == 100
        assert resp.exchange == "V"

    def test_timestamp(self, service):
        resp = service.GetLatestTrade(pb.GetLatestTradeRequest(symbol="AAPL"))
        assert resp.timestamp == "2025-01-15T15:30:00.456Z"

    def test_uses_data_url(self, service, mock_http):
        service.GetLatestTrade(pb.GetLatestTradeRequest(symbol="AAPL"))
        call_url = mock_http.get.call_args[0][0]
        assert "data.alpaca.markets" in call_url
        assert "/v2/stocks/AAPL/trades/latest" in call_url

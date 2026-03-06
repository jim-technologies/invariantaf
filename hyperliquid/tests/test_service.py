"""Unit tests for HyperliquidService — all SDK calls are mocked."""

import pytest

from hyperliquid_mcp.gen.hyperliquid.v1 import hyperliquid_pb2 as pb
from tests.conftest import (
    FAKE_CANCEL_FAIL,
    FAKE_ORDER_ERROR,
    FAKE_ORDER_FILLED,
)


# ---------------------------------------------------------------------------
# Market data (read-only, no auth)
# ---------------------------------------------------------------------------


class TestGetMeta:
    def test_returns_all_assets(self, service):
        resp = service.GetMeta(pb.GetMetaRequest())
        assert len(resp.assets) == 3
        assert resp.assets[0].name == "BTC"
        assert resp.assets[0].size_decimals == 5
        assert resp.assets[0].max_leverage == 40

    def test_eth_asset(self, service):
        resp = service.GetMeta(pb.GetMetaRequest())
        eth = resp.assets[1]
        assert eth.name == "ETH"
        assert eth.size_decimals == 4
        assert eth.max_leverage == 25

    def test_empty_universe(self, service, mock_info):
        mock_info.meta.return_value = {"universe": []}
        resp = service.GetMeta(pb.GetMetaRequest())
        assert len(resp.assets) == 0


class TestGetAllMids:
    def test_returns_all_mids(self, service):
        resp = service.GetAllMids(pb.GetAllMidsRequest())
        assert resp.mids["BTC"] == "67000.0"
        assert resp.mids["ETH"] == "3500.0"
        assert resp.mids["SOL"] == "150.0"
        assert len(resp.mids) == 3


class TestGetOrderbook:
    def test_bids_and_asks(self, service):
        resp = service.GetOrderbook(pb.GetOrderbookRequest(coin="BTC"))
        assert len(resp.bids) == 2
        assert len(resp.asks) == 2
        assert resp.bids[0].price == "66990.0"
        assert resp.bids[0].size == "1.5"
        assert resp.asks[0].price == "67010.0"
        assert resp.asks[0].size == "0.8"

    def test_calls_sdk_with_coin(self, service, mock_info):
        service.GetOrderbook(pb.GetOrderbookRequest(coin="ETH"))
        mock_info.l2_snapshot.assert_called_once_with("ETH")

    def test_empty_levels(self, service, mock_info):
        mock_info.l2_snapshot.return_value = {"levels": [[], []]}
        resp = service.GetOrderbook(pb.GetOrderbookRequest(coin="BTC"))
        assert len(resp.bids) == 0
        assert len(resp.asks) == 0


class TestGetCandles:
    def test_returns_candles(self, service):
        req = pb.GetCandlesRequest(
            coin="BTC",
            interval=pb.CANDLE_INTERVAL_1H,
            start_time=1700000000000,
            end_time=1700007200000,
        )
        resp = service.GetCandles(req)
        assert len(resp.candles) == 2
        assert resp.candles[0].open == "67000.0"
        assert resp.candles[0].close == "67100.0"
        assert resp.candles[0].high == "67200.0"
        assert resp.candles[0].low == "66900.0"
        assert resp.candles[0].volume == "500.5"
        assert resp.candles[0].time == 1700000000000

    def test_interval_mapping(self, service, mock_info):
        for proto_interval, sdk_string in [
            (pb.CANDLE_INTERVAL_1M, "1m"),
            (pb.CANDLE_INTERVAL_5M, "5m"),
            (pb.CANDLE_INTERVAL_15M, "15m"),
            (pb.CANDLE_INTERVAL_1H, "1h"),
            (pb.CANDLE_INTERVAL_4H, "4h"),
            (pb.CANDLE_INTERVAL_1D, "1d"),
        ]:
            service.GetCandles(
                pb.GetCandlesRequest(
                    coin="BTC", interval=proto_interval, start_time=0, end_time=0
                )
            )
            _, kwargs = mock_info.candles_snapshot.call_args
            # candles_snapshot is called with positional args
            args = mock_info.candles_snapshot.call_args[0]
            assert args[1] == sdk_string, f"{proto_interval} should map to {sdk_string}"

    def test_unspecified_interval_defaults_to_1h(self, service, mock_info):
        service.GetCandles(
            pb.GetCandlesRequest(
                coin="BTC",
                interval=pb.CANDLE_INTERVAL_UNSPECIFIED,
                start_time=0,
                end_time=0,
            )
        )
        args = mock_info.candles_snapshot.call_args[0]
        assert args[1] == "1h"


# ---------------------------------------------------------------------------
# Account data (read-only, needs address)
# ---------------------------------------------------------------------------


class TestGetAccountState:
    def test_account_summary(self, service):
        resp = service.GetAccountState(
            pb.GetAccountStateRequest(address="0xabc")
        )
        assert resp.account_value == "10000.0"
        assert resp.margin_used == "850.0"
        assert resp.withdrawable == "9150.0"

    def test_positions(self, service):
        resp = service.GetAccountState(
            pb.GetAccountStateRequest(address="0xabc")
        )
        assert len(resp.positions) == 1
        pos = resp.positions[0]
        assert pos.coin == "ETH"
        assert pos.size == "2.5"
        assert pos.entry_price == "3400.0"
        assert pos.unrealized_pnl == "250.0"
        assert pos.liquidation_price == "2800.0"
        assert pos.leverage == "10"
        assert pos.margin_used == "850.0"

    def test_cross_margin_summary(self, service):
        resp = service.GetAccountState(
            pb.GetAccountStateRequest(address="0xabc")
        )
        cms = resp.cross_margin_summary
        assert cms.account_value == "10000.0"
        assert cms.total_notional == "8500.0"
        assert cms.total_margin_used == "850.0"
        assert cms.total_raw_usd == "1500.0"

    def test_no_positions(self, service, mock_info):
        mock_info.user_state.return_value = {
            "assetPositions": [],
            "crossMarginSummary": {},
            "marginSummary": {"accountValue": "5000.0", "totalMarginUsed": "0.0"},
            "withdrawable": "5000.0",
        }
        resp = service.GetAccountState(
            pb.GetAccountStateRequest(address="0xabc")
        )
        assert len(resp.positions) == 0
        assert resp.account_value == "5000.0"

    def test_leverage_as_non_dict(self, service, mock_info):
        """Some edge cases return leverage as a plain value."""
        state = {
            "assetPositions": [
                {
                    "position": {
                        "coin": "BTC",
                        "szi": "0.1",
                        "entryPx": "67000.0",
                        "liquidationPx": "",
                        "unrealizedPnl": "0.0",
                        "returnOnEquity": "0.0",
                        "leverage": 5,  # plain int, not dict
                        "marginUsed": "1340.0",
                    },
                    "type": "oneWay",
                }
            ],
            "crossMarginSummary": {},
            "marginSummary": {"accountValue": "10000.0", "totalMarginUsed": "1340.0"},
            "withdrawable": "8660.0",
        }
        mock_info.user_state.return_value = state
        resp = service.GetAccountState(
            pb.GetAccountStateRequest(address="0xabc")
        )
        # leverage should be empty string when it's not a dict
        assert resp.positions[0].leverage == ""


class TestGetOpenOrders:
    def test_returns_orders(self, service):
        resp = service.GetOpenOrders(
            pb.GetOpenOrdersRequest(address="0xabc")
        )
        assert len(resp.orders) == 2

    def test_buy_side(self, service):
        resp = service.GetOpenOrders(
            pb.GetOpenOrdersRequest(address="0xabc")
        )
        assert resp.orders[0].side == pb.SIDE_BUY
        assert resp.orders[0].coin == "BTC"
        assert resp.orders[0].limit_price == "65000.0"
        assert resp.orders[0].order_id == 12345

    def test_sell_side(self, service):
        resp = service.GetOpenOrders(
            pb.GetOpenOrdersRequest(address="0xabc")
        )
        assert resp.orders[1].side == pb.SIDE_SELL
        assert resp.orders[1].coin == "ETH"

    def test_empty_orders(self, service, mock_info):
        mock_info.open_orders.return_value = []
        resp = service.GetOpenOrders(
            pb.GetOpenOrdersRequest(address="0xabc")
        )
        assert len(resp.orders) == 0


class TestGetFills:
    def test_returns_fills(self, service):
        resp = service.GetFills(pb.GetFillsRequest(address="0xabc"))
        assert len(resp.fills) == 2

    def test_fill_fields(self, service):
        resp = service.GetFills(pb.GetFillsRequest(address="0xabc"))
        f = resp.fills[0]
        assert f.coin == "BTC"
        assert f.price == "67000.0"
        assert f.size == "0.5"
        assert f.side == pb.SIDE_BUY
        assert f.fee == "3.35"
        assert f.closed_pnl == "0.0"

    def test_sell_fill_with_pnl(self, service):
        resp = service.GetFills(pb.GetFillsRequest(address="0xabc"))
        f = resp.fills[1]
        assert f.side == pb.SIDE_SELL
        assert f.closed_pnl == "250.0"


# ---------------------------------------------------------------------------
# Trading (authenticated)
# ---------------------------------------------------------------------------


class TestPlaceOrder:
    def test_resting_order(self, service):
        req = pb.PlaceOrderRequest(
            coin="BTC",
            side=pb.SIDE_BUY,
            size="0.1",
            price="65000.0",
            time_in_force=pb.TIME_IN_FORCE_GTC,
        )
        resp = service.PlaceOrder(req)
        assert resp.success is True
        assert resp.order_id == 99999
        assert resp.status == "resting"

    def test_filled_order(self, service, mock_exchange):
        mock_exchange.order.return_value = FAKE_ORDER_FILLED
        req = pb.PlaceOrderRequest(
            coin="BTC",
            side=pb.SIDE_BUY,
            size="0.1",
            price="67500.0",
            time_in_force=pb.TIME_IN_FORCE_IOC,
        )
        resp = service.PlaceOrder(req)
        assert resp.success is True
        assert resp.order_id == 88888
        assert resp.status == "filled"

    def test_rejected_order(self, service, mock_exchange):
        mock_exchange.order.return_value = FAKE_ORDER_ERROR
        req = pb.PlaceOrderRequest(
            coin="BTC",
            side=pb.SIDE_BUY,
            size="100.0",
            price="65000.0",
        )
        resp = service.PlaceOrder(req)
        assert resp.success is False
        assert "Insufficient margin" in resp.error

    def test_sdk_exception(self, service, mock_exchange):
        mock_exchange.order.side_effect = Exception("Network timeout")
        req = pb.PlaceOrderRequest(
            coin="BTC", side=pb.SIDE_BUY, size="0.1", price="65000.0"
        )
        resp = service.PlaceOrder(req)
        assert resp.success is False
        assert "Network timeout" in resp.error

    def test_tif_mapping(self, service, mock_exchange):
        for tif_proto, tif_str in [
            (pb.TIME_IN_FORCE_GTC, "Gtc"),
            (pb.TIME_IN_FORCE_IOC, "Ioc"),
            (pb.TIME_IN_FORCE_ALO, "Alo"),
        ]:
            service.PlaceOrder(
                pb.PlaceOrderRequest(
                    coin="BTC",
                    side=pb.SIDE_BUY,
                    size="0.1",
                    price="65000.0",
                    time_in_force=tif_proto,
                )
            )
            _, kwargs = mock_exchange.order.call_args
            args = mock_exchange.order.call_args[0]
            order_type = args[4]  # 5th positional arg
            assert order_type == {"limit": {"tif": tif_str}}

    def test_sell_side(self, service, mock_exchange):
        service.PlaceOrder(
            pb.PlaceOrderRequest(
                coin="ETH", side=pb.SIDE_SELL, size="1.0", price="3800.0"
            )
        )
        args = mock_exchange.order.call_args[0]
        assert args[0] == "ETH"  # coin
        assert args[1] is False  # is_buy = False for SELL

    def test_reduce_only(self, service, mock_exchange):
        service.PlaceOrder(
            pb.PlaceOrderRequest(
                coin="BTC",
                side=pb.SIDE_SELL,
                size="0.1",
                price="70000.0",
                reduce_only=True,
            )
        )
        _, kwargs = mock_exchange.order.call_args
        assert kwargs["reduce_only"] is True

    def test_requires_auth(self, service_no_auth):
        req = pb.PlaceOrderRequest(
            coin="BTC", side=pb.SIDE_BUY, size="0.1", price="65000.0"
        )
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.PlaceOrder(req)


class TestCancelOrder:
    def test_success(self, service):
        resp = service.CancelOrder(
            pb.CancelOrderRequest(coin="BTC", order_id=12345)
        )
        assert resp.success is True
        assert resp.error == ""

    def test_failure(self, service, mock_exchange):
        mock_exchange.cancel.return_value = FAKE_CANCEL_FAIL
        resp = service.CancelOrder(
            pb.CancelOrderRequest(coin="BTC", order_id=99999)
        )
        assert resp.success is False
        assert "Order not found" in resp.error

    def test_sdk_exception(self, service, mock_exchange):
        mock_exchange.cancel.side_effect = Exception("Connection error")
        resp = service.CancelOrder(
            pb.CancelOrderRequest(coin="BTC", order_id=12345)
        )
        assert resp.success is False
        assert "Connection error" in resp.error

    def test_requires_auth(self, service_no_auth):
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.CancelOrder(
                pb.CancelOrderRequest(coin="BTC", order_id=12345)
            )


class TestMarketOpen:
    def test_success(self, service):
        resp = service.MarketOpen(
            pb.MarketOpenRequest(coin="BTC", side=pb.SIDE_BUY, size="0.1")
        )
        assert resp.success is True
        assert resp.status == "filled"

    def test_with_slippage(self, service, mock_exchange):
        service.MarketOpen(
            pb.MarketOpenRequest(
                coin="BTC", side=pb.SIDE_BUY, size="0.1", slippage=0.05
            )
        )
        _, kwargs = mock_exchange.market_open.call_args
        assert kwargs["slippage"] == 0.05

    def test_default_slippage(self, service, mock_exchange):
        service.MarketOpen(
            pb.MarketOpenRequest(coin="BTC", side=pb.SIDE_BUY, size="0.1")
        )
        _, kwargs = mock_exchange.market_open.call_args
        assert kwargs["slippage"] == 0.01

    def test_sdk_exception(self, service, mock_exchange):
        mock_exchange.market_open.side_effect = Exception("Rate limited")
        resp = service.MarketOpen(
            pb.MarketOpenRequest(coin="BTC", side=pb.SIDE_BUY, size="0.1")
        )
        assert resp.success is False
        assert "Rate limited" in resp.error

    def test_requires_auth(self, service_no_auth):
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.MarketOpen(
                pb.MarketOpenRequest(coin="BTC", side=pb.SIDE_BUY, size="0.1")
            )


class TestMarketClose:
    def test_success(self, service):
        resp = service.MarketClose(pb.MarketCloseRequest(coin="ETH"))
        assert resp.success is True

    def test_no_position(self, service, mock_exchange):
        mock_exchange.market_close.return_value = None
        resp = service.MarketClose(pb.MarketCloseRequest(coin="DOGE"))
        assert resp.success is False
        assert "No open position" in resp.error

    def test_with_slippage(self, service, mock_exchange):
        service.MarketClose(pb.MarketCloseRequest(coin="ETH", slippage=0.02))
        _, kwargs = mock_exchange.market_close.call_args
        assert kwargs["slippage"] == 0.02

    def test_requires_auth(self, service_no_auth):
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.MarketClose(pb.MarketCloseRequest(coin="ETH"))


class TestUpdateLeverage:
    def test_success(self, service):
        resp = service.UpdateLeverage(
            pb.UpdateLeverageRequest(coin="BTC", leverage=20, is_cross=True)
        )
        assert resp.success is True

    def test_sdk_args(self, service, mock_exchange):
        service.UpdateLeverage(
            pb.UpdateLeverageRequest(coin="ETH", leverage=5, is_cross=False)
        )
        args = mock_exchange.update_leverage.call_args[0]
        assert args[0] == 5  # leverage
        assert args[1] == "ETH"  # coin
        _, kwargs = mock_exchange.update_leverage.call_args
        assert kwargs["is_cross"] is False

    def test_sdk_exception(self, service, mock_exchange):
        mock_exchange.update_leverage.side_effect = Exception("Invalid leverage")
        resp = service.UpdateLeverage(
            pb.UpdateLeverageRequest(coin="BTC", leverage=200)
        )
        assert resp.success is False
        assert "Invalid leverage" in resp.error

    def test_requires_auth(self, service_no_auth):
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.UpdateLeverage(
                pb.UpdateLeverageRequest(coin="BTC", leverage=10)
            )


class TestTransfer:
    def test_success(self, service):
        resp = service.Transfer(
            pb.TransferRequest(destination="0xdest", amount="100.0")
        )
        assert resp.success is True

    def test_sdk_exception(self, service, mock_exchange):
        mock_exchange.usd_transfer.side_effect = Exception("Insufficient balance")
        resp = service.Transfer(
            pb.TransferRequest(destination="0xdest", amount="999999.0")
        )
        assert resp.success is False
        assert "Insufficient balance" in resp.error

    def test_requires_auth(self, service_no_auth):
        with pytest.raises(ValueError, match="requires authentication"):
            service_no_auth.Transfer(
                pb.TransferRequest(destination="0xdest", amount="100.0")
            )


# ---------------------------------------------------------------------------
# _parse_order_result edge cases
# ---------------------------------------------------------------------------


class TestParseOrderResult:
    def test_bad_status(self):
        from hyperliquid_mcp.service import _parse_order_result

        resp = _parse_order_result({"status": "err", "error": "bad request"})
        assert resp.success is False

    def test_empty_statuses(self):
        from hyperliquid_mcp.service import _parse_order_result

        resp = _parse_order_result(
            {"status": "ok", "response": {"data": {"statuses": []}}}
        )
        assert resp.success is False
        assert "No status" in resp.error

    def test_unknown_status_shape(self):
        from hyperliquid_mcp.service import _parse_order_result

        resp = _parse_order_result(
            {"status": "ok", "response": {"data": {"statuses": ["unexpected"]}}}
        )
        assert resp.success is False

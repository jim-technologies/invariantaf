"""Unit tests -- every CoinGlassService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from coinglass_mcp.gen.coinglass.v1 import coinglass_pb2 as pb
from tests.conftest import (
    FAKE_FUNDING_RATE,
    FAKE_FUNDING_RATE_BTC,
    FAKE_OPEN_INTEREST,
    FAKE_LIQUIDATION,
    FAKE_LONG_SHORT,
    FAKE_OI_HISTORY,
)


class TestGetFundingRate:
    def test_returns_all_symbols(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        assert len(resp.data) == 2

    def test_btc_symbol(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest(symbol="BTC"))
        assert len(resp.data) == 1
        assert resp.data[0].symbol == "BTC"

    def test_exchange_count(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        btc = resp.data[0]
        assert len(btc.exchanges) == 3

    def test_exchange_fields(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        ex = resp.data[0].exchanges[0]
        assert ex.exchange == "Binance"
        assert ex.rate == 0.0001
        assert ex.predicted_rate == 0.00012

    def test_second_exchange(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        ex = resp.data[0].exchanges[1]
        assert ex.exchange == "Bybit"
        assert ex.rate == 0.00008
        assert ex.predicted_rate == 0.0001

    def test_eth_funding_rate(self, service):
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        eth = resp.data[1]
        assert eth.symbol == "ETH"
        assert len(eth.exchanges) == 2
        assert eth.exchanges[0].exchange == "Binance"
        assert eth.exchanges[0].rate == 0.00005

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"code": "0", "msg": "success", "data": []}),
        )
        resp = service.GetFundingRate(pb.GetFundingRateRequest())
        assert len(resp.data) == 0


class TestGetOpenInterest:
    def test_returns_data(self, service):
        resp = service.GetOpenInterest(pb.GetOpenInterestRequest(symbol="BTC"))
        assert resp.data is not None

    def test_exchange_count(self, service):
        resp = service.GetOpenInterest(pb.GetOpenInterestRequest(symbol="BTC"))
        assert len(resp.data.exchanges) == 3

    def test_exchange_fields(self, service):
        resp = service.GetOpenInterest(pb.GetOpenInterestRequest(symbol="BTC"))
        ex = resp.data.exchanges[0]
        assert ex.exchange == "Binance"
        assert ex.open_interest_usd == 5200000000.0
        assert ex.open_interest_amount == 80000.5

    def test_second_exchange(self, service):
        resp = service.GetOpenInterest(pb.GetOpenInterestRequest(symbol="BTC"))
        ex = resp.data.exchanges[1]
        assert ex.exchange == "Bybit"
        assert ex.open_interest_usd == 2100000000.0
        assert ex.open_interest_amount == 32000.25

    def test_third_exchange(self, service):
        resp = service.GetOpenInterest(pb.GetOpenInterestRequest(symbol="BTC"))
        ex = resp.data.exchanges[2]
        assert ex.exchange == "OKX"
        assert ex.open_interest_usd == 1800000000.0
        assert ex.open_interest_amount == 27500.0


class TestGetLiquidation:
    def test_returns_records(self, service):
        resp = service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC"))
        assert len(resp.records) == 3

    def test_first_record_fields(self, service):
        resp = service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC"))
        rec = resp.records[0]
        assert rec.timestamp == 1700000000000
        assert rec.long_liquidation_usd == 15000000.0
        assert rec.short_liquidation_usd == 8000000.0
        assert rec.long_count == 1234
        assert rec.short_count == 567

    def test_second_record(self, service):
        resp = service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC"))
        rec = resp.records[1]
        assert rec.timestamp == 1700003600000
        assert rec.long_liquidation_usd == 5000000.0
        assert rec.short_liquidation_usd == 12000000.0
        assert rec.long_count == 456
        assert rec.short_count == 890

    def test_defaults_time_type(self, service, mock_http):
        service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or (call_args[0][1] if len(call_args[0]) > 1 else None)
        if params is None and call_args.kwargs.get("params"):
            params = call_args.kwargs["params"]
        assert params["time_type"] == "all"

    def test_custom_time_type(self, service, mock_http):
        service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC", time_type="1h"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or call_args.kwargs.get("params")
        assert params["time_type"] == "1h"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"code": "0", "msg": "success", "data": []}),
        )
        resp = service.GetLiquidation(pb.GetLiquidationRequest(symbol="BTC"))
        assert len(resp.records) == 0


class TestGetLongShortRatio:
    def test_returns_records(self, service):
        resp = service.GetLongShortRatio(pb.GetLongShortRatioRequest(symbol="BTC"))
        assert len(resp.records) == 3

    def test_first_record_fields(self, service):
        resp = service.GetLongShortRatio(pb.GetLongShortRatioRequest(symbol="BTC"))
        rec = resp.records[0]
        assert rec.timestamp == 1700000000000
        assert rec.long_rate == 0.52
        assert rec.short_rate == 0.48
        assert rec.long_short_ratio == 1.083

    def test_second_record(self, service):
        resp = service.GetLongShortRatio(pb.GetLongShortRatioRequest(symbol="BTC"))
        rec = resp.records[1]
        assert rec.timestamp == 1700003600000
        assert rec.long_rate == 0.55
        assert rec.short_rate == 0.45
        assert rec.long_short_ratio == 1.222

    def test_bearish_ratio(self, service):
        resp = service.GetLongShortRatio(pb.GetLongShortRatioRequest(symbol="BTC"))
        rec = resp.records[2]
        assert rec.long_rate == 0.49
        assert rec.short_rate == 0.51
        assert rec.long_short_ratio == 0.961

    def test_defaults_time_type(self, service, mock_http):
        service.GetLongShortRatio(pb.GetLongShortRatioRequest(symbol="BTC"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or call_args.kwargs.get("params")
        assert params["time_type"] == "all"


class TestGetOIHistory:
    def test_returns_records(self, service):
        resp = service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        assert len(resp.records) == 4

    def test_first_record_fields(self, service):
        resp = service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        rec = resp.records[0]
        assert rec.timestamp == 1700000000000
        assert rec.open_interest_usd == 9500000000.0

    def test_second_record(self, service):
        resp = service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        rec = resp.records[1]
        assert rec.timestamp == 1700003600000
        assert rec.open_interest_usd == 9800000000.0

    def test_oi_decrease(self, service):
        resp = service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        rec = resp.records[2]
        assert rec.open_interest_usd == 9200000000.0

    def test_defaults_time_type(self, service, mock_http):
        service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or call_args.kwargs.get("params")
        assert params["time_type"] == "all"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"code": "0", "msg": "success", "data": []}),
        )
        resp = service.GetOIHistory(pb.GetOIHistoryRequest(symbol="BTC"))
        assert len(resp.records) == 0

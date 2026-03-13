"""Unit tests — every LidoService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from lido_mcp.gen.lido.v1 import lido_pb2 as pb
from tests.conftest import (
    FAKE_APR_LAST,
    FAKE_APR_SMA,
    FAKE_WITHDRAWAL_TIME,
)


class TestGetStETHApr:
    def test_returns_apr(self, service):
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.data.apr == 2.464

    def test_returns_time_unix(self, service):
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.data.time_unix == 1773318119

    def test_meta_symbol(self, service):
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.meta.symbol == "stETH"

    def test_meta_address(self, service):
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.meta.address == "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"

    def test_meta_chain_id(self, service):
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.meta.chain_id == 1

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetStETHApr(pb.GetStETHAprRequest())
        assert resp.data.apr == 0
        assert resp.data.time_unix == 0


class TestGetStETHAprSMA:
    def test_returns_sma_apr(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        assert resp.sma_apr == 2.387125

    def test_returns_aprs_list(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        assert len(resp.aprs) == 8

    def test_first_apr_data_point(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        first = resp.aprs[0]
        assert first.time_unix == 1772713319
        assert first.apr == 2.438

    def test_last_apr_data_point(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        last = resp.aprs[-1]
        assert last.time_unix == 1773318119
        assert last.apr == 2.464

    def test_meta_symbol(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        assert resp.meta.symbol == "stETH"

    def test_meta_chain_id(self, service):
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        assert resp.meta.chain_id == 1

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetStETHAprSMA(pb.GetStETHAprSMARequest())
        assert resp.sma_apr == 0
        assert len(resp.aprs) == 0


class TestGetWithdrawalTime:
    def test_returns_status(self, service):
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.status == "calculated"

    def test_finalization_in(self, service):
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.request_info.finalization_in == 427922000

    def test_finalization_at(self, service):
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.request_info.finalization_at == "2026-03-17T12:30:23.056Z"

    def test_request_type(self, service):
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.request_info.type == "exitValidators"

    def test_next_calculation_at(self, service):
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.next_calculation_at == "2026-03-12T13:40:00.308Z"

    def test_default_amount(self, service):
        """When amount is 0 (proto default), service defaults to 1."""
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest())
        assert resp.status == "calculated"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetWithdrawalTime(pb.GetWithdrawalTimeRequest(amount=32))
        assert resp.status == ""
        assert resp.request_info.finalization_in == 0

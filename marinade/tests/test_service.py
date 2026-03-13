"""Unit tests -- every MarinadeService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from marinade_mcp.gen.marinade.v1 import marinade_pb2 as pb
from tests.conftest import (
    FAKE_STAKE_STATS,
    FAKE_VALIDATORS,
    FAKE_MSOL_PRICE,
)


class TestGetStakeStats:
    def test_returns_apy(self, service):
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.apy == pytest.approx(0.05954983746147113)

    def test_returns_start_time(self, service):
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.start_time == "2026-02-10T16:04:49Z"

    def test_returns_end_time(self, service):
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.end_time == "2026-03-12T16:09:44Z"

    def test_returns_start_price(self, service):
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.start_price == pytest.approx(1.3594920492768106)

    def test_returns_end_price(self, service):
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.end_price == pytest.approx(1.3659716275487495)

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetStakeStats(pb.GetStakeStatsRequest())
        assert resp.apy == 0
        assert resp.start_time == ""
        assert resp.end_time == ""


class TestListValidators:
    def test_returns_validators(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert len(resp.validators) == 2

    def test_first_validator_name(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].info_name == "Helius"

    def test_first_validator_vote_account(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].vote_account == "he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk"

    def test_first_validator_commission(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].commission_advertised == 0

    def test_second_validator_name(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[1].info_name == "Figment"

    def test_second_validator_commission(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[1].commission_advertised == 7

    def test_validator_activated_stake(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].activated_stake == "14590505512992309"

    def test_validator_superminority(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].superminority is True

    def test_validator_dc_city(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].dc_city == "Frankfurt"

    def test_validator_avg_apy(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert resp.validators[0].avg_apy == pytest.approx(0.06186681193216703)

    def test_validator_skip_rate(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        # First completed epoch (938) for Helius has skip_rate 0.0
        assert resp.validators[0].skip_rate == 0.0

    def test_validator_null_url_becomes_empty(self, service):
        resp = service.ListValidators(pb.ListValidatorsRequest())
        # Figment has info_url: None in the mock data
        assert resp.validators[1].info_url == ""

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.ListValidators(pb.ListValidatorsRequest())
        assert len(resp.validators) == 0


class TestGetValidatorInfo:
    def test_returns_validator(self, service):
        resp = service.GetValidatorInfo(
            pb.GetValidatorInfoRequest(vote_account="he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk")
        )
        assert resp.validator.info_name == "Helius"

    def test_returns_vote_account(self, service):
        resp = service.GetValidatorInfo(
            pb.GetValidatorInfoRequest(vote_account="he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk")
        )
        assert resp.validator.vote_account == "he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk"

    def test_returns_version(self, service):
        resp = service.GetValidatorInfo(
            pb.GetValidatorInfoRequest(vote_account="he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk")
        )
        assert resp.validator.version == "3.1.8"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"validators": []}),
        )
        resp = service.GetValidatorInfo(
            pb.GetValidatorInfoRequest(vote_account="nonexistent")
        )
        assert not resp.HasField("validator")


class TestGetMSOLPrice:
    def test_returns_price(self, service):
        resp = service.GetMSOLPrice(pb.GetMSOLPriceRequest())
        assert resp.price_sol == pytest.approx(1.3659716275487495)

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetMSOLPrice(pb.GetMSOLPriceRequest())
        assert resp.price_sol == 0

"""Live integration tests for Marinade API -- hits the real API.

Run with:
    MARINADE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Marinade endpoints.
No API key or authentication is required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("MARINADE_RUN_LIVE_TESTS") != "1",
    reason="Set MARINADE_RUN_LIVE_TESTS=1 to run live Marinade API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from marinade_mcp.service import MarinadeService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-marinade-live", version="0.0.1"
    )
    servicer = MarinadeService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Stake Stats (mSOL APY) ---


class TestLiveStakeStats:
    def test_get_stake_stats(self, live_server):
        result = live_server._cli(["MarinadeService", "GetStakeStats"])
        assert "apy" in result
        assert isinstance(result["apy"], (int, float))
        assert result["apy"] > 0, "APY should be positive"

    def test_get_stake_stats_has_times(self, live_server):
        result = live_server._cli(["MarinadeService", "GetStakeStats"])
        start_key = "startTime" if "startTime" in result else "start_time"
        end_key = "endTime" if "endTime" in result else "end_time"
        assert start_key in result
        assert end_key in result

    def test_get_stake_stats_has_prices(self, live_server):
        result = live_server._cli(["MarinadeService", "GetStakeStats"])
        start_key = "startPrice" if "startPrice" in result else "start_price"
        end_key = "endPrice" if "endPrice" in result else "end_price"
        assert start_key in result
        assert end_key in result
        assert result[start_key] > 0
        assert result[end_key] > 0


# --- List Validators ---


class TestLiveListValidators:
    def test_list_validators(self, live_server):
        result = live_server._cli(
            [
                "MarinadeService",
                "ListValidators",
                "-r",
                json.dumps({"limit": 5, "offset": 0}),
            ]
        )
        assert "validators" in result
        validators = result["validators"]
        assert isinstance(validators, list)
        assert len(validators) > 0, "expected at least one validator"

    def test_validator_has_name(self, live_server):
        result = live_server._cli(
            [
                "MarinadeService",
                "ListValidators",
                "-r",
                json.dumps({"limit": 1}),
            ]
        )
        v = result["validators"][0]
        name_key = "infoName" if "infoName" in v else "info_name"
        assert name_key in v
        assert v[name_key], "expected non-empty validator name"

    def test_validator_has_vote_account(self, live_server):
        result = live_server._cli(
            [
                "MarinadeService",
                "ListValidators",
                "-r",
                json.dumps({"limit": 1}),
            ]
        )
        v = result["validators"][0]
        key = "voteAccount" if "voteAccount" in v else "vote_account"
        assert key in v
        assert v[key], "expected non-empty vote account"


# --- Get Validator Info ---


class TestLiveGetValidatorInfo:
    def test_get_validator_info(self, live_server):
        # First get a valid vote account
        list_result = live_server._cli(
            [
                "MarinadeService",
                "ListValidators",
                "-r",
                json.dumps({"limit": 1}),
            ]
        )
        v = list_result["validators"][0]
        key = "voteAccount" if "voteAccount" in v else "vote_account"
        vote_account = v[key]

        result = live_server._cli(
            [
                "MarinadeService",
                "GetValidatorInfo",
                "-r",
                json.dumps({"vote_account": vote_account}),
            ]
        )
        assert "validator" in result
        validator = result["validator"]
        va_key = "voteAccount" if "voteAccount" in validator else "vote_account"
        assert validator[va_key] == vote_account


# --- mSOL Price ---


class TestLiveGetMSOLPrice:
    def test_get_msol_price(self, live_server):
        result = live_server._cli(["MarinadeService", "GetMSOLPrice"])
        key = "priceSol" if "priceSol" in result else "price_sol"
        assert key in result
        assert isinstance(result[key], (int, float))
        assert result[key] > 1.0, "mSOL should be worth more than 1 SOL"

    def test_msol_price_reasonable(self, live_server):
        result = live_server._cli(["MarinadeService", "GetMSOLPrice"])
        key = "priceSol" if "priceSol" in result else "price_sol"
        price = result[key]
        assert 1.0 < price < 5.0, f"mSOL price {price} seems unreasonable"

"""Live integration tests for Lido API -- hits the real API.

Run with:
    LIDO_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Lido endpoints.
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
    os.getenv("LIDO_RUN_LIVE_TESTS") != "1",
    reason="Set LIDO_RUN_LIVE_TESTS=1 to run live Lido API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from lido_mcp.service import LidoService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-lido-live", version="0.0.1"
    )
    servicer = LidoService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- stETH APR ---


class TestLiveStETHApr:
    def test_get_steth_apr(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHApr"])
        assert "data" in result
        data = result["data"]
        assert "apr" in data
        assert isinstance(data["apr"], (int, float))
        assert data["apr"] > 0, "APR should be positive"

    def test_get_steth_apr_has_meta(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHApr"])
        assert "meta" in result
        meta = result["meta"]
        assert meta.get("symbol") == "stETH"
        assert meta.get("address"), "expected contract address"
        key = "chainId" if "chainId" in meta else "chain_id"
        assert meta.get(key) == 1, "expected Ethereum mainnet (chainId=1)"

    def test_get_steth_apr_has_timestamp(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHApr"])
        data = result["data"]
        key = "timeUnix" if "timeUnix" in data else "time_unix"
        assert key in data
        assert int(data[key]) > 0, "timestamp should be positive"


# --- stETH APR SMA ---


class TestLiveStETHAprSMA:
    def test_get_steth_apr_sma(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHAprSMA"])
        sma_key = "smaApr" if "smaApr" in result else "sma_apr"
        assert sma_key in result
        assert isinstance(result[sma_key], (int, float))
        assert result[sma_key] > 0, "SMA APR should be positive"

    def test_get_steth_apr_sma_has_aprs(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHAprSMA"])
        assert "aprs" in result
        aprs = result["aprs"]
        assert isinstance(aprs, list)
        assert len(aprs) > 0, "expected at least one APR data point"
        first = aprs[0]
        assert "apr" in first
        assert isinstance(first["apr"], (int, float))

    def test_get_steth_apr_sma_has_meta(self, live_server):
        result = live_server._cli(["LidoService", "GetStETHAprSMA"])
        assert "meta" in result
        meta = result["meta"]
        assert meta.get("symbol") == "stETH"


# --- Withdrawal Time ---


class TestLiveWithdrawalTime:
    def test_get_withdrawal_time(self, live_server):
        result = live_server._cli(
            [
                "LidoService",
                "GetWithdrawalTime",
                "-r",
                json.dumps({"amount": 32}),
            ]
        )
        assert "status" in result
        assert result["status"] in ("calculated", "pending")

    def test_get_withdrawal_time_has_request_info(self, live_server):
        result = live_server._cli(
            [
                "LidoService",
                "GetWithdrawalTime",
                "-r",
                json.dumps({"amount": 1}),
            ]
        )
        key = "requestInfo" if "requestInfo" in result else "request_info"
        assert key in result
        info = result[key]
        fin_at_key = "finalizationAt" if "finalizationAt" in info else "finalization_at"
        assert fin_at_key in info, "expected finalizationAt timestamp"

    def test_get_withdrawal_time_small_amount(self, live_server):
        result = live_server._cli(
            [
                "LidoService",
                "GetWithdrawalTime",
                "-r",
                json.dumps({"amount": 0.1}),
            ]
        )
        assert "status" in result

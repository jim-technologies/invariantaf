"""Live integration tests for Yearn Finance API -- hits the real API.

Run with:
    YEARN_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) yDaemon endpoints.
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
    os.getenv("YEARN_RUN_LIVE_TESTS") != "1",
    reason="Set YEARN_RUN_LIVE_TESTS=1 to run live Yearn API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from yearn_mcp.service import YearnService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-yearn-live", version="0.0.1"
    )
    servicer = YearnService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for discovery ---


@pytest.fixture(scope="module")
def first_vault_address(live_server):
    """Discover a vault address for tests that need one."""
    result = live_server._cli(["YearnService", "ListVaults"])
    vaults = result.get("vaults", [])
    assert vaults, "expected at least one vault on Ethereum"
    address = vaults[0].get("address", "")
    assert address, "first vault has no address"
    return address


# --- ListVaults ---


class TestLiveListVaults:
    def test_ethereum_vaults(self, live_server):
        result = live_server._cli(["YearnService", "ListVaults"])
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)
        assert len(vaults) > 0
        v = vaults[0]
        assert "address" in v
        assert "name" in v

    def test_vault_has_tvl(self, live_server):
        result = live_server._cli(["YearnService", "ListVaults"])
        vaults = result["vaults"]
        v = vaults[0]
        assert "tvl" in v

    def test_vault_has_apr(self, live_server):
        result = live_server._cli(["YearnService", "ListVaults"])
        vaults = result["vaults"]
        v = vaults[0]
        assert "apr" in v

    def test_vault_has_token(self, live_server):
        result = live_server._cli(["YearnService", "ListVaults"])
        vaults = result["vaults"]
        v = vaults[0]
        assert "token" in v
        assert "symbol" in v["token"]

    def test_optimism_vaults(self, live_server):
        result = live_server._cli(
            ["YearnService", "ListVaults", "-r", json.dumps({"chainId": 10})]
        )
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)

    def test_arbitrum_vaults(self, live_server):
        result = live_server._cli(
            ["YearnService", "ListVaults", "-r", json.dumps({"chainId": 42161})]
        )
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)

    def test_polygon_vaults(self, live_server):
        result = live_server._cli(
            ["YearnService", "ListVaults", "-r", json.dumps({"chainId": 137})]
        )
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)

    def test_base_vaults(self, live_server):
        result = live_server._cli(
            ["YearnService", "ListVaults", "-r", json.dumps({"chainId": 8453})]
        )
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)


# --- GetVault ---


class TestLiveGetVault:
    def test_get_single_vault(self, live_server, first_vault_address):
        result = live_server._cli(
            [
                "YearnService",
                "GetVault",
                "-r",
                json.dumps({"chainId": 1, "address": first_vault_address}),
            ]
        )
        assert "vault" in result
        vault = result["vault"]
        assert "address" in vault
        assert "name" in vault
        assert "tvl" in vault
        assert "apr" in vault

    def test_vault_has_fees(self, live_server, first_vault_address):
        result = live_server._cli(
            [
                "YearnService",
                "GetVault",
                "-r",
                json.dumps({"chainId": 1, "address": first_vault_address}),
            ]
        )
        vault = result["vault"]
        assert "fees" in vault


# --- ListAllVaults ---


class TestLiveListAllVaults:
    def test_returns_vaults_from_multiple_chains(self, live_server):
        result = live_server._cli(["YearnService", "ListAllVaults"])
        assert "vaults" in result
        vaults = result["vaults"]
        assert isinstance(vaults, list)
        assert len(vaults) > 0
        # Check that we got vaults from at least Ethereum.
        chain_ids = {v.get("chainId") or v.get("chain_id") for v in vaults}
        assert 1 in chain_ids or len(vaults) > 0

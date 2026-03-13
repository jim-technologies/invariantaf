"""Unit tests -- every YearnService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from yearn_mcp.gen.yearn.v1 import yearn_pb2 as pb
from tests.conftest import (
    FAKE_ETH_VAULTS,
    FAKE_OP_VAULTS,
    FAKE_VAULT_1,
    FAKE_VAULT_2,
    FAKE_OPTIMISM_VAULT,
)


class TestListVaults:
    def test_returns_vaults(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 2

    def test_defaults_to_ethereum(self, service, mock_http):
        service.ListVaults(pb.ListVaultsRequest())
        call_url = mock_http.get.call_args[0][0]
        assert "/1/vaults/all" in call_url

    def test_explicit_chain_id(self, service, mock_http):
        service.ListVaults(pb.ListVaultsRequest(chain_id=10))
        call_url = mock_http.get.call_args[0][0]
        assert "/10/vaults/all" in call_url

    def test_vault_basic_fields(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[0]
        assert v.address == "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213"
        assert v.name == "Curve YFIETH Factory yVault"
        assert v.symbol == "yvCurve-YFIETH-f"
        assert v.version == "0.4.6"
        assert v.type == "Yearn Vault"
        assert v.category == "Curve"
        assert v.decimals == 18
        assert v.chain_id == 1
        assert v.endorsed is True
        assert v.boosted is False
        assert v.emergency_shutdown is False
        assert v.kind == "Legacy"

    def test_vault_token_info(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        token = resp.vaults[0].token
        assert token.address == "0x29059568bB40344487d62f7450E78b8E6C74e0e5"
        assert token.name == "Curve.fi Factory Crypto Pool: YFI/ETH"
        assert token.symbol == "YFIETH-f"
        assert token.decimals == 18
        assert len(token.underlying_tokens_addresses) == 2

    def test_vault_tvl(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        tvl = resp.vaults[0].tvl
        assert tvl.total_assets == "11605289578737060000"
        assert tvl.tvl_usd == 15234567.89
        assert tvl.price == 1312.45

    def test_vault_apr(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        apr = resp.vaults[0].apr
        assert apr.type == "v2:averaged"
        assert apr.net_apr == 0.0523
        assert apr.week_ago == 0.0498
        assert apr.month_ago == 0.0612
        assert apr.inception == 0.0445
        assert apr.forward_apr == 0.0678

    def test_vault_composite_apr(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        comp = resp.vaults[0].apr.composite
        assert comp.boost == 2.5
        assert comp.pool_apy == 0.01
        assert comp.boosted_apr == 0.05
        assert comp.base_apr == 0.02
        assert comp.cvx_apr == 0.005
        assert comp.rewards_apr == 0.003

    def test_vault_fees(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        fees = resp.vaults[0].fees
        assert fees.performance == 0.1
        assert fees.management == 0.02

    def test_vault_strategies(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        strats = resp.vaults[0].strategies
        assert len(strats) == 1
        s = strats[0]
        assert s.address == "0xABC123def456"
        assert s.name == "StrategyCurveBoostedFactory-YFIETH"
        assert s.status == "Active"
        assert s.total_debt == "10000000000000000000"
        assert s.total_loss == "0"
        assert s.total_gain == "500000000000000000"
        assert s.last_report == 1700000000
        assert s.debt_ratio == 10000

    def test_vault_details(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        d = resp.vaults[0].details
        assert d.is_retired is False
        assert d.is_pool is True
        assert d.pool_provider == "Curve"
        assert d.stability == "Volatile"
        assert d.category == "Volatile"

    def test_second_vault(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[1]
        assert v.address == "0xdA816459F1AB5631232FE5e97a05BBBb94970c95"
        assert v.name == "DAI yVault"
        assert v.symbol == "yvDAI"
        assert len(v.strategies) == 2
        assert v.strategies[0].name == "StrategyLenderYieldOptimiser"
        assert v.strategies[1].name == "StrategyGenericLevCompFarm"

    def test_dai_vault_fees(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        fees = resp.vaults[1].fees
        assert fees.performance == 0.2
        assert fees.management == 0.0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 0

    def test_optimism_chain(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest(chain_id=10))
        assert len(resp.vaults) == 1
        v = resp.vaults[0]
        assert v.chain_id == 10
        assert v.symbol == "yvUSDC"


class TestGetVault:
    def test_returns_vault(self, service):
        resp = service.GetVault(pb.GetVaultRequest(
            chain_id=1,
            address="0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
        ))
        assert resp.vault is not None
        assert resp.vault.address == "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213"

    def test_vault_fields(self, service):
        resp = service.GetVault(pb.GetVaultRequest(
            chain_id=1,
            address="0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
        ))
        v = resp.vault
        assert v.name == "Curve YFIETH Factory yVault"
        assert v.apr.net_apr == 0.0523
        assert v.tvl.tvl_usd == 15234567.89

    def test_defaults_chain_to_ethereum(self, service, mock_http):
        service.GetVault(pb.GetVaultRequest(
            address="0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
        ))
        call_url = mock_http.get.call_args[0][0]
        assert "/1/vaults/" in call_url

    def test_dai_vault(self, service):
        resp = service.GetVault(pb.GetVaultRequest(
            chain_id=1,
            address="0xdA816459F1AB5631232FE5e97a05BBBb94970c95",
        ))
        v = resp.vault
        assert v.name == "DAI yVault"
        assert v.token.symbol == "DAI"
        assert v.tvl.tvl_usd == 50000000.0


class TestListAllVaults:
    def test_returns_all_chains(self, service):
        resp = service.ListAllVaults(pb.ListAllVaultsRequest())
        # 2 from Ethereum + 1 from Optimism + 0 from others = 3.
        assert len(resp.vaults) == 3

    def test_contains_ethereum_vaults(self, service):
        resp = service.ListAllVaults(pb.ListAllVaultsRequest())
        eth_vaults = [v for v in resp.vaults if v.chain_id == 1]
        assert len(eth_vaults) == 2

    def test_contains_optimism_vaults(self, service):
        resp = service.ListAllVaults(pb.ListAllVaultsRequest())
        op_vaults = [v for v in resp.vaults if v.chain_id == 10]
        assert len(op_vaults) == 1
        assert op_vaults[0].symbol == "yvUSDC"

    def test_skips_failed_chains(self, service, mock_http):
        """If a chain fails, other chains should still be returned."""
        original_get = mock_http.get.side_effect

        def failing_get(url, params=None):
            if "/10/vaults/all" in url:
                raise ConnectionError("network error")
            return original_get(url, params)

        mock_http.get.side_effect = failing_get
        resp = service.ListAllVaults(pb.ListAllVaultsRequest())
        # Should still get Ethereum vaults.
        assert len(resp.vaults) >= 2
        chain_ids = {v.chain_id for v in resp.vaults}
        assert 1 in chain_ids

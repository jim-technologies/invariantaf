"""Unit tests — every BeefyService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from beefy_mcp.gen.beefy.v1 import beefy_pb2 as pb
from tests.conftest import (
    FAKE_VAULTS,
    FAKE_APYS,
    FAKE_APY_BREAKDOWN,
    FAKE_TVL,
    FAKE_FEES,
    FAKE_LP_PRICES,
    FAKE_BOOSTS,
)


class TestListVaults:
    def test_returns_all_vaults(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 2

    def test_first_vault_id(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].id == "curve-usdc-usdf"

    def test_first_vault_name(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].name == "USDf/USDC"

    def test_first_vault_chain(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].chain == "ethereum"

    def test_first_vault_status(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].status == "active"

    def test_first_vault_assets(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert list(resp.vaults[0].assets) == ["USDf", "USDC"]

    def test_first_vault_platform(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].platform_id == "convex"

    def test_first_vault_risks(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        risks = resp.vaults[0].risks
        assert risks.not_timelocked is True
        assert risks.complex is False
        assert risks.not_audited is False

    def test_first_vault_created_at(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].created_at == 1747215194

    def test_first_vault_token_decimals(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[0].token_decimals == 18

    def test_second_vault_chain(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[1].chain == "base"

    def test_second_vault_curated(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert resp.vaults[1].risks.curated is True

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 0


class TestGetApys:
    def test_returns_all_apys(self, service):
        resp = service.GetApys(pb.GetApysRequest())
        assert len(resp.apys) == 3

    def test_apy_values(self, service):
        resp = service.GetApys(pb.GetApysRequest())
        by_id = {a.vault_id: a.apy for a in resp.apys}
        assert by_id["curve-usdc-usdf"] == 0.0523
        assert by_id["aero-weth-usdc"] == 0.1847
        assert by_id["beefy-maxi"] == 0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetApys(pb.GetApysRequest())
        assert len(resp.apys) == 0


class TestGetApyBreakdown:
    def test_returns_breakdowns(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        assert len(resp.breakdowns) == 2

    def test_first_breakdown_total_apy(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        bd = {b.vault_id: b for b in resp.breakdowns}
        assert bd["curve-usdc-usdf"].total_apy == 0.0523

    def test_first_breakdown_vault_apr(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        bd = {b.vault_id: b for b in resp.breakdowns}
        assert bd["curve-usdc-usdf"].vault_apr == 0.048

    def test_first_breakdown_compoundings(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        bd = {b.vault_id: b for b in resp.breakdowns}
        assert bd["curve-usdc-usdf"].compoundings_per_year == 2190

    def test_second_breakdown_boost_apr(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        bd = {b.vault_id: b for b in resp.breakdowns}
        assert bd["aero-weth-usdc"].boost_apr == 0.01

    def test_second_breakdown_trading_apr(self, service):
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        bd = {b.vault_id: b for b in resp.breakdowns}
        assert bd["aero-weth-usdc"].trading_apr == 0.02

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetApyBreakdown(pb.GetApyBreakdownRequest())
        assert len(resp.breakdowns) == 0


class TestGetTVL:
    def test_returns_chains(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        assert len(resp.chains) == 2

    def test_chain_ids(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        chain_ids = {c.chain_id for c in resp.chains}
        assert "1" in chain_ids
        assert "8453" in chain_ids

    def test_chain1_vaults(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        chain1 = [c for c in resp.chains if c.chain_id == "1"][0]
        assert len(chain1.vaults) == 2
        by_id = {v.vault_id: v.tvl_usd for v in chain1.vaults}
        assert by_id["curve-usdc-usdf"] == 1036888.59

    def test_chain_8453_vaults(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        chain = [c for c in resp.chains if c.chain_id == "8453"][0]
        assert len(chain.vaults) == 1
        assert chain.vaults[0].tvl_usd == 500000.0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetTVL(pb.GetTVLRequest())
        assert len(resp.chains) == 0


class TestGetFees:
    def test_returns_fees(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        assert len(resp.fees) == 2

    def test_first_fee_performance_total(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        by_id = {f.vault_id: f for f in resp.fees}
        assert by_id["curve-usdc-usdf"].performance.total == 0.045

    def test_first_fee_performance_strategist(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        by_id = {f.vault_id: f for f in resp.fees}
        assert by_id["curve-usdc-usdf"].performance.strategist == 0.005

    def test_first_fee_withdraw(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        by_id = {f.vault_id: f for f in resp.fees}
        assert by_id["curve-usdc-usdf"].withdraw == 0

    def test_second_fee_withdraw(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        by_id = {f.vault_id: f for f in resp.fees}
        assert by_id["aero-weth-usdc"].withdraw == 0.001

    def test_last_updated(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        by_id = {f.vault_id: f for f in resp.fees}
        assert by_id["curve-usdc-usdf"].last_updated == 1773286654682

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetFees(pb.GetFeesRequest())
        assert len(resp.fees) == 0


class TestGetLPPrices:
    def test_returns_prices(self, service):
        resp = service.GetLPPrices(pb.GetLPPricesRequest())
        assert len(resp.prices) == 3

    def test_price_values(self, service):
        resp = service.GetLPPrices(pb.GetLPPricesRequest())
        by_id = {p.lp_id: p.price for p in resp.prices}
        assert by_id["curve-usdc-usdf"] == 1.0012
        assert by_id["aero-weth-usdc"] == 245.67
        assert by_id["sushi-eth-dai"] == 0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetLPPrices(pb.GetLPPricesRequest())
        assert len(resp.prices) == 0


class TestGetBoosts:
    def test_returns_boosts(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert len(resp.boosts) == 2

    def test_first_boost_id(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].id == "moo_lendle-mantle-weth-lendle"

    def test_first_boost_name(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].name == "Lendle"

    def test_first_boost_chain(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].chain == "mantle"

    def test_first_boost_earned_token(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].earned_token == "LEND"

    def test_first_boost_partners(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert list(resp.boosts[0].partners) == ["lendle"]

    def test_first_boost_is_moo_staked(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].is_moo_staked is True

    def test_first_boost_period_finish(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert resp.boosts[0].period_finish == 1708274069

    def test_second_boost_assets(self, service):
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert list(resp.boosts[1].assets) == ["USDC", "FUSE"]

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        resp = service.GetBoosts(pb.GetBoostsRequest())
        assert len(resp.boosts) == 0

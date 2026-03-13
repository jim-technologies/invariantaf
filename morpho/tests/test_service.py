"""Unit tests -- every MorphoService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from morpho_mcp.gen.morpho.v1 import morpho_pb2 as pb


class TestListMarkets:
    def test_returns_markets(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        assert len(resp.markets) == 2

    def test_first_market_unique_key(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[0]
        assert m.unique_key == "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"

    def test_loan_asset(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[0]
        assert m.loan_asset.symbol == "USDC"
        assert m.loan_asset.decimals == 6
        assert m.loan_asset.address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def test_collateral_asset(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[0]
        assert m.collateral_asset.symbol == "WETH"
        assert m.collateral_asset.decimals == 18

    def test_chain(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[0]
        assert m.chain.id == 1
        assert m.chain.network == "Ethereum"

    def test_lltv(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[0]
        assert m.lltv == "860000000000000000"

    def test_market_state_apys(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        st = resp.markets[0].state
        assert st.supply_apy == 0.035
        assert st.borrow_apy == 0.045
        assert st.net_supply_apy == 0.038
        assert st.net_borrow_apy == 0.042

    def test_market_state_usd_amounts(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        st = resp.markets[0].state
        assert st.supply_assets_usd == 150000000.0
        assert st.borrow_assets_usd == 120000000.0
        assert st.liquidity_assets_usd == 30000000.0
        assert st.collateral_assets_usd == 200000000.0

    def test_market_state_utilization(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        st = resp.markets[0].state
        assert st.utilization == 0.80

    def test_market_rewards(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        rewards = resp.markets[0].state.rewards
        assert len(rewards) == 1
        assert rewards[0].supply_apr == 0.01
        assert rewards[0].borrow_apr == 0.005
        assert rewards[0].asset.symbol == "MORPHO"

    def test_second_market(self, service):
        resp = service.ListMarkets(pb.ListMarketsRequest())
        m = resp.markets[1]
        assert m.loan_asset.symbol == "DAI"
        assert m.collateral_asset.symbol == "wstETH"
        assert len(m.state.rewards) == 0

    def test_pagination_params(self, service, mock_http):
        service.ListMarkets(pb.ListMarketsRequest(first=5, skip=10))
        call_args = mock_http.post.call_args
        variables = call_args[1]["json"]["variables"] if "json" in call_args[1] else call_args[0][1]["variables"]
        assert variables["first"] == 5
        assert variables["skip"] == 10

    def test_first_capped_at_100(self, service, mock_http):
        service.ListMarkets(pb.ListMarketsRequest(first=200))
        call_args = mock_http.post.call_args
        variables = call_args[1]["json"]["variables"] if "json" in call_args[1] else call_args[0][1]["variables"]
        assert variables["first"] == 100

    def test_empty_response(self, service, mock_http):
        mock_http.post.side_effect = lambda url, json=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"data": {"markets": {"items": []}}}),
        )
        resp = service.ListMarkets(pb.ListMarketsRequest())
        assert len(resp.markets) == 0


class TestGetMarket:
    def test_returns_market(self, service):
        resp = service.GetMarket(
            pb.GetMarketRequest(unique_key="0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc")
        )
        assert resp.market.unique_key == "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"

    def test_market_loan_asset(self, service):
        resp = service.GetMarket(
            pb.GetMarketRequest(unique_key="0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc")
        )
        assert resp.market.loan_asset.symbol == "USDC"

    def test_market_state(self, service):
        resp = service.GetMarket(
            pb.GetMarketRequest(unique_key="0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc")
        )
        st = resp.market.state
        assert st.supply_apy == 0.035
        assert st.borrow_apy == 0.045

    def test_missing_unique_key_raises(self, service):
        with pytest.raises(ValueError, match="unique_key is required"):
            service.GetMarket(pb.GetMarketRequest())

    def test_chain_id_passed(self, service, mock_http):
        service.GetMarket(pb.GetMarketRequest(unique_key="0xabc", chain_id=1))
        call_args = mock_http.post.call_args
        variables = call_args[1]["json"]["variables"] if "json" in call_args[1] else call_args[0][1]["variables"]
        assert variables["chainId"] == 1


class TestListVaults:
    def test_returns_vaults(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 2

    def test_first_vault_fields(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[0]
        assert v.address == "0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076"
        assert v.name == "Steakhouse Prime USDC"
        assert v.symbol == "steakUSDC"

    def test_vault_asset(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[0]
        assert v.asset.symbol == "USDC"
        assert v.asset.decimals == 6

    def test_vault_chain(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[0]
        assert v.chain.id == 1
        assert v.chain.network == "Ethereum"

    def test_vault_state(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        st = resp.vaults[0].state
        assert st.apy == 0.055
        assert st.net_apy == 0.05
        assert st.total_assets_usd == 250000000.0
        assert st.total_assets == "250000000000000"
        assert st.total_supply == "240000000000000"
        assert st.fee == 0.10

    def test_vault_rewards(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        rewards = resp.vaults[0].state.rewards
        assert len(rewards) == 1
        assert rewards[0].supply_apr == 0.008
        assert rewards[0].asset.symbol == "MORPHO"

    def test_second_vault(self, service):
        resp = service.ListVaults(pb.ListVaultsRequest())
        v = resp.vaults[1]
        assert v.name == "Gauntlet WETH Prime"
        assert v.asset.symbol == "WETH"
        assert len(v.state.rewards) == 0

    def test_empty_response(self, service, mock_http):
        mock_http.post.side_effect = lambda url, json=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"data": {"vaults": {"items": []}}}),
        )
        resp = service.ListVaults(pb.ListVaultsRequest())
        assert len(resp.vaults) == 0


class TestGetVault:
    def test_returns_vault(self, service):
        resp = service.GetVault(
            pb.GetVaultRequest(address="0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076")
        )
        assert resp.vault.address == "0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076"
        assert resp.vault.name == "Steakhouse Prime USDC"

    def test_vault_state(self, service):
        resp = service.GetVault(
            pb.GetVaultRequest(address="0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076")
        )
        assert resp.vault.state.apy == 0.055

    def test_missing_address_raises(self, service):
        with pytest.raises(ValueError, match="address is required"):
            service.GetVault(pb.GetVaultRequest())

    def test_chain_id_passed(self, service, mock_http):
        service.GetVault(pb.GetVaultRequest(address="0xBEEF", chain_id=8453))
        call_args = mock_http.post.call_args
        variables = call_args[1]["json"]["variables"] if "json" in call_args[1] else call_args[0][1]["variables"]
        assert variables["chainId"] == 8453


class TestListMarketPositions:
    def test_returns_positions(self, service):
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        )
        assert len(resp.positions) == 1

    def test_position_health_factor(self, service):
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        )
        pos = resp.positions[0]
        assert pos.health_factor == 1.85

    def test_position_user_address(self, service):
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        )
        pos = resp.positions[0]
        assert pos.user_address == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    def test_position_market(self, service):
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        )
        pos = resp.positions[0]
        assert pos.market.loan_asset.symbol == "USDC"
        assert pos.market.collateral_asset.symbol == "WETH"

    def test_position_state(self, service):
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        )
        st = resp.positions[0].state
        assert st.supply_assets == "50000000000"
        assert st.supply_assets_usd == 50000.0
        assert st.borrow_assets == "30000000000"
        assert st.borrow_assets_usd == 30000.0
        assert st.collateral == "20000000000000000000"
        assert st.collateral_usd == 60000.0

    def test_missing_user_address_raises(self, service):
        with pytest.raises(ValueError, match="user_address is required"):
            service.ListMarketPositions(pb.ListMarketPositionsRequest())

    def test_empty_response(self, service, mock_http):
        mock_http.post.side_effect = lambda url, json=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"data": {"marketPositions": {"items": []}}}),
        )
        resp = service.ListMarketPositions(
            pb.ListMarketPositionsRequest(user_address="0xdead")
        )
        assert len(resp.positions) == 0

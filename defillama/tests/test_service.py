"""Unit tests — every DefiLlamaService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from defillama_mcp.gen.defillama.v1 import defillama_pb2 as pb
from tests.conftest import (
    FAKE_CHAINS,
    FAKE_DEX_VOLUMES,
    FAKE_FEES,
    FAKE_GLOBAL_TVL,
    FAKE_PROTOCOL_DETAIL,
    FAKE_PROTOCOLS,
    FAKE_STABLECOIN_CHAINS,
    FAKE_STABLECOINS,
    FAKE_TVL,
    FAKE_YIELD_POOLS,
)


class TestGetProtocols:
    def test_returns_protocols(self, service):
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        assert len(resp.protocols) == 2

    def test_aave_fields(self, service):
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        aave = resp.protocols[0]
        assert aave.name == "Aave"
        assert aave.symbol == "AAVE"
        assert aave.category == "Lending"
        assert aave.tvl == 26000000000
        assert aave.slug == "aave"
        assert "Ethereum" in aave.chains

    def test_lido_fields(self, service):
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        lido = resp.protocols[1]
        assert lido.name == "Lido"
        assert lido.slug == "lido"
        assert lido.category == "Liquid Staking"
        assert lido.tvl == 18000000000

    def test_change_fields(self, service):
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        aave = resp.protocols[0]
        assert aave.change_1h == 0.1
        assert aave.change_1d == 1.5
        assert aave.change_7d == 5.2

    def test_mcap(self, service):
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        assert resp.protocols[0].mcap == 4500000000
        assert resp.protocols[1].mcap == 2000000000

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        resp = service.GetProtocols(pb.GetProtocolsRequest())
        assert len(resp.protocols) == 0


class TestGetProtocol:
    def test_basic_fields(self, service):
        resp = service.GetProtocol(pb.GetProtocolRequest(slug="aave"))
        p = resp.protocol
        assert p.name == "Aave"
        assert p.symbol == "AAVE"
        assert p.gecko_id == "aave"
        assert p.twitter == "AaveAave"
        assert p.category == "Lending"

    def test_chains(self, service):
        resp = service.GetProtocol(pb.GetProtocolRequest(slug="aave"))
        p = resp.protocol
        assert "Ethereum" in p.chains
        assert "Polygon" in p.chains
        assert "Avalanche" in p.chains

    def test_tvl_history(self, service):
        resp = service.GetProtocol(pb.GetProtocolRequest(slug="aave"))
        p = resp.protocol
        assert len(p.tvl) == 3
        assert p.tvl[0].date == 1589932800
        assert p.tvl[0].total_liquidity_usd == 54026260
        assert p.tvl[2].total_liquidity_usd == 56000000

    def test_current_chain_tvls(self, service):
        resp = service.GetProtocol(pb.GetProtocolRequest(slug="aave"))
        p = resp.protocol
        assert p.current_chain_tvls["Ethereum"] == 20000000000
        assert p.current_chain_tvls["Polygon"] == 3000000000

    def test_mcap(self, service):
        resp = service.GetProtocol(pb.GetProtocolRequest(slug="aave"))
        assert resp.protocol.mcap == 4500000000


class TestGetTVL:
    def test_returns_tvl(self, service):
        resp = service.GetTVL(pb.GetTVLRequest(slug="aave"))
        assert resp.tvl == 26446474028


class TestGetChains:
    def test_returns_chains(self, service):
        resp = service.GetChains(pb.GetChainsRequest())
        assert len(resp.chains) == 2

    def test_ethereum_chain(self, service):
        resp = service.GetChains(pb.GetChainsRequest())
        eth = resp.chains[0]
        assert eth.name == "Ethereum"
        assert eth.tvl == 60000000000
        assert eth.token_symbol == "ETH"
        assert eth.gecko_id == "ethereum"
        assert eth.chain_id == 1

    def test_bsc_chain(self, service):
        resp = service.GetChains(pb.GetChainsRequest())
        bsc = resp.chains[1]
        assert bsc.name == "BSC"
        assert bsc.tvl == 5000000000
        assert bsc.token_symbol == "BNB"
        assert bsc.chain_id == 56


class TestGetGlobalTVL:
    def test_returns_data_points(self, service):
        resp = service.GetGlobalTVL(pb.GetGlobalTVLRequest())
        assert len(resp.data_points) == 3

    def test_data_point_fields(self, service):
        resp = service.GetGlobalTVL(pb.GetGlobalTVLRequest())
        dp = resp.data_points[0]
        assert dp.date == 1506470400
        assert dp.tvl == 0

    def test_last_data_point(self, service):
        resp = service.GetGlobalTVL(pb.GetGlobalTVLRequest())
        dp = resp.data_points[2]
        assert dp.date == 1506643200
        assert dp.tvl == 250000


class TestGetStablecoins:
    def test_returns_stablecoins(self, service):
        resp = service.GetStablecoins(pb.GetStablecoinsRequest())
        assert len(resp.stablecoins) == 2

    def test_tether_fields(self, service):
        resp = service.GetStablecoins(pb.GetStablecoinsRequest())
        usdt = resp.stablecoins[0]
        assert usdt.name == "Tether"
        assert usdt.symbol == "USDT"
        assert usdt.gecko_id == "tether"
        assert usdt.peg_type == "peggedUSD"
        assert usdt.peg_mechanism == "fiat-backed"
        assert usdt.circulating == 183620774070.14

    def test_usdc_fields(self, service):
        resp = service.GetStablecoins(pb.GetStablecoinsRequest())
        usdc = resp.stablecoins[1]
        assert usdc.name == "USD Coin"
        assert usdc.symbol == "USDC"
        assert usdc.circulating == 45000000000

    def test_historical_circulating(self, service):
        resp = service.GetStablecoins(pb.GetStablecoinsRequest())
        usdt = resp.stablecoins[0]
        assert usdt.circulating_prev_day == 183458165919.49
        assert usdt.circulating_prev_week == 183576475732.69
        assert usdt.circulating_prev_month == 185318552614.40


class TestGetYieldPools:
    def test_returns_pools(self, service):
        resp = service.GetYieldPools(pb.GetYieldPoolsRequest())
        assert len(resp.pools) == 2

    def test_lido_pool(self, service):
        resp = service.GetYieldPools(pb.GetYieldPoolsRequest())
        pool = resp.pools[0]
        assert pool.chain == "Ethereum"
        assert pool.project == "lido"
        assert pool.symbol == "STETH"
        assert pool.tvl_usd == 18312039691
        assert pool.apy == 2.501
        assert pool.apy_base == 2.501
        assert pool.stablecoin is False
        assert pool.il_risk == "no"
        assert pool.exposure == "single"

    def test_aave_pool(self, service):
        resp = service.GetYieldPools(pb.GetYieldPoolsRequest())
        pool = resp.pools[1]
        assert pool.project == "aave-v3"
        assert pool.symbol == "USDC"
        assert pool.apy == 4.0
        assert pool.apy_base == 3.5
        assert pool.apy_reward == 0.5
        assert pool.stablecoin is True

    def test_apy_changes(self, service):
        resp = service.GetYieldPools(pb.GetYieldPoolsRequest())
        pool = resp.pools[0]
        assert pool.apy_pct_1d == 0.122
        assert pool.apy_pct_7d == 0.134
        assert pool.apy_pct_30d == -1.116

    def test_predictions(self, service):
        resp = service.GetYieldPools(pb.GetYieldPoolsRequest())
        pool = resp.pools[0]
        assert pool.predicted_class == "Stable/Up"
        assert pool.predicted_probability == 73


class TestGetDexVolumes:
    def test_aggregate_fields(self, service):
        resp = service.GetDexVolumes(pb.GetDexVolumesRequest())
        assert resp.total_24h == 9702385010
        assert resp.total_7d == 59826406024
        assert resp.total_30d == 200000000000

    def test_change_fields(self, service):
        resp = service.GetDexVolumes(pb.GetDexVolumesRequest())
        assert resp.change_1d == 17.74
        assert resp.change_7d == 5.2
        assert resp.change_1m == -10.3

    def test_all_chains(self, service):
        resp = service.GetDexVolumes(pb.GetDexVolumesRequest())
        assert "Ethereum" in resp.all_chains
        assert "Solana" in resp.all_chains
        assert len(resp.all_chains) == 5

    def test_protocols(self, service):
        resp = service.GetDexVolumes(pb.GetDexVolumesRequest())
        assert len(resp.protocols) == 2
        uni = resp.protocols[0]
        assert uni.name == "Uniswap"
        assert uni.slug == "uniswap"
        assert uni.total_24h == 3000000000
        assert uni.change_1d == 10.5
        assert "Ethereum" in uni.chains

    def test_raydium(self, service):
        resp = service.GetDexVolumes(pb.GetDexVolumesRequest())
        ray = resp.protocols[1]
        assert ray.name == "Raydium"
        assert ray.total_24h == 2000000000
        assert "Solana" in ray.chains


class TestGetFees:
    def test_aggregate_fields(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        assert resp.total_24h == 50000000
        assert resp.total_7d == 350000000
        assert resp.total_30d == 1500000000

    def test_change_fields(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        assert resp.change_1d == 5.5
        assert resp.change_7d == -2.3
        assert resp.change_1m == 12.0

    def test_protocols(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        assert len(resp.protocols) == 2
        eth = resp.protocols[0]
        assert eth.name == "Ethereum"
        assert eth.slug == "ethereum"
        assert eth.total_24h == 20000000

    def test_lido_fees(self, service):
        resp = service.GetFees(pb.GetFeesRequest())
        lido = resp.protocols[1]
        assert lido.name == "Lido"
        assert lido.total_24h == 5000000
        assert lido.category == "Liquid Staking"


class TestGetStablecoinChains:
    def test_returns_chains(self, service):
        resp = service.GetStablecoinChains(pb.GetStablecoinChainsRequest())
        assert len(resp.chains) == 3

    def test_ethereum_chain(self, service):
        resp = service.GetStablecoinChains(pb.GetStablecoinChainsRequest())
        eth = resp.chains[0]
        assert eth.name == "Ethereum"
        assert eth.gecko_id == "ethereum"
        assert eth.token_symbol == "ETH"
        assert eth.total_circulating_usd == 100000000000

    def test_tron_chain(self, service):
        resp = service.GetStablecoinChains(pb.GetStablecoinChainsRequest())
        tron = resp.chains[1]
        assert tron.name == "Tron"
        assert tron.total_circulating_usd == 60000000000

    def test_bsc_chain(self, service):
        resp = service.GetStablecoinChains(pb.GetStablecoinChainsRequest())
        bsc = resp.chains[2]
        assert bsc.name == "BSC"
        assert bsc.total_circulating_usd == 8000000000

"""Unit tests — every CurveService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from curve_mcp.gen.curve.v1 import curve_pb2 as pb
from tests.conftest import (
    FAKE_ETH_PRICE,
    FAKE_FACTORY_TVL,
    FAKE_POOLS,
    FAKE_SUBGRAPH_DATA,
    FAKE_VOLUMES,
    FAKE_WEEKLY_FEES,
)


class TestGetPools:
    def test_returns_pools(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        assert len(resp.pools) == 2

    def test_3pool_fields(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[0]
        assert pool.name == "Curve.fi DAI/USDC/USDT"
        assert pool.symbol == "3Crv"
        assert pool.asset_type_name == "usd"
        assert pool.address == "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
        assert pool.usd_total == 162456848.37
        assert pool.is_meta_pool is False
        assert pool.amplification_coefficient == "4000"
        assert pool.is_broken is False

    def test_3pool_coins(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[0]
        assert len(pool.coins) == 3
        dai = pool.coins[0]
        assert dai.symbol == "DAI"
        assert dai.name == "Dai Stablecoin"
        assert dai.usd_price == 1.0001
        assert dai.is_base_pool_lp_token is False

    def test_3pool_urls(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[0]
        assert len(pool.pool_urls.swap) == 1
        assert "3pool" in pool.pool_urls.swap[0]

    def test_gauge_crv_apy(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[0]
        assert len(pool.gauge_crv_apy) == 2
        assert pool.gauge_crv_apy[0] == 0.00003641
        assert pool.gauge_crv_apy[1] == 0.00009103

    def test_gauge_rewards(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[1]
        assert len(pool.gauge_rewards) == 1
        reward = pool.gauge_rewards[0]
        assert reward.symbol == "CRV"
        assert reward.apy == 5.2
        assert reward.token_price == 0.5

    def test_second_pool(self, service):
        resp = service.GetPools(pb.GetPoolsRequest(blockchain_id="ethereum", registry_id="main"))
        pool = resp.pools[1]
        assert pool.name == "Curve.fi aDAI/aUSDC"
        assert pool.symbol == "a3Crv"
        assert pool.usd_total == 5000000.0

    def test_defaults_to_ethereum_main(self, service):
        resp = service.GetPools(pb.GetPoolsRequest())
        assert len(resp.pools) == 2

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None, follow_redirects=True: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"success": True, "data": {"poolData": []}}),
        )
        resp = service.GetPools(pb.GetPoolsRequest())
        assert len(resp.pools) == 0

    def test_creation_fields(self, service):
        resp = service.GetPools(pb.GetPoolsRequest())
        pool = resp.pools[0]
        assert pool.creation_ts == 1600000000
        assert pool.creation_block_number == 10809473


class TestGetApys:
    def test_returns_pools(self, service):
        resp = service.GetApys(pb.GetApysRequest())
        assert len(resp.pools) == 2

    def test_3pool_apy(self, service):
        resp = service.GetApys(pb.GetApysRequest())
        pool = resp.pools[0]
        assert pool.address == "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
        assert pool.type == "main"
        assert pool.latest_daily_apy_pcent == 1.49
        assert pool.latest_weekly_apy_pcent == 1.47
        assert pool.volume_usd == 396294.19

    def test_second_pool_apy(self, service):
        resp = service.GetApys(pb.GetApysRequest())
        pool = resp.pools[1]
        assert pool.latest_daily_apy_pcent == 0.28
        assert pool.volume_usd == 0


class TestGetVolumes:
    def test_returns_pools(self, service):
        resp = service.GetVolumes(pb.GetVolumesRequest())
        assert len(resp.pools) == 2

    def test_3pool_volume(self, service):
        resp = service.GetVolumes(pb.GetVolumesRequest())
        pool = resp.pools[0]
        assert pool.address == "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
        assert pool.volume_usd == 396294.19
        assert pool.latest_daily_apy_pcent == 1.49
        assert pool.latest_weekly_apy_pcent == 1.47
        assert pool.type == "main"

    def test_second_pool_volume(self, service):
        resp = service.GetVolumes(pb.GetVolumesRequest())
        pool = resp.pools[1]
        assert pool.volume_usd == 0
        assert pool.latest_daily_apy_pcent == 0.28


class TestGetTVL:
    def test_returns_pools(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        assert len(resp.pools) == 2

    def test_pool_usd_total(self, service):
        resp = service.GetTVL(pb.GetTVLRequest())
        assert resp.pools[0].usd_total == 162456848.37
        assert resp.pools[1].usd_total == 5000000.0


class TestGetFactoryTVL:
    def test_returns_factory_balances(self, service):
        resp = service.GetFactoryTVL(pb.GetFactoryTVLRequest())
        assert resp.factory_balances == 81615253.25


class TestGetWeeklyFees:
    def test_returns_weekly_fees(self, service):
        resp = service.GetWeeklyFees(pb.GetWeeklyFeesRequest())
        assert len(resp.weekly_fees) == 3

    def test_total_fees(self, service):
        resp = service.GetWeeklyFees(pb.GetWeeklyFeesRequest())
        assert resp.total_fees == 170504253.43

    def test_fee_entry_fields(self, service):
        resp = service.GetWeeklyFees(pb.GetWeeklyFeesRequest())
        entry = resp.weekly_fees[0]
        assert entry.date == "Thu Mar 12 2026"
        assert entry.ts == 1773273600000
        assert entry.raw_fees == 0

    def test_second_entry(self, service):
        resp = service.GetWeeklyFees(pb.GetWeeklyFeesRequest())
        entry = resp.weekly_fees[1]
        assert entry.raw_fees == 79144.67

    def test_third_entry(self, service):
        resp = service.GetWeeklyFees(pb.GetWeeklyFeesRequest())
        entry = resp.weekly_fees[2]
        assert entry.raw_fees == 110431.77


class TestGetETHPrice:
    def test_returns_price(self, service):
        resp = service.GetETHPrice(pb.GetETHPriceRequest())
        assert resp.price == 2028.76


class TestGetSubgraphData:
    def test_returns_pools(self, service):
        resp = service.GetSubgraphData(pb.GetSubgraphDataRequest(blockchain_id="ethereum"))
        assert len(resp.pools) == 2

    def test_3pool_subgraph(self, service):
        resp = service.GetSubgraphData(pb.GetSubgraphDataRequest(blockchain_id="ethereum"))
        pool = resp.pools[0]
        assert pool.address == "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
        assert pool.latest_daily_apy == 1.49
        assert pool.latest_weekly_apy == 1.47
        assert pool.type == "main"
        assert pool.volume_usd == 396294.19
        assert abs(pool.virtual_price - 1039823717130228200) < 1e6

    def test_defaults_to_ethereum(self, service):
        resp = service.GetSubgraphData(pb.GetSubgraphDataRequest())
        assert len(resp.pools) == 2

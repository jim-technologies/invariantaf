"""Unit tests — every OrcaService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from orca_mcp.gen.orca.v1 import orca_pb2 as pb
from tests.conftest import (
    FAKE_POOL,
    FAKE_POOL_2,
    FAKE_POOLS_RESPONSE,
    FAKE_PROTOCOL_STATS,
    FAKE_PROTOCOL_TOKEN,
    FAKE_TOKEN,
    FAKE_TOKEN_2,
    FAKE_TOKENS_RESPONSE,
)


class TestListPools:
    def test_returns_pools(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        assert len(resp.pools) == 2

    def test_sol_usdc_pool(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        pool = resp.pools[0]
        assert pool.address == "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
        assert pool.token_a.symbol == "SOL"
        assert pool.token_b.symbol == "USDC"
        assert pool.price == "135.50"
        assert pool.tvl_usdc == "12500000.00"
        assert pool.tick_spacing == 64
        assert pool.fee_rate == 2000

    def test_pool_stats(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        pool = resp.pools[0]
        assert pool.stats_24h.volume == "15000000.00"
        assert pool.stats_24h.fees == "30000.00"
        assert pool.stats_7d.volume == "95000000.00"
        assert pool.stats_30d.volume == "400000000.00"

    def test_pool_rewards(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        pool = resp.pools[0]
        assert len(pool.rewards) == 1
        assert pool.rewards[0].active is True
        assert pool.rewards[0].mint == "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"

    def test_locked_liquidity(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        pool = resp.pools[0]
        assert len(pool.locked_liquidity_percent) == 1
        assert pool.locked_liquidity_percent[0].name == "OrcaLock"
        assert pool.locked_liquidity_percent[0].locked_percentage == "0.00000068"

    def test_second_pool(self, service):
        resp = service.ListPools(pb.ListPoolsRequest())
        pool = resp.pools[1]
        assert pool.address == "HJPjoWUrhoZzkNfRpHuieeFk9WGRBBNRYgLKr3Cp2Jc2"
        assert pool.token_a.symbol == "USDC"
        assert pool.token_b.symbol == "USDT"
        assert pool.fee_rate == 100
        assert len(pool.rewards) == 0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"data": []})
        )
        resp = service.ListPools(pb.ListPoolsRequest())
        assert len(resp.pools) == 0


class TestGetPool:
    def test_returns_pool(self, service):
        resp = service.GetPool(pb.GetPoolRequest(address="Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"))
        assert resp.pool.address == "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
        assert resp.pool.token_a.symbol == "SOL"
        assert resp.pool.token_b.symbol == "USDC"

    def test_pool_balances(self, service):
        resp = service.GetPool(pb.GetPoolRequest(address="Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"))
        assert resp.pool.token_balance_a == "46200.123"
        assert resp.pool.token_balance_b == "6260000.456"

    def test_pool_type(self, service):
        resp = service.GetPool(pb.GetPoolRequest(address="Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"))
        assert resp.pool.pool_type == "concentrated"


class TestSearchPools:
    def test_returns_pools(self, service):
        resp = service.SearchPools(pb.SearchPoolsRequest(query="SOL-USDC"))
        assert len(resp.pools) == 2

    def test_first_result(self, service):
        resp = service.SearchPools(pb.SearchPoolsRequest(query="SOL-USDC"))
        assert resp.pools[0].token_a.symbol == "SOL"
        assert resp.pools[0].token_b.symbol == "USDC"


class TestListTokens:
    def test_returns_tokens(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        assert len(resp.tokens) == 2

    def test_orca_token(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        t = resp.tokens[0]
        assert t.address == "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"
        assert t.metadata.name == "Orca"
        assert t.metadata.symbol == "ORCA"
        assert t.decimals == 6
        assert t.price_usdc == "3.45"
        assert t.stats.volume_24h == 433016.17

    def test_sol_token(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        t = resp.tokens[1]
        assert t.address == "So11111111111111111111111111111111111111112"
        assert t.metadata.symbol == "SOL"
        assert t.price_usdc == "135.50"
        assert t.decimals == 9

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"data": []})
        )
        resp = service.ListTokens(pb.ListTokensRequest())
        assert len(resp.tokens) == 0


class TestGetToken:
    def test_returns_token(self, service):
        resp = service.GetToken(pb.GetTokenRequest(mint_address="orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"))
        assert resp.token.metadata.name == "Orca"
        assert resp.token.metadata.symbol == "ORCA"
        assert resp.token.price_usdc == "3.45"

    def test_token_supply(self, service):
        resp = service.GetToken(pb.GetTokenRequest(mint_address="orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"))
        assert resp.token.supply == 74999565293160

    def test_token_program(self, service):
        resp = service.GetToken(pb.GetTokenRequest(mint_address="orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"))
        assert resp.token.token_program == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


class TestSearchTokens:
    def test_returns_tokens(self, service):
        resp = service.SearchTokens(pb.SearchTokensRequest(query="ORCA"))
        assert len(resp.tokens) == 2

    def test_first_result(self, service):
        resp = service.SearchTokens(pb.SearchTokensRequest(query="ORCA"))
        assert resp.tokens[0].metadata.symbol == "ORCA"


class TestGetProtocolStats:
    def test_returns_stats(self, service):
        resp = service.GetProtocolStats(pb.GetProtocolStatsRequest())
        assert resp.tvl == "1250000000.00"
        assert resp.volume_24h_usdc == "350000000.00"
        assert resp.fees_24h_usdc == "700000.00"
        assert resp.revenue_24h_usdc == "210000.00"


class TestGetProtocolToken:
    def test_returns_token(self, service):
        resp = service.GetProtocolToken(pb.GetProtocolTokenRequest())
        assert resp.symbol == "ORCA"
        assert resp.name == "Orca"
        assert resp.price == "3.45"
        assert resp.circulating_supply == "50000000"
        assert resp.total_supply == "100000000"
        assert resp.volume_24h == "433016.17"

    def test_description(self, service):
        resp = service.GetProtocolToken(pb.GetProtocolTokenRequest())
        assert resp.description == "Orca is a DEX on Solana."

    def test_image_url(self, service):
        resp = service.GetProtocolToken(pb.GetProtocolTokenRequest())
        assert resp.image_url == "https://arweave.net/orca-logo.png"


class TestGetLockedLiquidity:
    def test_returns_entries(self, service):
        resp = service.GetLockedLiquidity(
            pb.GetLockedLiquidityRequest(address="Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE")
        )
        assert len(resp.entries) == 1
        assert resp.entries[0].name == "OrcaLock"
        assert resp.entries[0].locked_percentage == "0.00000068"

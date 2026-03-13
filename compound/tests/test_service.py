"""Unit tests -- every CompoundService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from compound_mcp.gen.compound.v1 import compound_pb2 as pb
from tests.conftest import (
    FAKE_CTOKENS_RESPONSE,
    FAKE_CTOKEN_DAI,
    FAKE_CTOKEN_ETH,
    FAKE_CTOKEN_USDC,
    FAKE_MARKET_HISTORY,
    FAKE_PROPOSALS,
)


class TestListCTokens:
    def test_returns_ctokens(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        assert len(resp.ctokens) == 3

    def test_ctoken_basic_fields(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.address == "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643"
        assert ct.name == "Compound Dai"
        assert ct.symbol == "cDAI"

    def test_ctoken_underlying(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        u = resp.ctokens[0].underlying
        assert u.address == "0x6B175474E89094C44Da98b954EedeAC495271d0F"
        assert u.name == "Dai"
        assert u.symbol == "DAI"
        assert u.decimals == 18
        assert u.price_usd == 1.0

    def test_ctoken_rates(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.supply_rate_apy == 0.032
        assert ct.borrow_rate_apy == 0.055

    def test_ctoken_supply_borrow(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.total_supply == "350000000.123456"
        assert ct.total_borrows == "210000000.654321"
        assert ct.reserves == "5000000.789"
        assert ct.cash == "145000000.000"

    def test_ctoken_collateral_factor(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.collateral_factor == 0.75

    def test_ctoken_exchange_rate(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.exchange_rate == 0.022

    def test_ctoken_participant_counts(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.number_of_suppliers == 12345
        assert ct.number_of_borrowers == 6789

    def test_ctoken_reserve_factor(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[0]
        assert ct.reserve_factor == 0.15

    def test_ctoken_borrow_cap(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        # DAI has no borrow cap.
        assert resp.ctokens[0].borrow_cap == "0"
        # ETH has a borrow cap.
        assert resp.ctokens[1].borrow_cap == "100000"

    def test_eth_ctoken(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[1]
        assert ct.symbol == "cETH"
        assert ct.underlying.symbol == "ETH"
        assert ct.underlying.price_usd == 3200.50
        assert ct.collateral_factor == 0.82
        assert ct.number_of_suppliers == 45678

    def test_usdc_ctoken(self, service):
        resp = service.ListCTokens(pb.ListCTokensRequest())
        ct = resp.ctokens[2]
        assert ct.symbol == "cUSDC"
        assert ct.underlying.symbol == "USDC"
        assert ct.underlying.decimals == 6
        assert ct.collateral_factor == 0.80

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"cToken": []}),
        )
        resp = service.ListCTokens(pb.ListCTokensRequest())
        assert len(resp.ctokens) == 0

    def test_calls_correct_url(self, service, mock_http):
        service.ListCTokens(pb.ListCTokensRequest())
        call_url = mock_http.get.call_args[0][0]
        assert call_url.endswith("/ctoken")


class TestGetMarketHistory:
    def test_returns_points(self, service):
        resp = service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        assert len(resp.points) == 3

    def test_point_fields(self, service):
        resp = service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        pt = resp.points[0]
        assert pt.block_number == 18000000
        assert pt.block_timestamp == 1700000000
        assert pt.supply_rate == 0.031
        assert pt.total_supply == "340000000.00"
        assert pt.total_borrows == "200000000.00"

    def test_second_point(self, service):
        resp = service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        pt = resp.points[1]
        assert pt.block_number == 18100000
        assert pt.block_timestamp == 1700100000
        assert pt.supply_rate == 0.033

    def test_third_point(self, service):
        resp = service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        pt = resp.points[2]
        assert pt.block_number == 18200000
        assert pt.supply_rate == 0.032
        assert pt.total_supply == "350000000.00"

    def test_passes_asset_param(self, service, mock_http):
        service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        call_kwargs = mock_http.get.call_args
        assert call_kwargs[1]["params"]["asset"] == "0x6B175474E89094C44Da98b954EedeAC495271d0F"

    def test_passes_optional_params(self, service, mock_http):
        service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
            min_block_timestamp=1700000000,
            num_points=10,
        ))
        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1]["params"]
        assert params["min_block_timestamp"] == 1700000000
        assert params["num_points"] == 10

    def test_empty_history(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"market_history": []}),
        )
        resp = service.GetMarketHistory(pb.GetMarketHistoryRequest(
            asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ))
        assert len(resp.points) == 0


class TestListProposals:
    def test_returns_proposals(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        assert len(resp.proposals) == 3

    def test_proposal_basic_fields(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[0]
        assert p.id == 130
        assert p.title == "Add WBTC Market"
        assert p.state == "Executed"
        assert p.proposer == "0x1234567890abcdef1234567890abcdef12345678"

    def test_proposal_description(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[0]
        assert "WBTC" in p.description

    def test_proposal_votes(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[0]
        assert p.for_votes == "500000"
        assert p.against_votes == "10000"

    def test_proposal_blocks(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[0]
        assert p.start_block == 17900000
        assert p.end_block == 17920000
        assert p.created_at == 1699500000

    def test_active_proposal(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[1]
        assert p.id == 131
        assert p.title == "Update Interest Rate Model"
        assert p.state == "Active"
        assert p.for_votes == "300000"
        assert p.against_votes == "50000"

    def test_defeated_proposal(self, service):
        resp = service.ListProposals(pb.ListProposalsRequest())
        p = resp.proposals[2]
        assert p.id == 132
        assert p.state == "Defeated"
        assert p.for_votes == "100000"
        assert p.against_votes == "400000"

    def test_passes_limit_as_page_size(self, service, mock_http):
        service.ListProposals(pb.ListProposalsRequest(limit=5))
        call_kwargs = mock_http.get.call_args
        assert call_kwargs[1]["params"]["page_size"] == 5

    def test_no_limit_no_params(self, service, mock_http):
        service.ListProposals(pb.ListProposalsRequest())
        call_kwargs = mock_http.get.call_args
        # No params when limit is 0 (default).
        assert call_kwargs[1].get("params") == {} or "page_size" not in call_kwargs[1].get("params", {})

    def test_empty_proposals(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"proposals": []}),
        )
        resp = service.ListProposals(pb.ListProposalsRequest())
        assert len(resp.proposals) == 0

"""Unit tests for AaveService -- uses mocked GraphQL."""

from aave_mcp.gen.aave.v1 import aave_pb2 as pb


class TestGetMarkets:
    def test_returns_markets(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest(chain_ids=[1]))
        assert len(resp.markets) == 1

    def test_market_fields(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest(chain_ids=[1]))
        m = resp.markets[0]
        assert m.name == "AaveV3Ethereum"
        assert m.chain_id == 1
        assert "34000000000" in m.total_market_size

    def test_reserves(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest(chain_ids=[1]))
        reserves = resp.markets[0].reserves
        assert len(reserves) == 2
        assert reserves[0].symbol == "WETH"
        assert reserves[1].symbol == "USDC"

    def test_reserve_fields(self, service):
        resp = service.GetMarkets(pb.GetMarketsRequest(chain_ids=[1]))
        r = resp.markets[0].reserves[0]
        assert r.supply_apy == "0.02"
        assert r.borrow_apy == "0.03"
        assert r.utilization_rate == "0.6"
        assert r.usd_exchange_rate == "2100.50"
        assert r.is_frozen is False
        assert r.borrowing_enabled is True


class TestGetSupplyAPYHistory:
    def test_returns_data_points(self, service):
        resp = service.GetSupplyAPYHistory(pb.GetAPYHistoryRequest(
            market_address="0xabc", underlying_token="0xdef",
            chain_id=1, window="ONE_MONTH",
        ))
        assert len(resp.data_points) == 2

    def test_data_point_fields(self, service):
        resp = service.GetSupplyAPYHistory(pb.GetAPYHistoryRequest(
            market_address="0xabc", underlying_token="0xdef",
            chain_id=1, window="ONE_MONTH",
        ))
        dp = resp.data_points[0]
        assert dp.timestamp == 1700000000
        assert dp.apy == "0.02"


class TestGetBorrowAPYHistory:
    def test_returns_data_points(self, service):
        resp = service.GetBorrowAPYHistory(pb.GetAPYHistoryRequest(
            market_address="0xabc", underlying_token="0xdef",
            chain_id=1, window="ONE_MONTH",
        ))
        assert len(resp.data_points) == 2

    def test_data_point_fields(self, service):
        resp = service.GetBorrowAPYHistory(pb.GetAPYHistoryRequest(
            market_address="0xabc", underlying_token="0xdef",
            chain_id=1, window="ONE_MONTH",
        ))
        dp = resp.data_points[0]
        assert dp.timestamp == 1700000000
        assert dp.apy == "0.03"


class TestGetReserve:
    def test_returns_reserve(self, service):
        resp = service.GetReserve(pb.GetReserveRequest(
            market_address="0xabc", underlying_token="0xdef", chain_id=1,
        ))
        assert resp.reserve is not None
        assert resp.reserve.symbol == "WETH"

    def test_reserve_fields(self, service):
        resp = service.GetReserve(pb.GetReserveRequest(
            market_address="0xabc", underlying_token="0xdef", chain_id=1,
        ))
        r = resp.reserve
        assert r.supply_apy == "0.02"
        assert r.borrow_apy == "0.03"
        assert r.borrowing_enabled is True

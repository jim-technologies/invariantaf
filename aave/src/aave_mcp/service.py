"""AaveService -- wraps the Aave v3 GraphQL API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from aave_mcp.gen.aave.v1 import aave_pb2 as pb

_GRAPHQL_URL = "https://api.v3.aave.com/graphql"

_MARKETS_QUERY = """
query GetMarkets($chainIds: [Int!]!) {
  markets(request: { chainIds: $chainIds }) {
    name
    chain { chainId }
    totalMarketSize
    totalAvailableLiquidity
    reserves {
      underlyingToken { symbol name }
      supplyInfo { apy { value } total { value } }
      borrowInfo { apy { value } total { amount { value } } utilizationRate { value } }
      usdExchangeRate
      isFrozen
    }
  }
}
"""

_SUPPLY_APY_HISTORY_QUERY = """
query GetSupplyAPYHistory($market: String!, $token: String!, $window: TimeWindow!, $chainId: Int!) {
  supplyAPYHistory(request: { market: $market, underlyingToken: $token, window: $window, chainId: $chainId }) {
    timestamp
    apy { value }
  }
}
"""

_BORROW_APY_HISTORY_QUERY = """
query GetBorrowAPYHistory($market: String!, $token: String!, $window: TimeWindow!, $chainId: Int!) {
  borrowAPYHistory(request: { market: $market, underlyingToken: $token, window: $window, chainId: $chainId }) {
    timestamp
    apy { value }
  }
}
"""

_RESERVE_QUERY = """
query GetReserve($market: String!, $token: String!, $chainId: Int!) {
  reserve(request: { market: $market, underlyingToken: $token, chainId: $chainId }) {
    underlyingToken { symbol name }
    supplyInfo { apy { value } total { value } maxLTV { value } liquidationThreshold { value } }
    borrowInfo { apy { value } total { amount { value } } availableLiquidity { amount { value } } utilizationRate { value } reserveFactor { value } }
    usdExchangeRate
    isFrozen
    flashLoanEnabled
  }
}
"""

_VALID_WINDOWS = {"ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "ONE_YEAR", "ALL_TIME"}


class AaveService:
    """Implements AaveService RPCs via the Aave v3 GraphQL API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30, follow_redirects=True)

    def _query(self, query: str, variables: dict | None = None) -> Any:
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        resp = self._http.post(_GRAPHQL_URL, json=body)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data and data["errors"]:
            raise RuntimeError(f"GraphQL error: {data['errors'][0].get('message', data['errors'])}")
        return data.get("data", {})

    def _parse_reserve(self, r: dict) -> pb.Reserve:
        token = r.get("underlyingToken") or {}
        supply = r.get("supplyInfo") or {}
        borrow = r.get("borrowInfo")
        supply_apy = (supply.get("apy") or {}).get("value", "0")
        total_supplied = (supply.get("total") or {}).get("value", "0")

        borrow_apy = "0"
        total_borrowed = "0"
        utilization = "0"
        borrowing_enabled = borrow is not None

        if borrow:
            borrow_apy = (borrow.get("apy") or {}).get("value", "0")
            total_borrowed = ((borrow.get("total") or {}).get("amount") or {}).get("value", "0")
            utilization = (borrow.get("utilizationRate") or {}).get("value", "0")

        return pb.Reserve(
            symbol=token.get("symbol", ""),
            name=token.get("name", ""),
            supply_apy=supply_apy,
            total_supplied=total_supplied,
            borrow_apy=borrow_apy,
            total_borrowed=total_borrowed,
            utilization_rate=utilization,
            usd_exchange_rate=str(r.get("usdExchangeRate", "0")),
            is_frozen=r.get("isFrozen", False),
            borrowing_enabled=borrowing_enabled,
        )

    def GetMarkets(self, request: Any, context: Any = None) -> pb.GetMarketsResponse:
        chain_ids = list(request.chain_ids) if request.chain_ids else [1]
        raw = self._query(_MARKETS_QUERY, {"chainIds": chain_ids})
        resp = pb.GetMarketsResponse()
        for m in raw.get("markets", []):
            chain = m.get("chain") or {}
            reserves = [self._parse_reserve(r) for r in (m.get("reserves") or [])]
            resp.markets.append(pb.Market(
                name=m.get("name", ""),
                chain_id=chain.get("chainId", 0),
                total_market_size=str(m.get("totalMarketSize", "0")),
                total_available_liquidity=str(m.get("totalAvailableLiquidity", "0")),
                reserves=reserves,
            ))
        return resp

    def _get_apy_history(self, query: str, response_key: str, request: Any) -> pb.GetAPYHistoryResponse:
        window = request.window if request.window in _VALID_WINDOWS else "ONE_MONTH"
        raw = self._query(query, {
            "market": request.market_address,
            "token": request.underlying_token,
            "window": window,
            "chainId": request.chain_id,
        })
        resp = pb.GetAPYHistoryResponse()
        for dp in raw.get(response_key, []):
            resp.data_points.append(pb.APYDataPoint(
                timestamp=dp.get("timestamp", 0),
                apy=(dp.get("apy") or {}).get("value", "0"),
            ))
        return resp

    def GetSupplyAPYHistory(self, request: Any, context: Any = None) -> pb.GetAPYHistoryResponse:
        return self._get_apy_history(_SUPPLY_APY_HISTORY_QUERY, "supplyAPYHistory", request)

    def GetBorrowAPYHistory(self, request: Any, context: Any = None) -> pb.GetAPYHistoryResponse:
        return self._get_apy_history(_BORROW_APY_HISTORY_QUERY, "borrowAPYHistory", request)

    def GetReserve(self, request: Any, context: Any = None) -> pb.GetReserveResponse:
        raw = self._query(_RESERVE_QUERY, {
            "market": request.market_address,
            "token": request.underlying_token,
            "chainId": request.chain_id,
        })
        reserve_data = raw.get("reserve", {})
        return pb.GetReserveResponse(reserve=self._parse_reserve(reserve_data))

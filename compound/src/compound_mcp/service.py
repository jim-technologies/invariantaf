"""CompoundService -- wraps the Compound Finance API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from compound_mcp.gen.compound.v1 import compound_pb2 as pb

_BASE_URL = "https://api.compound.finance/api/v2"


def _parse_ctoken(ct: dict) -> pb.CToken:
    """Parse a raw Compound API cToken JSON object into a CToken proto message."""
    # Underlying token info.
    raw_underlying = ct.get("underlying") or {}
    underlying = pb.UnderlyingToken(
        address=raw_underlying.get("address", "") or "",
        name=raw_underlying.get("name", "") or "",
        symbol=raw_underlying.get("symbol", "") or "",
        decimals=int(raw_underlying.get("decimals") or 0),
        price_usd=float(raw_underlying.get("price", {}).get("value") or 0),
    )

    return pb.CToken(
        address=ct.get("token_address", "") or "",
        name=ct.get("name", "") or "",
        symbol=ct.get("symbol", "") or "",
        underlying=underlying,
        supply_rate_apy=float(ct.get("supply_rate", {}).get("value") or 0),
        borrow_rate_apy=float(ct.get("borrow_rate", {}).get("value") or 0),
        total_supply=str(ct.get("total_supply", {}).get("value", "") or ""),
        total_borrows=str(ct.get("total_borrows", {}).get("value", "") or ""),
        reserves=str(ct.get("reserves", {}).get("value", "") or ""),
        cash=str(ct.get("cash", {}).get("value", "") or ""),
        collateral_factor=float(ct.get("collateral_factor", {}).get("value") or 0),
        exchange_rate=float(ct.get("exchange_rate", {}).get("value") or 0),
        number_of_suppliers=int(ct.get("number_of_suppliers") or 0),
        number_of_borrowers=int(ct.get("number_of_borrowers") or 0),
        reserve_factor=float(ct.get("reserve_factor", {}).get("value") or 0),
        borrow_cap=str(ct.get("borrow_cap", {}).get("value", "") or ""),
    )


def _parse_market_history_point(pt: dict) -> pb.MarketHistoryPoint:
    """Parse a raw market history data point."""
    return pb.MarketHistoryPoint(
        block_number=int(pt.get("block_number") or 0),
        block_timestamp=int(pt.get("block_timestamp") or 0),
        supply_rate=float(pt.get("rates", [{}])[0].get("rate") or 0) if pt.get("rates") else 0,
        borrow_rate=float(pt.get("rates", [{}])[0].get("rate") or 0) if pt.get("rates") else 0,
        total_supply=str(pt.get("total_supply", {}).get("value", "") or ""),
        total_borrows=str(pt.get("total_borrows", {}).get("value", "") or ""),
    )


def _parse_proposal(p: dict) -> pb.Proposal:
    """Parse a raw governance proposal JSON object."""
    return pb.Proposal(
        id=int(p.get("id") or 0),
        title=p.get("title", "") or "",
        description=p.get("description", "") or "",
        state=p.get("state", "") or "",
        proposer=p.get("proposer", "") or "",
        for_votes=str(p.get("for_votes") or "0"),
        against_votes=str(p.get("against_votes") or "0"),
        start_block=int(p.get("start_block") or 0),
        end_block=int(p.get("end_block") or 0),
        created_at=int(p.get("created_at") or 0),
    )


class CompoundService:
    """Implements CompoundService RPCs via the free Compound v2 API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def ListCTokens(self, request: Any, context: Any = None) -> pb.ListCTokensResponse:
        raw = self._get(f"{_BASE_URL}/ctoken")
        resp = pb.ListCTokensResponse()
        for ct in raw.get("cToken", []):
            resp.ctokens.append(_parse_ctoken(ct))
        return resp

    def GetMarketHistory(self, request: Any, context: Any = None) -> pb.GetMarketHistoryResponse:
        params: dict[str, Any] = {"asset": request.asset}
        if request.min_block_timestamp:
            params["min_block_timestamp"] = request.min_block_timestamp
        if request.num_points:
            params["num_points"] = request.num_points
        raw = self._get(f"{_BASE_URL}/market_history/graph", params=params)
        resp = pb.GetMarketHistoryResponse()
        for pt in raw.get("market_history", []):
            resp.points.append(_parse_market_history_point(pt))
        return resp

    def ListProposals(self, request: Any, context: Any = None) -> pb.ListProposalsResponse:
        params: dict[str, Any] = {}
        if request.limit:
            params["page_size"] = request.limit
        raw = self._get(f"{_BASE_URL}/governance/proposals", params=params)
        resp = pb.ListProposalsResponse()
        for p in raw.get("proposals", []):
            resp.proposals.append(_parse_proposal(p))
        return resp

"""OneInchService — wraps the 1inch DEX aggregator API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from oneinch_mcp.gen.oneinch.v1 import oneinch_pb2 as pb

_BASE_URL = "https://api.1inch.dev"


class OneInchService:
    """Implements OneInchService RPCs via the 1inch Developer Portal API."""

    def __init__(self, *, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ONEINCH_API_KEY", "")
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._http = httpx.Client(timeout=30, headers=headers)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    # --- RPCs ---

    def GetQuote(self, request: Any, context: Any = None) -> pb.GetQuoteResponse:
        chain_id = request.chain_id or 1
        params = {
            "src": request.src,
            "dst": request.dst,
            "amount": request.amount,
        }
        raw = self._get(f"/swap/v6.0/{chain_id}/quote", params=params)
        return pb.GetQuoteResponse(
            src_token=raw.get("srcToken", "") or "",
            dst_token=raw.get("dstToken", "") or "",
            src_amount=str(raw.get("srcAmount", "")) or "",
            dst_amount=str(raw.get("dstAmount", "")) or "",
            gas=raw.get("gas") or 0,
        )

    def GetSwap(self, request: Any, context: Any = None) -> pb.GetSwapResponse:
        chain_id = request.chain_id or 1
        params = {
            "src": request.src,
            "dst": request.dst,
            "amount": request.amount,
            "from": getattr(request, "from"),  # 'from' is a Python keyword
            "slippage": request.slippage,
        }
        raw = self._get(f"/swap/v6.0/{chain_id}/swap", params=params)
        tx_data = raw.get("tx", {})
        tx = pb.SwapTransaction(
            to=tx_data.get("to", "") or "",
            data=tx_data.get("data", "") or "",
            value=str(tx_data.get("value", "")) or "",
            gas=tx_data.get("gas") or 0,
            gas_price=str(tx_data.get("gasPrice", "")) or "",
        )
        return pb.GetSwapResponse(
            src_token=raw.get("srcToken", "") or "",
            dst_token=raw.get("dstToken", "") or "",
            src_amount=str(raw.get("srcAmount", "")) or "",
            dst_amount=str(raw.get("dstAmount", "")) or "",
            tx=tx,
        )

    def GetTokenPrice(self, request: Any, context: Any = None) -> pb.GetTokenPriceResponse:
        chain_id = request.chain_id or 1
        currency = request.currency or "USD"
        params = {
            "tokens": request.tokens,
            "currency": currency,
        }
        raw = self._get(f"/price/v1.1/{chain_id}", params=params)
        resp = pb.GetTokenPriceResponse()
        for addr, price_val in raw.items():
            price = 0.0
            if isinstance(price_val, (int, float)):
                price = float(price_val)
            elif isinstance(price_val, str):
                try:
                    price = float(price_val)
                except ValueError:
                    pass
            resp.prices.append(pb.TokenPrice(
                address=addr,
                price_usd=price,
            ))
        return resp

    def GetTokenInfo(self, request: Any, context: Any = None) -> pb.GetTokenInfoResponse:
        chain_id = request.chain_id or 1
        params = {"address": request.address}
        raw = self._get(f"/token/v1.2/{chain_id}", params=params)
        token = pb.TokenInfo(
            address=raw.get("address", "") or "",
            symbol=raw.get("symbol", "") or "",
            name=raw.get("name", "") or "",
            decimals=raw.get("decimals") or 0,
            logo_uri=raw.get("logoURI", "") or "",
            tags=raw.get("tags", []) or [],
        )
        return pb.GetTokenInfoResponse(token=token)

    def SearchTokens(self, request: Any, context: Any = None) -> pb.SearchTokensResponse:
        chain_id = request.chain_id or 1
        params = {"query": request.query}
        raw = self._get(f"/token/v1.2/{chain_id}/search", params=params)
        resp = pb.SearchTokensResponse()
        tokens_list = raw if isinstance(raw, list) else []
        for t in tokens_list:
            resp.tokens.append(pb.TokenInfo(
                address=t.get("address", "") or "",
                symbol=t.get("symbol", "") or "",
                name=t.get("name", "") or "",
                decimals=t.get("decimals") or 0,
                logo_uri=t.get("logoURI", "") or "",
                tags=t.get("tags", []) or [],
            ))
        return resp

    def GetBalances(self, request: Any, context: Any = None) -> pb.GetBalancesResponse:
        chain_id = request.chain_id or 1
        raw = self._get(f"/balance/v1.2/{chain_id}/balances/{request.address}")
        resp = pb.GetBalancesResponse()
        for addr, balance in raw.items():
            resp.balances.append(pb.TokenBalance(
                address=addr,
                balance=str(balance),
            ))
        return resp

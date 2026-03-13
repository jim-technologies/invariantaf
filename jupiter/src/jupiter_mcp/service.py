"""JupiterService — wraps the Jupiter Solana DEX aggregator API into proto RPCs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from jupiter_mcp.gen.jupiter.v1 import jupiter_pb2 as pb

_BASE_URL = "https://api.jup.ag"


class JupiterService:
    """Implements JupiterService RPCs via the Jupiter API.

    An API key is required. Generate a free key at https://portal.jup.ag
    and pass it via the ``api_key`` parameter or the ``JUPITER_API_KEY``
    environment variable.
    """

    def __init__(self, *, api_key: str | None = None):
        key = api_key or os.environ.get("JUPITER_API_KEY", "")
        headers = {}
        if key:
            headers["x-api-key"] = key
        self._http = httpx.Client(timeout=30, headers=headers)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, json_body: dict) -> Any:
        resp = self._http.post(url, json=json_body)
        resp.raise_for_status()
        return resp.json()

    # --- Price ---

    def GetPrice(self, request: Any, context: Any = None) -> pb.GetPriceResponse:
        raw = self._get(f"{_BASE_URL}/price/v3", params={"ids": request.ids})
        resp = pb.GetPriceResponse()
        for mint, info in raw.items():
            if not isinstance(info, dict):
                continue
            price = 0.0
            if info.get("usdPrice") is not None:
                try:
                    price = float(info["usdPrice"])
                except (ValueError, TypeError):
                    price = 0.0
            resp.prices.append(pb.TokenPrice(
                mint=mint,
                price=price,
                liquidity=info.get("liquidity") or 0,
                price_change_24h=info.get("priceChange24h") or 0,
            ))
        return resp

    # --- Quote ---

    def GetQuote(self, request: Any, context: Any = None) -> pb.GetQuoteResponse:
        params = {
            "inputMint": request.input_mint,
            "outputMint": request.output_mint,
            "amount": request.amount,
            "slippageBps": request.slippage_bps,
        }
        raw = self._get(f"{_BASE_URL}/swap/v1/quote", params=params)
        resp = pb.GetQuoteResponse(
            input_mint=raw.get("inputMint", ""),
            output_mint=raw.get("outputMint", ""),
            in_amount=raw.get("inAmount", ""),
            out_amount=raw.get("outAmount", ""),
            other_amount_threshold=raw.get("otherAmountThreshold", ""),
            price_impact_pct=raw.get("priceImpactPct", "") or "",
            swap_mode=raw.get("swapMode", ""),
            slippage_bps=raw.get("slippageBps", 0),
        )
        for step in raw.get("routePlan", []):
            swap_info = step.get("swapInfo", {})
            resp.route_plan.append(pb.RoutePlanStep(
                amm_key=swap_info.get("ammKey", ""),
                label=swap_info.get("label", "") or "",
                input_mint=swap_info.get("inputMint", ""),
                output_mint=swap_info.get("outputMint", ""),
                fee_amount=swap_info.get("feeAmount", ""),
                fee_mint=swap_info.get("feeMint", ""),
                percent=step.get("percent", 0),
            ))
        return resp

    # --- Swap ---

    def Swap(self, request: Any, context: Any = None) -> pb.SwapResponse:
        quote = json.loads(request.quote_response)
        body = {
            "quoteResponse": quote,
            "userPublicKey": request.user_public_key,
            "wrapAndUnwrapSol": request.wrap_and_unwrap_sol,
        }
        raw = self._post(f"{_BASE_URL}/swap/v1/swap", json_body=body)
        return pb.SwapResponse(
            swap_transaction=raw.get("swapTransaction", ""),
            last_valid_block_height=raw.get("lastValidBlockHeight", 0),
        )

    # --- Token Lists ---

    def ListTokens(self, request: Any, context: Any = None) -> pb.ListTokensResponse:
        raw = self._get(
            f"{_BASE_URL}/tokens/v2/search",
            params={"query": request.query},
        )
        resp = pb.ListTokensResponse()
        for t in raw:
            resp.tokens.append(self._parse_token(t))
        return resp

    def ListVerifiedTokens(self, request: Any, context: Any = None) -> pb.ListVerifiedTokensResponse:
        raw = self._get(
            f"{_BASE_URL}/tokens/v2/tag",
            params={"query": "verified"},
        )
        resp = pb.ListVerifiedTokensResponse()
        for t in raw:
            resp.tokens.append(self._parse_token(t))
        return resp

    # --- Markets ---

    def ListMarkets(self, request: Any, context: Any = None) -> pb.ListMarketsResponse:
        raw = self._get(f"{_BASE_URL}/swap/v1/markets")
        resp = pb.ListMarketsResponse()
        if isinstance(raw, list):
            for m in raw:
                resp.markets.append(pb.Market(
                    id=m.get("id", "") or "",
                    base_mint=m.get("baseMint", "") or "",
                    quote_mint=m.get("quoteMint", "") or "",
                    label=m.get("label", "") or "",
                    liquidity=m.get("liquidity") or 0,
                ))
        return resp

    # --- Helpers ---

    @staticmethod
    def _parse_token(t: dict) -> pb.Token:
        return pb.Token(
            address=t.get("address", "") or t.get("id", "") or "",
            symbol=t.get("symbol", "") or "",
            name=t.get("name", "") or "",
            decimals=t.get("decimals", 0),
            logo_uri=t.get("logoURI", "") or t.get("icon", "") or "",
            daily_volume=t.get("daily_volume") or 0,
            is_verified=bool(t.get("isVerified", False)),
        )

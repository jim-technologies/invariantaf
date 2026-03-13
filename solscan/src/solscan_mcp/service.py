"""SolscanService -- wraps the Solscan API v2 into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from solscan_mcp.gen.solscan.v1 import solscan_pb2 as pb

_BASE_URL = "https://pro-api.solscan.io/v2.0"


class SolscanService:
    """Implements SolscanService RPCs via the Solscan public API v2."""

    def __init__(self):
        api_key = os.environ.get("SOLSCAN_API_KEY", "")
        self._http = httpx.Client(
            timeout=30,
            headers={"token": api_key},
        )

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def GetAccountInfo(self, request: Any, context: Any = None) -> pb.GetAccountInfoResponse:
        raw = self._get("/account", params={"address": request.address})
        data = raw.get("data") or raw
        account = pb.AccountInfo(
            address=data.get("address", "") or "",
            lamports=data.get("lamports") or 0,
            owner=data.get("owner", "") or "",
            type=data.get("type", "") or "",
            rent_epoch=data.get("rentEpoch") or 0,
            executable=bool(data.get("executable")),
        )
        return pb.GetAccountInfoResponse(account=account)

    def GetAccountTokens(self, request: Any, context: Any = None) -> pb.GetAccountTokensResponse:
        raw = self._get("/account/token-accounts", params={"address": request.address})
        data = raw.get("data") or raw
        if isinstance(data, dict):
            data = data.get("token_accounts") or data.get("tokenAccounts") or []
        resp = pb.GetAccountTokensResponse()
        for t in data:
            info = t.get("tokenInfo") or t.get("token_info") or {}
            resp.tokens.append(pb.TokenAccount(
                token_address=t.get("tokenAddress", "") or t.get("token_address", "") or "",
                token_account=t.get("tokenAccount", "") or t.get("token_account", "") or "",
                amount=str(t.get("amount", "")) or "",
                token_decimals=info.get("decimals") or t.get("tokenDecimals") or t.get("token_decimals") or 0,
                token_name=info.get("name", "") or t.get("tokenName") or t.get("token_name") or "",
                token_symbol=info.get("symbol", "") or t.get("tokenSymbol") or t.get("token_symbol") or "",
                token_icon=info.get("icon", "") or t.get("tokenIcon") or t.get("token_icon") or "",
            ))
        return resp

    def GetAccountTransactions(self, request: Any, context: Any = None) -> pb.GetAccountTransactionsResponse:
        limit = request.limit if request.limit else 10
        raw = self._get("/account/transactions", params={
            "address": request.address,
            "limit": limit,
        })
        data = raw.get("data") or raw
        if isinstance(data, dict):
            data = data.get("transactions") or []
        resp = pb.GetAccountTransactionsResponse()
        for tx in data:
            signer = ""
            signer_list = tx.get("signer") or []
            if isinstance(signer_list, list) and signer_list:
                signer = signer_list[0]
            elif isinstance(signer_list, str):
                signer = signer_list
            resp.transactions.append(pb.Transaction(
                tx_hash=tx.get("txHash", "") or tx.get("tx_hash", "") or "",
                block_id=tx.get("blockId") or tx.get("block_id") or 0,
                block_time=tx.get("blockTime") or tx.get("block_time") or 0,
                status=tx.get("status", "") or "",
                fee=tx.get("fee") or 0,
                signer=signer,
            ))
        return resp

    def GetTokenMeta(self, request: Any, context: Any = None) -> pb.GetTokenMetaResponse:
        raw = self._get("/token/meta", params={"address": request.address})
        data = raw.get("data") or raw
        token = pb.TokenMeta(
            address=data.get("address", "") or "",
            name=data.get("name", "") or "",
            symbol=data.get("symbol", "") or "",
            decimals=data.get("decimals") or 0,
            icon=data.get("icon", "") or "",
            website=data.get("website", "") or "",
            twitter=data.get("twitter", "") or "",
            tag=data.get("tag", "") or "",
        )
        return pb.GetTokenMetaResponse(token=token)

    def GetTokenPrice(self, request: Any, context: Any = None) -> pb.GetTokenPriceResponse:
        raw = self._get("/token/price", params={"address": request.address})
        data = raw.get("data") or raw
        price = pb.TokenPrice(
            address=request.address,
            price_usdt=data.get("priceUsdt") or data.get("price_usdt") or data.get("price") or 0,
        )
        return pb.GetTokenPriceResponse(price=price)

    def GetTokenHolders(self, request: Any, context: Any = None) -> pb.GetTokenHoldersResponse:
        page = request.page if request.page else 1
        page_size = request.page_size if request.page_size else 10
        raw = self._get("/token/holders", params={
            "address": request.address,
            "page": page,
            "page_size": page_size,
        })
        data = raw.get("data") or raw
        items = data
        total = 0
        if isinstance(data, dict):
            items = data.get("items") or data.get("holders") or []
            total = data.get("total") or 0
        resp = pb.GetTokenHoldersResponse(total=total)
        for h in items:
            resp.holders.append(pb.TokenHolder(
                address=h.get("address", "") or h.get("owner", "") or "",
                amount=str(h.get("amount", "")) or "",
                decimals=h.get("decimals") or 0,
                rank=h.get("rank") or 0,
                owner_percentage=h.get("ownerPercentage") or h.get("owner_percentage") or 0,
            ))
        return resp

    def GetMarketInfo(self, request: Any, context: Any = None) -> pb.GetMarketInfoResponse:
        raw = self._get(f"/market/token/{request.address}")
        data = raw.get("data") or raw
        market = pb.MarketInfo(
            address=request.address,
            price_usdt=data.get("priceUsdt") or data.get("price_usdt") or data.get("price") or 0,
            volume_24h=data.get("volume24h") or data.get("volume_24h") or 0,
            market_cap=data.get("marketCap") or data.get("market_cap") or 0,
            market_cap_rank=data.get("marketCapRank") or data.get("market_cap_rank") or 0,
            total_supply=str(data.get("totalSupply", "")) or str(data.get("total_supply", "")) or "",
            circulating_supply=str(data.get("circulatingSupply", "")) or str(data.get("circulating_supply", "")) or "",
        )
        return pb.GetMarketInfoResponse(market=market)

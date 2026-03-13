"""OrcaService — wraps the Orca Solana DEX REST API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from orca_mcp.gen.orca.v1 import orca_pb2 as pb

_BASE_URL = "https://api.orca.so/v2/solana"


def _str(val: Any, default: str = "") -> str:
    """Coerce a value to str, treating None as *default*."""
    if val is None:
        return default
    return str(val)


def _parse_pool_token(raw: dict) -> pb.PoolToken:
    return pb.PoolToken(
        address=raw.get("address", ""),
        program_id=raw.get("programId", ""),
        image_url=raw.get("imageUrl", "") or "",
        name=raw.get("name", ""),
        symbol=raw.get("symbol", ""),
        decimals=raw.get("decimals", 0),
        tags=raw.get("tags", []) or [],
    )


def _parse_pool_stats(raw: dict | None) -> pb.PoolStats:
    if not raw:
        return pb.PoolStats()
    return pb.PoolStats(
        volume=_str(raw.get("volume")),
        fees=_str(raw.get("fees")),
        rewards=_str(raw.get("rewards")),
        yield_over_tvl=_str(raw.get("yieldOverTvl")),
    )


def _parse_pool_reward(raw: dict) -> pb.PoolReward:
    return pb.PoolReward(
        mint=raw.get("mint", ""),
        vault=raw.get("vault", ""),
        authority=raw.get("authority", ""),
        emissions_per_second_x64=_str(raw.get("emissions_per_second_x64", raw.get("emissionsPerSecondX64"))),
        growth_global_x64=_str(raw.get("growth_global_x64", raw.get("growthGlobalX64"))),
        active=bool(raw.get("active", False)),
        emissions_per_second=_str(raw.get("emissionsPerSecond")),
    )


def _parse_locked_liquidity(raw: dict) -> pb.LockedLiquidity:
    return pb.LockedLiquidity(
        name=raw.get("name", ""),
        locked_percentage=_str(raw.get("locked_percentage", raw.get("lockedPercentage"))),
    )


def _parse_pool(raw: dict) -> pb.Pool:
    stats = raw.get("stats", {}) or {}
    return pb.Pool(
        address=raw.get("address", ""),
        whirlpools_config=raw.get("whirlpoolsConfig", ""),
        tick_spacing=raw.get("tickSpacing", 0),
        fee_rate=raw.get("feeRate", 0),
        protocol_fee_rate=raw.get("protocolFeeRate", 0),
        liquidity=_str(raw.get("liquidity")),
        sqrt_price=_str(raw.get("sqrtPrice")),
        tick_current_index=raw.get("tickCurrentIndex", 0),
        token_mint_a=raw.get("tokenMintA", ""),
        token_mint_b=raw.get("tokenMintB", ""),
        token_a=_parse_pool_token(raw.get("tokenA", {})),
        token_b=_parse_pool_token(raw.get("tokenB", {})),
        price=_str(raw.get("price")),
        tvl_usdc=_str(raw.get("tvlUsdc")),
        yield_over_tvl=_str(raw.get("yieldOverTvl")),
        token_balance_a=_str(raw.get("tokenBalanceA")),
        token_balance_b=_str(raw.get("tokenBalanceB")),
        stats_24h=_parse_pool_stats(stats.get("24h")),
        stats_7d=_parse_pool_stats(stats.get("7d")),
        stats_30d=_parse_pool_stats(stats.get("30d")),
        rewards=[_parse_pool_reward(r) for r in (raw.get("rewards") or [])],
        locked_liquidity_percent=[
            _parse_locked_liquidity(ll) for ll in (raw.get("lockedLiquidityPercent") or [])
        ],
        has_warning=bool(raw.get("hasWarning", False)),
        pool_type=raw.get("poolType", "") or "",
        updated_at=raw.get("updatedAt", "") or "",
    )


def _parse_token(raw: dict) -> pb.Token:
    meta_raw = raw.get("metadata") or {}
    stats_raw = raw.get("stats") or {}
    stats_24h = stats_raw.get("24h") or {}
    return pb.Token(
        address=raw.get("address", ""),
        supply=raw.get("supply") or 0,
        decimals=raw.get("decimals", 0),
        is_initialized=bool(raw.get("isInitialized", False)),
        token_program=raw.get("tokenProgram", "") or "",
        price_usdc=_str(raw.get("priceUsdc")),
        metadata=pb.TokenMetadata(
            name=meta_raw.get("name", ""),
            symbol=meta_raw.get("symbol", ""),
            description=meta_raw.get("description", "") or "",
            image=meta_raw.get("image", "") or "",
            risk=meta_raw.get("risk", 0) or 0,
        ),
        stats=pb.TokenStats(
            volume_24h=stats_24h.get("volume") or 0,
        ),
        updated_at=raw.get("updatedAt", "") or "",
    )


class OrcaService:
    """Implements OrcaService RPCs via the free Orca REST API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def ListPools(self, request: Any, context: Any = None) -> pb.ListPoolsResponse:
        limit = request.limit if request.limit else 100
        raw = self._get(f"{_BASE_URL}/pools", params={"limit": limit})
        resp = pb.ListPoolsResponse()
        for p in raw.get("data", []):
            resp.pools.append(_parse_pool(p))
        return resp

    def GetPool(self, request: Any, context: Any = None) -> pb.GetPoolResponse:
        raw = self._get(f"{_BASE_URL}/pools/{request.address}")
        data = raw.get("data", raw)
        return pb.GetPoolResponse(pool=_parse_pool(data))

    def SearchPools(self, request: Any, context: Any = None) -> pb.SearchPoolsResponse:
        limit = request.limit if request.limit else 10
        raw = self._get(f"{_BASE_URL}/pools/search", params={"q": request.query, "limit": limit})
        resp = pb.SearchPoolsResponse()
        for p in raw.get("data", []):
            resp.pools.append(_parse_pool(p))
        return resp

    def ListTokens(self, request: Any, context: Any = None) -> pb.ListTokensResponse:
        limit = request.limit if request.limit else 100
        raw = self._get(f"{_BASE_URL}/tokens", params={"limit": limit})
        resp = pb.ListTokensResponse()
        for t in raw.get("data", []):
            resp.tokens.append(_parse_token(t))
        return resp

    def GetToken(self, request: Any, context: Any = None) -> pb.GetTokenResponse:
        raw = self._get(f"{_BASE_URL}/tokens/{request.mint_address}")
        data = raw.get("data", raw)
        return pb.GetTokenResponse(token=_parse_token(data))

    def SearchTokens(self, request: Any, context: Any = None) -> pb.SearchTokensResponse:
        limit = request.limit if request.limit else 10
        raw = self._get(f"{_BASE_URL}/tokens/search", params={"q": request.query, "limit": limit})
        resp = pb.SearchTokensResponse()
        for t in raw.get("data", []):
            resp.tokens.append(_parse_token(t))
        return resp

    def GetProtocolStats(self, request: Any, context: Any = None) -> pb.GetProtocolStatsResponse:
        raw = self._get(f"{_BASE_URL}/protocol")
        return pb.GetProtocolStatsResponse(
            tvl=_str(raw.get("tvl")),
            volume_24h_usdc=_str(raw.get("volume24hUsdc")),
            fees_24h_usdc=_str(raw.get("fees24hUsdc")),
            revenue_24h_usdc=_str(raw.get("revenue24hUsdc")),
        )

    def GetProtocolToken(self, request: Any, context: Any = None) -> pb.GetProtocolTokenResponse:
        raw = self._get(f"{_BASE_URL}/protocol/token")
        stats = raw.get("stats") or {}
        stats_24h = stats.get("24h") or {}
        return pb.GetProtocolTokenResponse(
            symbol=raw.get("symbol", ""),
            name=raw.get("name", ""),
            description=raw.get("description", "") or "",
            image_url=raw.get("imageUrl", "") or "",
            price=_str(raw.get("price")),
            circulating_supply=_str(raw.get("circulatingSupply")),
            total_supply=_str(raw.get("totalSupply")),
            volume_24h=_str(stats_24h.get("volume")),
        )

    def GetLockedLiquidity(self, request: Any, context: Any = None) -> pb.GetLockedLiquidityResponse:
        raw = self._get(f"{_BASE_URL}/pools/{request.address}")
        data = raw.get("data", raw)
        entries = data.get("lockedLiquidityPercent") or []
        resp = pb.GetLockedLiquidityResponse()
        for e in entries:
            resp.entries.append(_parse_locked_liquidity(e))
        return resp

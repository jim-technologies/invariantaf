"""CurveService — wraps the Curve Finance API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from curve_mcp.gen.curve.v1 import curve_pb2 as pb

_BASE_URL = "https://api.curve.finance"


def _to_float(val: Any) -> float:
    """Safely convert a value to float; handles None, strings, and numbers."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _parse_pool(p: dict) -> pb.Pool:
    """Convert a raw pool dict from the Curve API into a Pool proto."""
    coins = []
    for c in p.get("coins", []):
        coins.append(pb.Coin(
            address=c.get("address", ""),
            usd_price=_to_float(c.get("usdPrice")),
            decimals=str(c.get("decimals", "")),
            is_base_pool_lp_token=bool(c.get("isBasePoolLpToken")),
            symbol=c.get("symbol", "") or "",
            name=c.get("name", "") or "",
            pool_balance=str(c.get("poolBalance", "")),
        ))

    gauge_rewards = []
    for gr in p.get("gaugeRewards", []):
        gauge_rewards.append(pb.GaugeReward(
            gauge_address=gr.get("gaugeAddress", "") or "",
            token_price=_to_float(gr.get("tokenPrice")),
            name=gr.get("name", "") or "",
            symbol=gr.get("symbol", "") or "",
            decimals=str(gr.get("decimals", "")),
            apy=_to_float(gr.get("apy")),
            token_address=gr.get("tokenAddress", "") or "",
        ))

    pool_urls_raw = p.get("poolUrls") or {}
    pool_urls = pb.PoolUrls(
        swap=pool_urls_raw.get("swap", []) or [],
        deposit=pool_urls_raw.get("deposit", []) or [],
        withdraw=pool_urls_raw.get("withdraw", []) or [],
    )

    return pb.Pool(
        id=str(p.get("id", "")),
        address=p.get("address", "") or "",
        name=p.get("name", "") or "",
        symbol=p.get("symbol", "") or "",
        asset_type_name=p.get("assetTypeName", "") or "",
        coins=coins,
        usd_total=_to_float(p.get("usdTotal")),
        is_meta_pool=bool(p.get("isMetaPool")),
        amplification_coefficient=str(p.get("amplificationCoefficient", "")),
        virtual_price=str(p.get("virtualPrice", "")),
        lp_token_address=p.get("lpTokenAddress", "") or "",
        implementation=p.get("implementation", "") or "",
        gauge_address=p.get("gaugeAddress", "") or "",
        gauge_rewards=gauge_rewards,
        gauge_crv_apy=[_to_float(x) for x in (p.get("gaugeCrvApy") or []) if x is not None],
        pool_urls=pool_urls,
        total_supply=str(p.get("totalSupply", "")),
        coins_addresses=p.get("coinsAddresses", []) or [],
        decimals=[str(d) for d in (p.get("decimals", []) or [])],
        is_broken=bool(p.get("isBroken")),
        creation_ts=p.get("creationTs") or 0,
        creation_block_number=p.get("creationBlockNumber") or 0,
    )


class CurveService:
    """Implements CurveService RPCs via the free Curve Finance API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()

    def GetPools(self, request: Any, context: Any = None) -> pb.GetPoolsResponse:
        blockchain_id = request.blockchain_id or "ethereum"
        registry_id = request.registry_id or "main"
        raw = self._get(f"{_BASE_URL}/v1/getPools/{blockchain_id}/{registry_id}")
        resp = pb.GetPoolsResponse()
        for p in raw.get("data", {}).get("poolData", []):
            resp.pools.append(_parse_pool(p))
        return resp

    def GetApys(self, request: Any, context: Any = None) -> pb.GetApysResponse:
        raw = self._get(f"{_BASE_URL}/api/getSubgraphData/ethereum")
        resp = pb.GetApysResponse()
        for p in raw.get("data", {}).get("poolList", []):
            resp.pools.append(pb.PoolApy(
                address=p.get("address", ""),
                type=p.get("type", "") or "",
                volume_usd=_to_float(p.get("volumeUSD")),
                latest_daily_apy_pcent=_to_float(p.get("latestDailyApy")),
                latest_weekly_apy_pcent=_to_float(p.get("latestWeeklyApy")),
                included_apy_pcent_from_lsts=0,
                virtual_price=_to_float(p.get("virtualPrice")),
            ))
        return resp

    def GetVolumes(self, request: Any, context: Any = None) -> pb.GetVolumesResponse:
        raw = self._get(f"{_BASE_URL}/v1/getVolumes")
        resp = pb.GetVolumesResponse()
        for p in raw.get("data", {}).get("pools", []):
            resp.pools.append(pb.PoolVolume(
                address=p.get("address", ""),
                type=p.get("type", "") or "",
                volume_usd=_to_float(p.get("volumeUSD")),
                latest_daily_apy_pcent=_to_float(p.get("latestDailyApyPcent")),
                latest_weekly_apy_pcent=_to_float(p.get("latestWeeklyApyPcent")),
                included_apy_pcent_from_lsts=_to_float(p.get("includedApyPcentFromLsts")),
                virtual_price=_to_float(p.get("virtualPrice")),
            ))
        return resp

    def GetTVL(self, request: Any, context: Any = None) -> pb.GetTVLResponse:
        raw = self._get(f"{_BASE_URL}/v1/getTVL")
        resp = pb.GetTVLResponse()
        for p in raw.get("data", {}).get("poolData", []):
            resp.pools.append(_parse_pool(p))
        return resp

    def GetFactoryTVL(self, request: Any, context: Any = None) -> pb.GetFactoryTVLResponse:
        raw = self._get(f"{_BASE_URL}/v1/getFactoryTVL")
        factory_balances = _to_float(raw.get("data", {}).get("factoryBalances"))
        return pb.GetFactoryTVLResponse(factory_balances=factory_balances)

    def GetWeeklyFees(self, request: Any, context: Any = None) -> pb.GetWeeklyFeesResponse:
        raw = self._get(f"{_BASE_URL}/v1/getWeeklyFees")
        data = raw.get("data", {})
        resp = pb.GetWeeklyFeesResponse()
        for entry in data.get("weeklyFeesTable", []):
            resp.weekly_fees.append(pb.WeeklyFeeEntry(
                date=entry.get("date", ""),
                ts=entry.get("ts") or 0,
                raw_fees=_to_float(entry.get("rawFees")),
            ))
        total_fees_data = data.get("totalFees", {})
        resp.total_fees = _to_float(total_fees_data.get("fees"))
        return resp

    def GetETHPrice(self, request: Any, context: Any = None) -> pb.GetETHPriceResponse:
        raw = self._get(f"{_BASE_URL}/v1/getETHprice")
        price = _to_float(raw.get("data", {}).get("price"))
        return pb.GetETHPriceResponse(price=price)

    def GetSubgraphData(self, request: Any, context: Any = None) -> pb.GetSubgraphDataResponse:
        blockchain_id = request.blockchain_id or "ethereum"
        raw = self._get(f"{_BASE_URL}/api/getSubgraphData/{blockchain_id}")
        resp = pb.GetSubgraphDataResponse()
        for p in raw.get("data", {}).get("poolList", []):
            resp.pools.append(pb.SubgraphPool(
                address=p.get("address", ""),
                latest_daily_apy=_to_float(p.get("latestDailyApy")),
                latest_weekly_apy=_to_float(p.get("latestWeeklyApy")),
                type=p.get("type", "") or "",
                volume_usd=_to_float(p.get("volumeUSD")),
                virtual_price=_to_float(p.get("virtualPrice")),
            ))
        return resp

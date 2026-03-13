"""DefiLlamaService — wraps the DeFiLlama free API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from defillama_mcp.gen.defillama.v1 import defillama_pb2 as pb

_BASE_URL = "https://api.llama.fi"
_YIELDS_URL = "https://yields.llama.fi"
_STABLECOINS_URL = "https://stablecoins.llama.fi"


class DefiLlamaService:
    """Implements DefiLlamaService RPCs via the free DeFiLlama API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def GetProtocols(self, request: Any, context: Any = None) -> pb.GetProtocolsResponse:
        raw = self._get(f"{_BASE_URL}/protocols")
        resp = pb.GetProtocolsResponse()
        for p in raw:
            resp.protocols.append(pb.Protocol(
                id=str(p.get("id", "")),
                name=p.get("name", ""),
                symbol=p.get("symbol", "") or "",
                url=p.get("url", "") or "",
                description=p.get("description", "") or "",
                chain=p.get("chain", "") or "",
                logo=p.get("logo", "") or "",
                category=p.get("category", "") or "",
                chains=p.get("chains", []) or [],
                tvl=p.get("tvl") or 0,
                change_1h=p.get("change_1h") or 0,
                change_1d=p.get("change_1d") or 0,
                change_7d=p.get("change_7d") or 0,
                slug=p.get("slug", "") or "",
                twitter=p.get("twitter", "") or "",
                mcap=p.get("mcap") or 0,
            ))
        return resp

    def GetProtocol(self, request: Any, context: Any = None) -> pb.GetProtocolResponse:
        raw = self._get(f"{_BASE_URL}/protocol/{request.slug}")
        tvl_history = []
        for dp in raw.get("tvl", []):
            tvl_history.append(pb.TVLDataPoint(
                date=dp.get("date", 0),
                total_liquidity_usd=dp.get("totalLiquidityUSD", 0),
            ))
        current_chain_tvls = {}
        for chain, val in (raw.get("currentChainTvls") or {}).items():
            if isinstance(val, (int, float)):
                current_chain_tvls[chain] = float(val)
        detail = pb.ProtocolDetail(
            id=str(raw.get("id", "")),
            name=raw.get("name", ""),
            url=raw.get("url", "") or "",
            description=raw.get("description", "") or "",
            logo=raw.get("logo", "") or "",
            symbol=raw.get("symbol", "") or "",
            chains=raw.get("chains", []) or [],
            gecko_id=raw.get("gecko_id", "") or "",
            twitter=raw.get("twitter", "") or "",
            tvl=tvl_history,
            current_chain_tvls=current_chain_tvls,
            mcap=raw.get("mcap") or 0,
            category=raw.get("category", "") or "",
        )
        return pb.GetProtocolResponse(protocol=detail)

    def GetTVL(self, request: Any, context: Any = None) -> pb.GetTVLResponse:
        raw = self._get(f"{_BASE_URL}/tvl/{request.slug}")
        tvl = float(raw) if isinstance(raw, (int, float)) else 0
        return pb.GetTVLResponse(tvl=tvl)

    def GetChains(self, request: Any, context: Any = None) -> pb.GetChainsResponse:
        raw = self._get(f"{_BASE_URL}/v2/chains")
        resp = pb.GetChainsResponse()
        for c in raw:
            resp.chains.append(pb.Chain(
                name=c.get("name", ""),
                tvl=c.get("tvl") or 0,
                token_symbol=c.get("tokenSymbol", "") or "",
                gecko_id=c.get("gecko_id", "") or "",
                chain_id=int(cid) if isinstance(cid := c.get("chainId"), (int, float)) else 0,
            ))
        return resp

    def GetGlobalTVL(self, request: Any, context: Any = None) -> pb.GetGlobalTVLResponse:
        raw = self._get(f"{_BASE_URL}/v2/historicalChainTvl")
        resp = pb.GetGlobalTVLResponse()
        for dp in raw:
            resp.data_points.append(pb.GlobalTVLDataPoint(
                date=dp.get("date", 0),
                tvl=dp.get("tvl") or 0,
            ))
        return resp

    def GetStablecoins(self, request: Any, context: Any = None) -> pb.GetStablecoinsResponse:
        raw = self._get(f"{_STABLECOINS_URL}/stablecoins")
        resp = pb.GetStablecoinsResponse()
        for s in raw.get("peggedAssets", []):
            circ = s.get("circulating", {})
            circ_prev_day = s.get("circulatingPrevDay", {})
            circ_prev_week = s.get("circulatingPrevWeek", {})
            circ_prev_month = s.get("circulatingPrevMonth", {})
            # Sum all peg type values (usually just one key like peggedUSD).
            def _sum_peg(d):
                return sum(v for v in d.values() if isinstance(v, (int, float)))
            resp.stablecoins.append(pb.Stablecoin(
                id=str(s.get("id", "")),
                name=s.get("name", ""),
                symbol=s.get("symbol", "") or "",
                gecko_id=s.get("gecko_id", "") or "",
                peg_type=s.get("pegType", "") or "",
                peg_mechanism=s.get("pegMechanism", "") or "",
                circulating=_sum_peg(circ),
                circulating_prev_day=_sum_peg(circ_prev_day),
                circulating_prev_week=_sum_peg(circ_prev_week),
                circulating_prev_month=_sum_peg(circ_prev_month),
            ))
        return resp

    def GetYieldPools(self, request: Any, context: Any = None) -> pb.GetYieldPoolsResponse:
        raw = self._get(f"{_YIELDS_URL}/pools")
        resp = pb.GetYieldPoolsResponse()
        for p in raw.get("data", []):
            preds = p.get("predictions") or {}
            resp.pools.append(pb.YieldPool(
                pool=p.get("pool", ""),
                chain=p.get("chain", ""),
                project=p.get("project", ""),
                symbol=p.get("symbol", ""),
                tvl_usd=p.get("tvlUsd") or 0,
                apy=p.get("apy") or 0,
                apy_base=p.get("apyBase") or 0,
                apy_reward=p.get("apyReward") or 0,
                stablecoin=bool(p.get("stablecoin")),
                il_risk=p.get("ilRisk", "") or "",
                exposure=p.get("exposure", "") or "",
                apy_pct_1d=p.get("apyPct1D") or 0,
                apy_pct_7d=p.get("apyPct7D") or 0,
                apy_pct_30d=p.get("apyPct30D") or 0,
                predicted_class=preds.get("predictedClass", "") or "",
                predicted_probability=int(preds.get("predictedProbability") or 0),
            ))
        return resp

    def GetDexVolumes(self, request: Any, context: Any = None) -> pb.GetDexVolumesResponse:
        raw = self._get(f"{_BASE_URL}/overview/dexs")
        resp = pb.GetDexVolumesResponse(
            total_24h=raw.get("total24h") or 0,
            total_7d=raw.get("total7d") or 0,
            total_30d=raw.get("total30d") or 0,
            change_1d=raw.get("change_1d") or 0,
            change_7d=raw.get("change_7d") or 0,
            change_1m=raw.get("change_1m") or 0,
            all_chains=raw.get("allChains", []) or [],
        )
        for p in raw.get("protocols", []):
            resp.protocols.append(pb.DexProtocol(
                name=p.get("name", ""),
                slug=p.get("slug", "") or p.get("module", "") or "",
                logo=p.get("logo", "") or "",
                category=p.get("category", "") or "",
                chains=p.get("chains", []) or [],
                total_24h=p.get("total24h") or 0,
                total_7d=p.get("total7d") or 0,
                total_30d=p.get("total30d") or 0,
                change_1d=p.get("change_1d") or 0,
                change_7d=p.get("change_7d") or 0,
                change_1m=p.get("change_1m") or 0,
            ))
        return resp

    def GetFees(self, request: Any, context: Any = None) -> pb.GetFeesResponse:
        raw = self._get(f"{_BASE_URL}/overview/fees")
        resp = pb.GetFeesResponse(
            total_24h=raw.get("total24h") or 0,
            total_7d=raw.get("total7d") or 0,
            total_30d=raw.get("total30d") or 0,
            change_1d=raw.get("change_1d") or 0,
            change_7d=raw.get("change_7d") or 0,
            change_1m=raw.get("change_1m") or 0,
        )
        for p in raw.get("protocols", []):
            resp.protocols.append(pb.FeesProtocol(
                name=p.get("name", ""),
                slug=p.get("slug", "") or p.get("module", "") or "",
                logo=p.get("logo", "") or "",
                category=p.get("category", "") or "",
                chains=p.get("chains", []) or [],
                total_24h=p.get("total24h") or 0,
                total_7d=p.get("total7d") or 0,
                total_30d=p.get("total30d") or 0,
                change_1d=p.get("change_1d") or 0,
                change_7d=p.get("change_7d") or 0,
                change_1m=p.get("change_1m") or 0,
            ))
        return resp

    def GetStablecoinChains(self, request: Any, context: Any = None) -> pb.GetStablecoinChainsResponse:
        raw = self._get(f"{_STABLECOINS_URL}/stablecoinchains")
        resp = pb.GetStablecoinChainsResponse()
        for c in raw:
            circ = c.get("totalCirculatingUSD", {})
            total = sum(v for v in circ.values() if isinstance(v, (int, float)))
            resp.chains.append(pb.StablecoinChain(
                name=c.get("name", ""),
                gecko_id=c.get("gecko_id", "") or "",
                token_symbol=c.get("tokenSymbol", "") or "",
                total_circulating_usd=total,
            ))
        return resp

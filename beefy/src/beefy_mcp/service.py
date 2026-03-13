"""BeefyService — wraps the Beefy Finance public APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from beefy_mcp.gen.beefy.v1 import beefy_pb2 as pb

_BASE_URL = "https://api.beefy.finance"


class BeefyService:
    """Implements BeefyService RPCs via the free Beefy Finance API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def ListVaults(self, request: Any, context: Any = None) -> pb.ListVaultsResponse:
        raw = self._get(f"{_BASE_URL}/vaults")
        resp = pb.ListVaultsResponse()
        for v in raw:
            risks_raw = v.get("risks") or {}
            risks = pb.VaultRisks(
                complex=bool(risks_raw.get("complex")),
                curated=bool(risks_raw.get("curated")),
                not_audited=bool(risks_raw.get("notAudited")),
                not_battle_tested=bool(risks_raw.get("notBattleTested")),
                not_correlated=bool(risks_raw.get("notCorrelated")),
                not_timelocked=bool(risks_raw.get("notTimelocked")),
                not_verified=bool(risks_raw.get("notVerified")),
                synth_asset=bool(risks_raw.get("synthAsset")),
            )
            resp.vaults.append(pb.Vault(
                id=v.get("id", ""),
                name=v.get("name", ""),
                type=v.get("type", "") or "",
                token=v.get("token", "") or "",
                token_address=v.get("tokenAddress", "") or "",
                token_decimals=v.get("tokenDecimals") or 0,
                earn_contract_address=v.get("earnContractAddress", "") or "",
                earned_token=v.get("earnedToken", "") or "",
                status=v.get("status", "") or "",
                chain=v.get("chain", "") or v.get("network", "") or "",
                platform_id=v.get("platformId", "") or "",
                assets=v.get("assets", []) or [],
                strategy_type_id=v.get("strategyTypeId", "") or "",
                risks=risks,
                created_at=v.get("createdAt") or 0,
                strategy=v.get("strategy", "") or "",
                last_harvest=v.get("lastHarvest") or 0,
                price_per_full_share=str(v.get("pricePerFullShare", "")) or "",
                is_gov_vault=bool(v.get("isGovVault")),
            ))
        return resp

    def GetApys(self, request: Any, context: Any = None) -> pb.GetApysResponse:
        raw = self._get(f"{_BASE_URL}/apy")
        resp = pb.GetApysResponse()
        for vault_id, apy in raw.items():
            resp.apys.append(pb.VaultApy(
                vault_id=vault_id,
                apy=apy if isinstance(apy, (int, float)) else 0,
            ))
        return resp

    def GetApyBreakdown(self, request: Any, context: Any = None) -> pb.GetApyBreakdownResponse:
        raw = self._get(f"{_BASE_URL}/apy/breakdown")
        resp = pb.GetApyBreakdownResponse()
        for vault_id, bd in raw.items():
            if not isinstance(bd, dict):
                continue
            resp.breakdowns.append(pb.ApyBreakdown(
                vault_id=vault_id,
                total_apy=bd.get("totalApy") or 0,
                vault_apr=bd.get("vaultApr") or 0,
                compoundings_per_year=bd.get("compoundingsPerYear") or 0,
                beefy_performance_fee=bd.get("beefyPerformanceFee") or 0,
                lp_fee=bd.get("lpFee") or 0,
                trading_apr=bd.get("tradingApr") or 0,
                boost_apr=bd.get("boostApr") or 0,
            ))
        return resp

    def GetTVL(self, request: Any, context: Any = None) -> pb.GetTVLResponse:
        raw = self._get(f"{_BASE_URL}/tvl")
        resp = pb.GetTVLResponse()
        for chain_id, vaults in raw.items():
            if not isinstance(vaults, dict):
                continue
            chain_tvl = pb.ChainTVL(chain_id=str(chain_id))
            for vault_id, tvl in vaults.items():
                chain_tvl.vaults.append(pb.VaultTVL(
                    vault_id=vault_id,
                    tvl_usd=tvl if isinstance(tvl, (int, float)) else 0,
                ))
            resp.chains.append(chain_tvl)
        return resp

    def GetFees(self, request: Any, context: Any = None) -> pb.GetFeesResponse:
        raw = self._get(f"{_BASE_URL}/fees")
        resp = pb.GetFeesResponse()
        for vault_id, fee_data in raw.items():
            if not isinstance(fee_data, dict):
                continue
            perf_raw = fee_data.get("performance") or {}
            performance = pb.PerformanceFees(
                total=perf_raw.get("total") or 0,
                strategist=perf_raw.get("strategist") or 0,
                call=perf_raw.get("call") or 0,
                treasury=perf_raw.get("treasury") or 0,
                stakers=perf_raw.get("stakers") or 0,
            )
            resp.fees.append(pb.VaultFees(
                vault_id=vault_id,
                performance=performance,
                withdraw=fee_data.get("withdraw") or 0,
                deposit=fee_data.get("deposit") or 0,
                last_updated=fee_data.get("lastUpdated") or 0,
            ))
        return resp

    def GetLPPrices(self, request: Any, context: Any = None) -> pb.GetLPPricesResponse:
        raw = self._get(f"{_BASE_URL}/lps")
        resp = pb.GetLPPricesResponse()
        for lp_id, price in raw.items():
            resp.prices.append(pb.LPPrice(
                lp_id=lp_id,
                price=price if isinstance(price, (int, float)) else 0,
            ))
        return resp

    def GetBoosts(self, request: Any, context: Any = None) -> pb.GetBoostsResponse:
        raw = self._get(f"{_BASE_URL}/boosts")
        resp = pb.GetBoostsResponse()
        for b in raw:
            resp.boosts.append(pb.Boost(
                id=b.get("id", ""),
                name=b.get("name", ""),
                chain=b.get("chain", "") or "",
                pool_id=b.get("poolId", "") or "",
                assets=b.get("assets", []) or [],
                status=b.get("status", "") or "",
                earn_contract_address=b.get("earnContractAddress", "") or "",
                earned_token=b.get("earnedToken", "") or "",
                earned_token_decimals=b.get("earnedTokenDecimals") or 0,
                earned_token_address=b.get("earnedTokenAddress", "") or "",
                partners=b.get("partners", []) or [],
                is_moo_staked=bool(b.get("isMooStaked")),
                period_finish=b.get("periodFinish") or 0,
            ))
        return resp

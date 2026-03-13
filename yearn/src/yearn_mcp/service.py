"""YearnService -- wraps the yDaemon API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from yearn_mcp.gen.yearn.v1 import yearn_pb2 as pb

_BASE_URL = "https://ydaemon.yearn.fi"

# Supported chain IDs.
_SUPPORTED_CHAINS = [1, 10, 137, 250, 42161, 8453]


def _parse_vault(v: dict) -> pb.Vault:
    """Parse a raw yDaemon vault JSON object into a Vault proto message."""
    # Token info.
    raw_token = v.get("token") or {}
    token = pb.TokenInfo(
        address=raw_token.get("address", "") or "",
        name=raw_token.get("name", "") or "",
        symbol=raw_token.get("symbol", "") or "",
        decimals=raw_token.get("decimals") or 0,
        description=raw_token.get("description", "") or "",
        underlying_tokens_addresses=raw_token.get("underlyingTokensAddresses") or [],
    )

    # TVL.
    raw_tvl = v.get("tvl") or {}
    tvl = pb.VaultTVL(
        total_assets=str(raw_tvl.get("totalAssets", "")) or "",
        tvl_usd=raw_tvl.get("tvl") or 0,
        price=raw_tvl.get("price") or 0,
    )

    # APR.
    raw_apr = v.get("apr") or {}
    raw_points = raw_apr.get("points") or {}
    raw_forward = raw_apr.get("forwardAPR") or {}
    raw_composite = raw_forward.get("composite") or {}
    composite = pb.CompositeAPR(
        boost=raw_composite.get("boost") or 0,
        pool_apy=raw_composite.get("poolAPY") or 0,
        boosted_apr=raw_composite.get("boostedAPR") or 0,
        base_apr=raw_composite.get("baseAPR") or 0,
        cvx_apr=raw_composite.get("cvxAPR") or 0,
        rewards_apr=raw_composite.get("rewardsAPR") or 0,
    )
    apr = pb.VaultAPR(
        type=raw_apr.get("type", "") or "",
        net_apr=raw_apr.get("netAPR") or 0,
        week_ago=raw_points.get("weekAgo") or 0,
        month_ago=raw_points.get("monthAgo") or 0,
        inception=raw_points.get("inception") or 0,
        forward_apr=raw_forward.get("netAPR") or 0,
        composite=composite,
    )

    # Fees.
    raw_fees = (raw_apr.get("fees") or {})
    fees = pb.VaultFees(
        performance=raw_fees.get("performance") or 0,
        management=raw_fees.get("management") or 0,
    )

    # Strategies.
    strategies = []
    for s in v.get("strategies") or []:
        s_details = s.get("details") or {}
        strategies.append(pb.StrategyDetail(
            address=s.get("address", "") or "",
            name=s.get("name", "") or "",
            status=s.get("status", "") or "",
            total_debt=str(s_details.get("totalDebt", "")) or "",
            total_loss=str(s_details.get("totalLoss", "")) or "",
            total_gain=str(s_details.get("totalGain", "")) or "",
            performance_fee=s_details.get("performanceFee") or 0,
            last_report=s_details.get("lastReport") or 0,
            debt_ratio=s_details.get("debtRatio") or 0,
        ))

    # Details.
    raw_details = v.get("details") or {}
    details = pb.VaultDetails(
        is_retired=bool(raw_details.get("isRetired")),
        is_hidden=bool(raw_details.get("isHidden")),
        is_boosted=bool(raw_details.get("isBoosted")),
        is_automated=bool(raw_details.get("isAutomated")),
        is_pool=bool(raw_details.get("isPool")),
        pool_provider=raw_details.get("poolProvider", "") or "",
        stability=raw_details.get("stability", "") or "",
        category=raw_details.get("category", "") or "",
    )

    return pb.Vault(
        address=v.get("address", "") or "",
        name=v.get("name", "") or "",
        display_name=v.get("displayName", "") or "",
        symbol=v.get("symbol", "") or "",
        display_symbol=v.get("displaySymbol", "") or "",
        icon=v.get("icon", "") or "",
        version=v.get("version", "") or "",
        type=v.get("type", "") or "",
        category=v.get("category", "") or "",
        decimals=v.get("decimals") or 0,
        chain_id=v.get("chainID") or 0,
        endorsed=bool(v.get("endorsed")),
        boosted=bool(v.get("boosted")),
        emergency_shutdown=bool(v.get("emergency_shutdown")),
        token=token,
        tvl=tvl,
        apr=apr,
        fees=fees,
        strategies=strategies,
        details=details,
        price_per_share=str(v.get("pricePerShare", "")) or "",
        featuring_score=v.get("featuringScore") or 0,
        kind=v.get("kind", "") or "",
    )


class YearnService:
    """Implements YearnService RPCs via the free yDaemon API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def ListVaults(self, request: Any, context: Any = None) -> pb.ListVaultsResponse:
        chain_id = request.chain_id if request.chain_id else 1
        raw = self._get(f"{_BASE_URL}/{chain_id}/vaults/all")
        resp = pb.ListVaultsResponse()
        for v in raw:
            resp.vaults.append(_parse_vault(v))
        return resp

    def GetVault(self, request: Any, context: Any = None) -> pb.GetVaultResponse:
        chain_id = request.chain_id if request.chain_id else 1
        raw = self._get(f"{_BASE_URL}/{chain_id}/vaults/{request.address}")
        vault = _parse_vault(raw)
        return pb.GetVaultResponse(vault=vault)

    def ListAllVaults(self, request: Any, context: Any = None) -> pb.ListAllVaultsResponse:
        resp = pb.ListAllVaultsResponse()
        for chain_id in _SUPPORTED_CHAINS:
            try:
                raw = self._get(f"{_BASE_URL}/{chain_id}/vaults/all")
                for v in raw:
                    resp.vaults.append(_parse_vault(v))
            except Exception:
                # Skip chains that fail (may be temporarily unavailable).
                continue
        return resp

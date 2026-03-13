"""MarinadeService -- wraps the Marinade Finance public APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from marinade_mcp.gen.marinade.v1 import marinade_pb2 as pb

_MARINADE_API_URL = "https://api.marinade.finance"
_VALIDATORS_API_URL = "https://validators-api.marinade.finance"


class MarinadeService:
    """Implements MarinadeService RPCs via the free Marinade APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def GetStakeStats(self, request: Any, context: Any = None) -> pb.GetStakeStatsResponse:
        raw = self._get(f"{_MARINADE_API_URL}/msol/apy/30d")
        return pb.GetStakeStatsResponse(
            apy=raw.get("value", 0),
            start_time=raw.get("start_time", ""),
            end_time=raw.get("end_time", ""),
            start_price=raw.get("start_price", 0),
            end_price=raw.get("end_price", 0),
        )

    def ListValidators(self, request: Any, context: Any = None) -> pb.ListValidatorsResponse:
        limit = request.limit if hasattr(request, "limit") and request.limit else 10
        offset = request.offset if hasattr(request, "offset") and request.offset else 0
        raw = self._get(
            f"{_VALIDATORS_API_URL}/validators",
            params={"limit": limit, "offset": offset},
        )
        validators = []
        for v in raw.get("validators", []):
            validators.append(_parse_validator(v))
        return pb.ListValidatorsResponse(validators=validators)

    def GetValidatorInfo(self, request: Any, context: Any = None) -> pb.GetValidatorInfoResponse:
        vote_account = request.vote_account if hasattr(request, "vote_account") else ""
        raw = self._get(
            f"{_VALIDATORS_API_URL}/validators",
            params={"limit": 1, "offset": 0, "query": vote_account},
        )
        validators = raw.get("validators", [])
        if not validators:
            return pb.GetValidatorInfoResponse()
        return pb.GetValidatorInfoResponse(validator=_parse_validator(validators[0]))

    def GetMSOLPrice(self, request: Any, context: Any = None) -> pb.GetMSOLPriceResponse:
        raw = self._get(f"{_MARINADE_API_URL}/msol/price_sol")
        # The API returns a bare number (float).
        price = raw if isinstance(raw, (int, float)) else 0
        return pb.GetMSOLPriceResponse(price_sol=price)


def _parse_validator(v: dict) -> pb.ValidatorInfo:
    """Convert a raw validator dict from the Marinade API into a proto message."""
    # Grab skip_rate from most recent completed epoch stats (the one with a non-null apy).
    skip_rate = 0.0
    for es in v.get("epoch_stats", []):
        if es.get("apy") is not None:
            skip_rate = es.get("skip_rate", 0) or 0
            break

    return pb.ValidatorInfo(
        identity=v.get("identity", ""),
        vote_account=v.get("vote_account", ""),
        info_name=v.get("info_name", ""),
        info_url=v.get("info_url", "") or "",
        info_icon_url=v.get("info_icon_url", "") or "",
        commission_advertised=v.get("commission_advertised", 0) or 0,
        activated_stake=v.get("activated_stake", "0") or "0",
        marinade_stake=v.get("marinade_stake", "0") or "0",
        version=v.get("version", ""),
        superminority=v.get("superminority", False),
        credits=v.get("credits", 0) or 0,
        score=v.get("score", 0) or 0,
        dc_city=v.get("dc_city", "") or "",
        dc_country=v.get("dc_country", "") or "",
        avg_uptime_pct=v.get("avg_uptime_pct", 0) or 0,
        avg_apy=v.get("avg_apy", 0) or 0,
        epochs_count=v.get("epochs_count", 0) or 0,
        skip_rate=skip_rate,
    )

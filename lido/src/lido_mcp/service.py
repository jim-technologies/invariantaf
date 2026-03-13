"""LidoService — wraps the Lido public APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from lido_mcp.gen.lido.v1 import lido_pb2 as pb

_ETH_API_URL = "https://eth-api.lido.fi"
_WQ_API_URL = "https://wq-api.lido.fi"


class LidoService:
    """Implements LidoService RPCs via the free Lido APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def GetStETHApr(self, request: Any, context: Any = None) -> pb.GetStETHAprResponse:
        raw = self._get(f"{_ETH_API_URL}/v1/protocol/steth/apr/last")
        data = raw.get("data", {})
        meta = raw.get("meta", {})
        return pb.GetStETHAprResponse(
            data=pb.AprDataPoint(
                time_unix=data.get("timeUnix", 0),
                apr=data.get("apr", 0),
            ),
            meta=pb.TokenMeta(
                symbol=meta.get("symbol", ""),
                address=meta.get("address", ""),
                chain_id=meta.get("chainId", 0),
            ),
        )

    def GetStETHAprSMA(self, request: Any, context: Any = None) -> pb.GetStETHAprSMAResponse:
        raw = self._get(f"{_ETH_API_URL}/v1/protocol/steth/apr/sma")
        data = raw.get("data", {})
        meta = raw.get("meta", {})
        aprs = []
        for dp in data.get("aprs", []):
            aprs.append(pb.AprDataPoint(
                time_unix=dp.get("timeUnix", 0),
                apr=dp.get("apr", 0),
            ))
        return pb.GetStETHAprSMAResponse(
            aprs=aprs,
            sma_apr=data.get("smaApr", 0),
            meta=pb.TokenMeta(
                symbol=meta.get("symbol", ""),
                address=meta.get("address", ""),
                chain_id=meta.get("chainId", 0),
            ),
        )

    def GetWithdrawalTime(self, request: Any, context: Any = None) -> pb.GetWithdrawalTimeResponse:
        amount = request.amount if hasattr(request, "amount") and request.amount else 1
        raw = self._get(
            f"{_WQ_API_URL}/v2/request-time/calculate",
            params={"amount": amount},
        )
        req_info = raw.get("requestInfo", {})
        return pb.GetWithdrawalTimeResponse(
            request_info=pb.WithdrawalRequestInfo(
                finalization_in=req_info.get("finalizationIn", 0),
                finalization_at=req_info.get("finalizationAt", ""),
                type=req_info.get("type", ""),
            ),
            status=raw.get("status", ""),
            next_calculation_at=raw.get("nextCalculationAt", ""),
        )

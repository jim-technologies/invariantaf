"""PollingService -- wraps PredictIt and Metaculus APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from polling_mcp.gen.polling.v1 import polling_pb2 as pb

_PREDICTIT_BASE = "https://www.predictit.org/api/marketdata"
_METACULUS_BASE = "https://www.metaculus.com/api2/questions"


def _parse_contract(c: dict) -> pb.PredictItContract:
    """Parse a raw PredictIt contract JSON object into a proto message."""
    return pb.PredictItContract(
        id=c.get("id") or 0,
        date_end=c.get("dateEnd", "") or "",
        name=c.get("name", "") or "",
        short_name=c.get("shortName", "") or "",
        status=c.get("status", "") or "",
        last_trade_price=c.get("lastTradePrice") or 0,
        best_buy_yes_cost=c.get("bestBuyYesCost") or 0,
        best_buy_no_cost=c.get("bestBuyNoCost") or 0,
        best_sell_yes_cost=c.get("bestSellYesCost") or 0,
        best_sell_no_cost=c.get("bestSellNoCost") or 0,
        last_close_price=c.get("lastClosePrice") or 0,
    )


def _parse_market(m: dict) -> pb.PredictItMarket:
    """Parse a raw PredictIt market JSON object into a proto message."""
    contracts = []
    for c in m.get("contracts") or []:
        contracts.append(_parse_contract(c))

    return pb.PredictItMarket(
        id=m.get("id") or 0,
        name=m.get("name", "") or "",
        short_name=m.get("shortName", "") or "",
        url=m.get("url", "") or "",
        status=m.get("status", "") or "",
        timestamp=m.get("timeStamp", "") or "",
        image=m.get("image", "") or "",
        contracts=contracts,
    )


def _parse_question(q: dict) -> pb.MetaculusQuestion:
    """Parse a raw Metaculus question JSON object into a proto message."""
    # Community prediction can be nested in different ways.
    community_pred = 0.0
    prediction_data = q.get("community_prediction") or {}
    if isinstance(prediction_data, dict):
        # Try the "full" key first, then "history" last value.
        full = prediction_data.get("full")
        if isinstance(full, dict):
            community_pred = full.get("q2") or full.get("median") or 0.0
        elif isinstance(full, (int, float)):
            community_pred = float(full)
    elif isinstance(prediction_data, (int, float)):
        community_pred = float(prediction_data)

    resolution = q.get("resolution") if q.get("resolution") is not None else -1
    if resolution is None:
        resolution = -1

    return pb.MetaculusQuestion(
        id=q.get("id") or 0,
        title=q.get("title", "") or "",
        url=q.get("url", "") or "",
        created_time=q.get("created_time", "") or "",
        publish_time=q.get("publish_time", "") or "",
        close_time=q.get("close_time", "") or "",
        resolve_time=q.get("resolve_time", "") or "",
        number_of_predictions=q.get("number_of_predictions") or 0,
        status=q.get("status", "") or "",
        type=q.get("type", "") or "",
        community_prediction=community_pred,
        title_short=q.get("title_short", "") or "",
        resolution=float(resolution),
    )


class PollingService:
    """Implements PollingService RPCs via PredictIt and Metaculus APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def ListPredictItMarkets(self, request: Any, context: Any = None) -> pb.ListPredictItMarketsResponse:
        raw = self._get(f"{_PREDICTIT_BASE}/all/")
        resp = pb.ListPredictItMarketsResponse()
        for m in raw.get("markets") or []:
            resp.markets.append(_parse_market(m))
        return resp

    def GetPredictItMarket(self, request: Any, context: Any = None) -> pb.GetPredictItMarketResponse:
        ticker = request.ticker
        raw = self._get(f"{_PREDICTIT_BASE}/ticker/{ticker}/")
        market = _parse_market(raw)
        return pb.GetPredictItMarketResponse(market=market)

    def ListMetaculusQuestions(self, request: Any, context: Any = None) -> pb.ListMetaculusQuestionsResponse:
        limit = request.limit if request.limit else 20
        offset = request.offset if request.offset else 0
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": "-activity",
        }
        raw = self._get(f"{_METACULUS_BASE}/", params=params)
        resp = pb.ListMetaculusQuestionsResponse()
        for q in raw.get("results") or []:
            resp.questions.append(_parse_question(q))
        return resp

    def GetMetaculusQuestion(self, request: Any, context: Any = None) -> pb.GetMetaculusQuestionResponse:
        question_id = request.id
        raw = self._get(f"{_METACULUS_BASE}/{question_id}/")
        question = _parse_question(raw)
        return pb.GetMetaculusQuestionResponse(question=question)

"""Unit tests -- every PollingService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from polling_mcp.gen.polling.v1 import polling_pb2 as pb
from tests.conftest import (
    FAKE_PREDICTIT_ALL,
    FAKE_PREDICTIT_TICKER,
    FAKE_PREDICTIT_MARKET_1,
    FAKE_PREDICTIT_MARKET_2,
    FAKE_PREDICTIT_CONTRACT_1,
    FAKE_PREDICTIT_CONTRACT_2,
    FAKE_METACULUS_LIST,
    FAKE_METACULUS_QUESTION_1,
    FAKE_METACULUS_QUESTION_2,
    FAKE_METACULUS_RESOLVED,
)


class TestListPredictItMarkets:
    def test_returns_markets(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        assert len(resp.markets) == 2

    def test_market_basic_fields(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        m = resp.markets[0]
        assert m.id == 7456
        assert m.name == "Which party will win the 2024 presidential election?"
        assert m.short_name == "2024 Presidential Election"
        assert m.url == "https://www.predictit.org/markets/detail/7456"
        assert m.status == "Open"
        assert m.timestamp == "2024-06-15T12:30:00Z"

    def test_market_contracts(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        m = resp.markets[0]
        assert len(m.contracts) == 2

    def test_contract_fields(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        c = resp.markets[0].contracts[0]
        assert c.id == 28901
        assert c.name == "Republican"
        assert c.short_name == "Republican"
        assert c.status == "Open"
        assert c.last_trade_price == 0.55
        assert c.best_buy_yes_cost == 0.56
        assert c.best_buy_no_cost == 0.46
        assert c.best_sell_yes_cost == 0.54
        assert c.best_sell_no_cost == 0.44
        assert c.last_close_price == 0.54

    def test_democratic_contract(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        c = resp.markets[0].contracts[1]
        assert c.id == 28902
        assert c.name == "Democratic"
        assert c.last_trade_price == 0.48

    def test_second_market(self, service):
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        m = resp.markets[1]
        assert m.id == 7500
        assert m.name == "Will there be a government shutdown in 2024?"
        assert len(m.contracts) == 1
        assert m.contracts[0].last_trade_price == 0.35

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"markets": []})
        )
        resp = service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        assert len(resp.markets) == 0

    def test_calls_correct_url(self, service, mock_http):
        service.ListPredictItMarkets(pb.ListPredictItMarketsRequest())
        call_url = mock_http.get.call_args[0][0]
        assert "/api/marketdata/all/" in call_url


class TestGetPredictItMarket:
    def test_returns_market(self, service):
        resp = service.GetPredictItMarket(pb.GetPredictItMarketRequest(ticker="PARTY.PRES2024"))
        assert resp.market is not None
        assert resp.market.id == 7456

    def test_market_fields(self, service):
        resp = service.GetPredictItMarket(pb.GetPredictItMarketRequest(ticker="PARTY.PRES2024"))
        m = resp.market
        assert m.name == "Which party will win the 2024 presidential election?"
        assert m.short_name == "2024 Presidential Election"
        assert len(m.contracts) == 2

    def test_calls_correct_url(self, service, mock_http):
        service.GetPredictItMarket(pb.GetPredictItMarketRequest(ticker="PARTY.PRES2024"))
        call_url = mock_http.get.call_args[0][0]
        assert "/api/marketdata/ticker/PARTY.PRES2024/" in call_url

    def test_contract_prices(self, service):
        resp = service.GetPredictItMarket(pb.GetPredictItMarketRequest(ticker="PARTY.PRES2024"))
        c = resp.market.contracts[0]
        assert c.last_trade_price == 0.55
        assert c.best_buy_yes_cost == 0.56


class TestListMetaculusQuestions:
    def test_returns_questions(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        assert len(resp.questions) == 3

    def test_question_basic_fields(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        q = resp.questions[0]
        assert q.id == 10001
        assert q.title == "Will AI pass the Turing test by 2030?"
        assert q.url == "https://www.metaculus.com/questions/10001/"
        assert q.status == "open"
        assert q.type == "binary"
        assert q.number_of_predictions == 1250
        assert q.title_short == "AI Turing Test 2030"

    def test_community_prediction(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        q = resp.questions[0]
        assert q.community_prediction == 0.72

    def test_second_question(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        q = resp.questions[1]
        assert q.id == 10002
        assert q.title == "Will the US enter a recession in 2025?"
        assert q.community_prediction == 0.38

    def test_resolved_question(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        q = resp.questions[2]
        assert q.id == 9999
        assert q.status == "resolved"
        assert q.resolution == 1.0
        assert q.community_prediction == 0.65

    def test_unresolved_question_resolution(self, service):
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        q = resp.questions[0]
        assert q.resolution == -1.0

    def test_default_limit(self, service, mock_http):
        service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1].get("params") if call_kwargs[1] else call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        assert params.get("limit") == 20

    def test_custom_limit(self, service, mock_http):
        service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest(limit=50, offset=10))
        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1].get("params") if call_kwargs[1] else {}
        assert params.get("limit") == 50
        assert params.get("offset") == 10

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"results": []})
        )
        resp = service.ListMetaculusQuestions(pb.ListMetaculusQuestionsRequest())
        assert len(resp.questions) == 0


class TestGetMetaculusQuestion:
    def test_returns_question(self, service):
        resp = service.GetMetaculusQuestion(pb.GetMetaculusQuestionRequest(id=10001))
        assert resp.question is not None
        assert resp.question.id == 10001

    def test_question_fields(self, service):
        resp = service.GetMetaculusQuestion(pb.GetMetaculusQuestionRequest(id=10001))
        q = resp.question
        assert q.title == "Will AI pass the Turing test by 2030?"
        assert q.community_prediction == 0.72
        assert q.type == "binary"
        assert q.number_of_predictions == 1250

    def test_calls_correct_url(self, service, mock_http):
        service.GetMetaculusQuestion(pb.GetMetaculusQuestionRequest(id=10001))
        call_url = mock_http.get.call_args[0][0]
        assert "/api2/questions/10001/" in call_url

    def test_resolved_question(self, service):
        resp = service.GetMetaculusQuestion(pb.GetMetaculusQuestionRequest(id=9999))
        q = resp.question
        assert q.status == "resolved"
        assert q.resolution == 1.0
        assert q.title == "Will inflation exceed 5% in 2023?"

    def test_timestamps(self, service):
        resp = service.GetMetaculusQuestion(pb.GetMetaculusQuestionRequest(id=10001))
        q = resp.question
        assert q.created_time == "2023-01-15T10:00:00Z"
        assert q.publish_time == "2023-01-16T10:00:00Z"
        assert q.close_time == "2029-12-31T23:59:59Z"
        assert q.resolve_time == "2030-06-30T23:59:59Z"

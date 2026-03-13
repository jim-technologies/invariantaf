"""Unit tests -- every SolscanService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from solscan_mcp.gen.solscan.v1 import solscan_pb2 as pb
from tests.conftest import (
    FAKE_ACCOUNT_INFO,
    FAKE_ACCOUNT_TOKENS,
    FAKE_ACCOUNT_TRANSACTIONS,
    FAKE_TOKEN_META,
    FAKE_TOKEN_PRICE,
    FAKE_TOKEN_HOLDERS,
    FAKE_MARKET_INFO,
)


class TestGetAccountInfo:
    def test_returns_account(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account is not None

    def test_account_address(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.address == "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg"

    def test_account_lamports(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.lamports == 1000000000

    def test_account_owner(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.owner == "11111111111111111111111111111111"

    def test_account_type(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.type == "system"

    def test_account_rent_epoch(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.rent_epoch == 361

    def test_account_not_executable(self, service):
        resp = service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.account.executable is False

    def test_calls_correct_endpoint(self, service, mock_http):
        service.GetAccountInfo(pb.GetAccountInfoRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        call_url = mock_http.get.call_args[0][0]
        assert "/account" in call_url


class TestGetAccountTokens:
    def test_returns_tokens(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert len(resp.tokens) == 2

    def test_first_token_address(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].token_address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def test_first_token_account(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].token_account == "3emsAVdmGKoHve6pchAm15mfKgAsHnWnoZFpoKSfGBJJ"

    def test_first_token_amount(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].amount == "50000000"

    def test_first_token_decimals(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].token_decimals == 6

    def test_first_token_name(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].token_name == "USD Coin"

    def test_first_token_symbol(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[0].token_symbol == "USDC"

    def test_second_token(self, service):
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.tokens[1].token_address == "So11111111111111111111111111111111111111112"
        assert resp.tokens[1].token_symbol == "SOL"
        assert resp.tokens[1].amount == "2000000000"
        assert resp.tokens[1].token_decimals == 9

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"success": True, "data": []}),
        )
        resp = service.GetAccountTokens(pb.GetAccountTokensRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert len(resp.tokens) == 0


class TestGetAccountTransactions:
    def test_returns_transactions(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert len(resp.transactions) == 2

    def test_first_tx_hash(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].tx_hash == "5jGv8dCGxB1Mh6wGBzRfhGLfpDhWfJqdeQ8Ka1u8n7Rg4jYVmV5gCR3Z7m1FCp8kF5zTgXjWdJwJjFrX8vN2nFe"

    def test_first_tx_block_id(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].block_id == 250000000

    def test_first_tx_block_time(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].block_time == 1700000000

    def test_first_tx_status(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].status == "Success"

    def test_first_tx_fee(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].fee == 5000

    def test_first_tx_signer(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[0].signer == "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg"

    def test_default_limit(self, service, mock_http):
        service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        call_params = mock_http.get.call_args[1].get("params") or mock_http.get.call_args[0][1] if len(mock_http.get.call_args[0]) > 1 else mock_http.get.call_args[1].get("params")
        assert call_params["limit"] == 10

    def test_custom_limit(self, service, mock_http):
        service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
            limit=5,
        ))
        call_params = mock_http.get.call_args[1].get("params") or mock_http.get.call_args[0][1] if len(mock_http.get.call_args[0]) > 1 else mock_http.get.call_args[1].get("params")
        assert call_params["limit"] == 5

    def test_second_transaction(self, service):
        resp = service.GetAccountTransactions(pb.GetAccountTransactionsRequest(
            address="vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        ))
        assert resp.transactions[1].block_id == 249999999
        assert resp.transactions[1].block_time == 1699999500


class TestGetTokenMeta:
    def test_returns_token(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token is not None

    def test_token_address(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def test_token_name(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.name == "USD Coin"

    def test_token_symbol(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.symbol == "USDC"

    def test_token_decimals(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.decimals == 6

    def test_token_icon(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert "logo.png" in resp.token.icon

    def test_token_website(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.website == "https://www.centre.io/"

    def test_token_twitter(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.twitter == "circle"

    def test_token_tag(self, service):
        resp = service.GetTokenMeta(pb.GetTokenMetaRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.token.tag == "stablecoin"


class TestGetTokenPrice:
    def test_returns_price(self, service):
        resp = service.GetTokenPrice(pb.GetTokenPriceRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.price is not None

    def test_price_value(self, service):
        resp = service.GetTokenPrice(pb.GetTokenPriceRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.price.price_usdt == 1.0001

    def test_price_address(self, service):
        resp = service.GetTokenPrice(pb.GetTokenPriceRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.price.address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class TestGetTokenHolders:
    def test_returns_holders(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert len(resp.holders) == 2

    def test_total_count(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.total == 500000

    def test_first_holder_address(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.holders[0].address == "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"

    def test_first_holder_amount(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.holders[0].amount == "10000000000"

    def test_first_holder_rank(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.holders[0].rank == 1

    def test_first_holder_percentage(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.holders[0].owner_percentage == 5.5

    def test_second_holder(self, service):
        resp = service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.holders[1].address == "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT"
        assert resp.holders[1].rank == 2
        assert resp.holders[1].owner_percentage == 2.75

    def test_default_pagination(self, service, mock_http):
        service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        call_params = mock_http.get.call_args[1].get("params") or mock_http.get.call_args[0][1] if len(mock_http.get.call_args[0]) > 1 else mock_http.get.call_args[1].get("params")
        assert call_params["page"] == 1
        assert call_params["page_size"] == 10

    def test_custom_pagination(self, service, mock_http):
        service.GetTokenHolders(pb.GetTokenHoldersRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            page=2,
            page_size=20,
        ))
        call_params = mock_http.get.call_args[1].get("params") or mock_http.get.call_args[0][1] if len(mock_http.get.call_args[0]) > 1 else mock_http.get.call_args[1].get("params")
        assert call_params["page"] == 2
        assert call_params["page_size"] == 20


class TestGetMarketInfo:
    def test_returns_market(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market is not None

    def test_market_price(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.price_usdt == 1.0001

    def test_market_volume(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.volume_24h == 5000000000.0

    def test_market_cap(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.market_cap == 32000000000.0

    def test_market_cap_rank(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.market_cap_rank == 7

    def test_market_total_supply(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.total_supply == "40000000000000000"

    def test_market_circulating_supply(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.circulating_supply == "32000000000000000"

    def test_market_address(self, service):
        resp = service.GetMarketInfo(pb.GetMarketInfoRequest(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        ))
        assert resp.market.address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

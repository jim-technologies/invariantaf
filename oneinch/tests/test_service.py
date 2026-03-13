"""Unit tests — every OneInchService RPC method, mocked HTTP."""

from unittest.mock import MagicMock

from oneinch_mcp.gen.oneinch.v1 import oneinch_pb2 as pb
from tests.conftest import (
    FAKE_BALANCES,
    FAKE_QUOTE,
    FAKE_SEARCH_TOKENS,
    FAKE_SWAP,
    FAKE_TOKEN_INFO,
    FAKE_TOKEN_PRICES,
    NATIVE_TOKEN,
    USDC_ADDRESS,
    WALLET_ADDRESS,
    WETH_ADDRESS,
)


class TestGetQuote:
    def test_returns_quote(self, service):
        req = pb.GetQuoteRequest(
            chain_id=1,
            src=WETH_ADDRESS,
            dst=USDC_ADDRESS,
            amount="1000000000000000000",
        )
        resp = service.GetQuote(req)
        assert resp.src_token == WETH_ADDRESS
        assert resp.dst_token == USDC_ADDRESS
        assert resp.src_amount == "1000000000000000000"
        assert resp.dst_amount == "3500000000"
        assert resp.gas == 250000

    def test_default_chain_id(self, service, mock_http):
        req = pb.GetQuoteRequest(
            src=WETH_ADDRESS,
            dst=USDC_ADDRESS,
            amount="1000000000000000000",
        )
        resp = service.GetQuote(req)
        # Should default to chain_id 1 (Ethereum).
        call_args = mock_http.get.call_args
        assert "/1/quote" in call_args[0][0]


class TestGetSwap:
    def test_returns_swap(self, service):
        req = pb.GetSwapRequest(
            chain_id=1,
            src=WETH_ADDRESS,
            dst=USDC_ADDRESS,
            amount="1000000000000000000",
            slippage=1.0,
        )
        setattr(req, "from", WALLET_ADDRESS)
        resp = service.GetSwap(req)
        assert resp.src_token == WETH_ADDRESS
        assert resp.dst_token == USDC_ADDRESS
        assert resp.src_amount == "1000000000000000000"
        assert resp.dst_amount == "3480000000"

    def test_swap_tx_fields(self, service):
        req = pb.GetSwapRequest(
            chain_id=1,
            src=WETH_ADDRESS,
            dst=USDC_ADDRESS,
            amount="1000000000000000000",
            slippage=1.0,
        )
        setattr(req, "from", WALLET_ADDRESS)
        resp = service.GetSwap(req)
        tx = resp.tx
        assert tx.to == "0x1111111254EEB25477B68fb85Ed929f73A960582"
        assert tx.data.startswith("0x")
        assert tx.value == "0"
        assert tx.gas == 250000
        assert tx.gas_price == "30000000000"

    def test_swap_passes_slippage(self, service, mock_http):
        req = pb.GetSwapRequest(
            chain_id=1,
            src=WETH_ADDRESS,
            dst=USDC_ADDRESS,
            amount="1000000000000000000",
            slippage=0.5,
        )
        setattr(req, "from", WALLET_ADDRESS)
        service.GetSwap(req)
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        assert params["slippage"] == 0.5


class TestGetTokenPrice:
    def test_returns_prices(self, service):
        req = pb.GetTokenPriceRequest(
            chain_id=1,
            tokens=f"{WETH_ADDRESS},{USDC_ADDRESS}",
        )
        resp = service.GetTokenPrice(req)
        assert len(resp.prices) == 2
        prices_by_addr = {p.address: p.price_usd for p in resp.prices}
        assert prices_by_addr[WETH_ADDRESS] == 3500.42
        assert prices_by_addr[USDC_ADDRESS] == 1.0001

    def test_default_currency(self, service, mock_http):
        req = pb.GetTokenPriceRequest(
            chain_id=1,
            tokens=WETH_ADDRESS,
        )
        service.GetTokenPrice(req)
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params["currency"] == "USD"

    def test_custom_currency(self, service, mock_http):
        req = pb.GetTokenPriceRequest(
            chain_id=1,
            tokens=WETH_ADDRESS,
            currency="EUR",
        )
        service.GetTokenPrice(req)
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params["currency"] == "EUR"


class TestGetTokenInfo:
    def test_returns_token_info(self, service):
        req = pb.GetTokenInfoRequest(
            chain_id=1,
            address=WETH_ADDRESS,
        )
        resp = service.GetTokenInfo(req)
        token = resp.token
        assert token.address == WETH_ADDRESS
        assert token.symbol == "WETH"
        assert token.name == "Wrapped Ether"
        assert token.decimals == 18
        assert "1inch.io" in token.logo_uri
        assert "tokens" in token.tags
        assert "PEG:ETH" in token.tags


class TestSearchTokens:
    def test_returns_tokens(self, service):
        req = pb.SearchTokensRequest(chain_id=1, query="USD")
        resp = service.SearchTokens(req)
        assert len(resp.tokens) == 2

    def test_usdc_result(self, service):
        req = pb.SearchTokensRequest(chain_id=1, query="USD")
        resp = service.SearchTokens(req)
        usdc = resp.tokens[0]
        assert usdc.symbol == "USDC"
        assert usdc.name == "USD Coin"
        assert usdc.decimals == 6
        assert usdc.address == USDC_ADDRESS

    def test_usdt_result(self, service):
        req = pb.SearchTokensRequest(chain_id=1, query="USD")
        resp = service.SearchTokens(req)
        usdt = resp.tokens[1]
        assert usdt.symbol == "USDT"
        assert usdt.name == "Tether USD"
        assert usdt.decimals == 6

    def test_tags(self, service):
        req = pb.SearchTokensRequest(chain_id=1, query="USD")
        resp = service.SearchTokens(req)
        assert "stablecoin" in resp.tokens[0].tags

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=[])
        )
        req = pb.SearchTokensRequest(chain_id=1, query="nonexistent")
        resp = service.SearchTokens(req)
        assert len(resp.tokens) == 0


class TestGetBalances:
    def test_returns_balances(self, service):
        req = pb.GetBalancesRequest(
            chain_id=1,
            address=WALLET_ADDRESS,
        )
        resp = service.GetBalances(req)
        assert len(resp.balances) == 3

    def test_weth_balance(self, service):
        req = pb.GetBalancesRequest(chain_id=1, address=WALLET_ADDRESS)
        resp = service.GetBalances(req)
        balances_by_addr = {b.address: b.balance for b in resp.balances}
        assert balances_by_addr[WETH_ADDRESS] == "500000000000000000"

    def test_usdc_balance(self, service):
        req = pb.GetBalancesRequest(chain_id=1, address=WALLET_ADDRESS)
        resp = service.GetBalances(req)
        balances_by_addr = {b.address: b.balance for b in resp.balances}
        assert balances_by_addr[USDC_ADDRESS] == "10000000000"

    def test_native_token_balance(self, service):
        req = pb.GetBalancesRequest(chain_id=1, address=WALLET_ADDRESS)
        resp = service.GetBalances(req)
        balances_by_addr = {b.address: b.balance for b in resp.balances}
        assert balances_by_addr[NATIVE_TOKEN] == "2000000000000000000"

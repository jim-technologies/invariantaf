"""Unit tests -- every EtherscanService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from etherscan_mcp.gen.etherscan.v1 import etherscan_pb2 as pb
from tests.conftest import (
    FAKE_BALANCE_RESPONSE,
    FAKE_TOKEN_BALANCE_RESPONSE,
    FAKE_TRANSACTIONS_RESPONSE,
    FAKE_TOKEN_TRANSFERS_RESPONSE,
    FAKE_GAS_ORACLE_RESPONSE,
    FAKE_ETH_PRICE_RESPONSE,
    FAKE_CONTRACT_ABI_RESPONSE,
    FAKE_TX_1,
    FAKE_TX_2,
    FAKE_TOKEN_TRANSFER_1,
    FAKE_TOKEN_TRANSFER_2,
)


class TestGetBalance:
    def test_returns_balance(self, service):
        resp = service.GetBalance(pb.GetBalanceRequest(address="0xTestAddress"))
        assert resp.balance == "40891626854930000000000"

    def test_passes_address(self, service, mock_http):
        service.GetBalance(pb.GetBalanceRequest(address="0xMyWallet"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["address"] == "0xMyWallet"
        assert call_params["module"] == "account"
        assert call_params["action"] == "balance"

    def test_includes_api_key(self, service, mock_http):
        service.GetBalance(pb.GetBalanceRequest(address="0xTestAddress"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["apikey"] == "fake-api-key"


class TestGetTokenBalance:
    def test_returns_token_balance(self, service):
        resp = service.GetTokenBalance(pb.GetTokenBalanceRequest(
            address="0xTestAddress",
            contract_address="0xTokenContract",
        ))
        assert resp.balance == "135499000000"

    def test_passes_params(self, service, mock_http):
        service.GetTokenBalance(pb.GetTokenBalanceRequest(
            address="0xMyWallet",
            contract_address="0xUSDC",
        ))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["address"] == "0xMyWallet"
        assert call_params["contractaddress"] == "0xUSDC"
        assert call_params["module"] == "account"
        assert call_params["action"] == "tokenbalance"


class TestGetTransactions:
    def test_returns_transactions(self, service):
        resp = service.GetTransactions(pb.GetTransactionsRequest(address="0xTestAddress"))
        assert len(resp.transactions) == 2

    def test_first_transaction_fields(self, service):
        resp = service.GetTransactions(pb.GetTransactionsRequest(address="0xTestAddress"))
        tx = resp.transactions[0]
        assert tx.block_number == "19000000"
        assert tx.time_stamp == "1700000000"
        assert tx.hash == "0xabc123def456789"
        assert getattr(tx, "from") == "0xSenderAddress1"
        assert tx.to == "0xRecipientAddress1"
        assert tx.value == "1000000000000000000"
        assert tx.gas_used == "21000"
        assert tx.gas_price == "20000000000"
        assert tx.is_error == "0"
        assert tx.nonce == "42"
        assert tx.confirmations == "100"

    def test_second_transaction_fields(self, service):
        resp = service.GetTransactions(pb.GetTransactionsRequest(address="0xTestAddress"))
        tx = resp.transactions[1]
        assert tx.block_number == "19000001"
        assert tx.hash == "0xdef789abc012345"
        assert tx.value == "2500000000000000000"

    def test_defaults_sort_desc(self, service, mock_http):
        service.GetTransactions(pb.GetTransactionsRequest(address="0xTestAddress"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["sort"] == "desc"

    def test_defaults_block_range(self, service, mock_http):
        service.GetTransactions(pb.GetTransactionsRequest(address="0xTestAddress"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["startblock"] == 0
        assert call_params["endblock"] == 99999999

    def test_custom_sort_and_blocks(self, service, mock_http):
        service.GetTransactions(pb.GetTransactionsRequest(
            address="0xTestAddress",
            start_block=1000,
            end_block=2000,
            sort="asc",
        ))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["sort"] == "asc"
        assert call_params["startblock"] == 1000
        assert call_params["endblock"] == 2000

    def test_empty_result(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"status": "0", "message": "No transactions found", "result": []}),
        )
        resp = service.GetTransactions(pb.GetTransactionsRequest(address="0xEmptyWallet"))
        assert len(resp.transactions) == 0


class TestGetTokenTransfers:
    def test_returns_transfers(self, service):
        resp = service.GetTokenTransfers(pb.GetTokenTransfersRequest(address="0xTestAddress"))
        assert len(resp.transfers) == 2

    def test_first_transfer_fields(self, service):
        resp = service.GetTokenTransfers(pb.GetTokenTransfersRequest(address="0xTestAddress"))
        t = resp.transfers[0]
        assert t.block_number == "19000100"
        assert t.time_stamp == "1700001200"
        assert t.hash == "0xtokentx123"
        assert t.token_name == "USD Coin"
        assert t.token_symbol == "USDC"
        assert t.token_decimal == "6"
        assert t.value == "500000000"
        assert t.contract_address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def test_second_transfer_fields(self, service):
        resp = service.GetTokenTransfers(pb.GetTokenTransfersRequest(address="0xTestAddress"))
        t = resp.transfers[1]
        assert t.token_name == "Wrapped Ether"
        assert t.token_symbol == "WETH"
        assert t.token_decimal == "18"
        assert t.value == "1000000000000000000000"

    def test_defaults_sort_desc(self, service, mock_http):
        service.GetTokenTransfers(pb.GetTokenTransfersRequest(address="0xTestAddress"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["sort"] == "desc"

    def test_empty_result(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"status": "0", "message": "No transfers found", "result": []}),
        )
        resp = service.GetTokenTransfers(pb.GetTokenTransfersRequest(address="0xEmptyWallet"))
        assert len(resp.transfers) == 0


class TestGetGasPrice:
    def test_returns_gas_oracle(self, service):
        resp = service.GetGasPrice(pb.GetGasPriceRequest())
        assert resp.gas_oracle is not None

    def test_gas_price_fields(self, service):
        resp = service.GetGasPrice(pb.GetGasPriceRequest())
        g = resp.gas_oracle
        assert g.safe_gas_price == "15"
        assert g.propose_gas_price == "20"
        assert g.fast_gas_price == "30"
        assert g.suggest_base_fee == "14.5"
        assert g.gas_used_ratio == "0.45,0.67,0.32,0.89,0.55"


class TestGetETHPrice:
    def test_returns_eth_price(self, service):
        resp = service.GetETHPrice(pb.GetETHPriceRequest())
        assert resp.eth_price is not None

    def test_eth_price_fields(self, service):
        resp = service.GetETHPrice(pb.GetETHPriceRequest())
        p = resp.eth_price
        assert p.ethusd == "2150.45"
        assert p.ethbtc == "0.05234"
        assert p.ethusd_timestamp == "1700000000"
        assert p.ethbtc_timestamp == "1700000000"


class TestGetContractABI:
    def test_returns_abi(self, service):
        resp = service.GetContractABI(pb.GetContractABIRequest(address="0xContractAddress"))
        assert resp.abi != ""
        assert "name" in resp.abi

    def test_abi_content(self, service):
        resp = service.GetContractABI(pb.GetContractABIRequest(address="0xContractAddress"))
        assert '"type":"function"' in resp.abi

    def test_passes_address(self, service, mock_http):
        service.GetContractABI(pb.GetContractABIRequest(address="0xMyContract"))
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["address"] == "0xMyContract"
        assert call_params["module"] == "contract"
        assert call_params["action"] == "getabi"

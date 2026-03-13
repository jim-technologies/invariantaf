"""Live integration tests for Etherscan API -- hits the real API.

Run with:
    ETHERSCAN_API_KEY=your_key ETHERSCAN_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Requires a valid ETHERSCAN_API_KEY environment variable.
A free tier API key is available at https://etherscan.io/apis.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("ETHERSCAN_RUN_LIVE_TESTS") != "1",
    reason="Set ETHERSCAN_RUN_LIVE_TESTS=1 to run live Etherscan API tests",
)

# Well-known Ethereum addresses for testing.
VITALIK_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from etherscan_mcp.service import EtherscanService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-etherscan-live", version="0.0.1"
    )
    servicer = EtherscanService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- GetBalance ---


class TestLiveGetBalance:
    def test_get_balance(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetBalance", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        assert "balance" in result
        assert result["balance"] != ""

    def test_balance_is_numeric(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetBalance", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        assert result["balance"].isdigit()


# --- GetTokenBalance ---


class TestLiveGetTokenBalance:
    def test_get_token_balance(self, live_server):
        result = live_server._cli(
            [
                "EtherscanService",
                "GetTokenBalance",
                "-r",
                json.dumps({"address": VITALIK_ADDRESS, "contractAddress": USDC_CONTRACT}),
            ]
        )
        assert "balance" in result


# --- GetTransactions ---


class TestLiveGetTransactions:
    def test_get_transactions(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetTransactions", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        assert "transactions" in result
        txs = result["transactions"]
        assert isinstance(txs, list)
        assert len(txs) > 0

    def test_transaction_has_fields(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetTransactions", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        tx = result["transactions"][0]
        assert "hash" in tx
        assert "value" in tx
        assert "blockNumber" in tx or "block_number" in tx


# --- GetTokenTransfers ---


class TestLiveGetTokenTransfers:
    def test_get_token_transfers(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetTokenTransfers", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        assert "transfers" in result
        transfers = result["transfers"]
        assert isinstance(transfers, list)

    def test_transfer_has_token_info(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetTokenTransfers", "-r", json.dumps({"address": VITALIK_ADDRESS})]
        )
        transfers = result["transfers"]
        if len(transfers) > 0:
            t = transfers[0]
            assert "tokenName" in t or "token_name" in t
            assert "tokenSymbol" in t or "token_symbol" in t


# --- GetGasPrice ---


class TestLiveGetGasPrice:
    def test_get_gas_price(self, live_server):
        result = live_server._cli(["EtherscanService", "GetGasPrice"])
        assert "gasOracle" in result or "gas_oracle" in result

    def test_gas_oracle_fields(self, live_server):
        result = live_server._cli(["EtherscanService", "GetGasPrice"])
        oracle = result.get("gasOracle") or result.get("gas_oracle", {})
        assert "safeGasPrice" in oracle or "safe_gas_price" in oracle
        assert "proposeGasPrice" in oracle or "propose_gas_price" in oracle
        assert "fastGasPrice" in oracle or "fast_gas_price" in oracle


# --- GetETHPrice ---


class TestLiveGetETHPrice:
    def test_get_eth_price(self, live_server):
        result = live_server._cli(["EtherscanService", "GetETHPrice"])
        assert "ethPrice" in result or "eth_price" in result

    def test_eth_price_fields(self, live_server):
        result = live_server._cli(["EtherscanService", "GetETHPrice"])
        price = result.get("ethPrice") or result.get("eth_price", {})
        assert "ethusd" in price
        assert "ethbtc" in price


# --- GetContractABI ---


class TestLiveGetContractABI:
    def test_get_contract_abi(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetContractABI", "-r", json.dumps({"address": UNISWAP_ROUTER})]
        )
        assert "abi" in result
        assert result["abi"] != ""

    def test_abi_is_json(self, live_server):
        result = live_server._cli(
            ["EtherscanService", "GetContractABI", "-r", json.dumps({"address": UNISWAP_ROUTER})]
        )
        import json as json_mod
        abi = json_mod.loads(result["abi"])
        assert isinstance(abi, list)

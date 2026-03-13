"""EtherscanService -- wraps the Etherscan API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from etherscan_mcp.gen.etherscan.v1 import etherscan_pb2 as pb

_BASE_URL = "https://api.etherscan.io/api"


def _parse_transaction(t: dict) -> pb.Transaction:
    """Parse a raw Etherscan transaction JSON object into a Transaction proto."""
    return pb.Transaction(
        block_number=str(t.get("blockNumber", "")),
        time_stamp=str(t.get("timeStamp", "")),
        hash=str(t.get("hash", "")),
        **{"from": str(t.get("from", ""))},
        to=str(t.get("to", "")),
        value=str(t.get("value", "")),
        gas_used=str(t.get("gasUsed", "")),
        gas_price=str(t.get("gasPrice", "")),
        is_error=str(t.get("isError", "")),
        contract_address=str(t.get("contractAddress", "")),
        input=str(t.get("input", "")),
        nonce=str(t.get("nonce", "")),
        transaction_index=str(t.get("transactionIndex", "")),
        gas=str(t.get("gas", "")),
        confirmations=str(t.get("confirmations", "")),
    )


def _parse_token_transfer(t: dict) -> pb.TokenTransfer:
    """Parse a raw Etherscan token transfer JSON object into a TokenTransfer proto."""
    return pb.TokenTransfer(
        block_number=str(t.get("blockNumber", "")),
        time_stamp=str(t.get("timeStamp", "")),
        hash=str(t.get("hash", "")),
        **{"from": str(t.get("from", ""))},
        to=str(t.get("to", "")),
        value=str(t.get("value", "")),
        token_name=str(t.get("tokenName", "")),
        token_symbol=str(t.get("tokenSymbol", "")),
        token_decimal=str(t.get("tokenDecimal", "")),
        contract_address=str(t.get("contractAddress", "")),
        gas_used=str(t.get("gasUsed", "")),
        gas_price=str(t.get("gasPrice", "")),
        nonce=str(t.get("nonce", "")),
        confirmations=str(t.get("confirmations", "")),
    )


class EtherscanService:
    """Implements EtherscanService RPCs via the Etherscan API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)
        self._api_key = os.environ.get("ETHERSCAN_API_KEY", "")

    def _get(self, params: dict) -> Any:
        params["apikey"] = self._api_key
        resp = self._http.get(_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data

    def GetBalance(self, request: Any, context: Any = None) -> pb.GetBalanceResponse:
        data = self._get({
            "module": "account",
            "action": "balance",
            "address": request.address,
        })
        return pb.GetBalanceResponse(balance=str(data.get("result", "")))

    def GetTokenBalance(self, request: Any, context: Any = None) -> pb.GetTokenBalanceResponse:
        data = self._get({
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": request.contract_address,
            "address": request.address,
        })
        return pb.GetTokenBalanceResponse(balance=str(data.get("result", "")))

    def GetTransactions(self, request: Any, context: Any = None) -> pb.GetTransactionsResponse:
        start_block = request.start_block if request.start_block else 0
        end_block = request.end_block if request.end_block else 99999999
        sort = request.sort if request.sort else "desc"
        data = self._get({
            "module": "account",
            "action": "txlist",
            "address": request.address,
            "startblock": start_block,
            "endblock": end_block,
            "sort": sort,
        })
        resp = pb.GetTransactionsResponse()
        result = data.get("result", [])
        if isinstance(result, list):
            for t in result:
                resp.transactions.append(_parse_transaction(t))
        return resp

    def GetTokenTransfers(self, request: Any, context: Any = None) -> pb.GetTokenTransfersResponse:
        start_block = request.start_block if request.start_block else 0
        end_block = request.end_block if request.end_block else 99999999
        sort = request.sort if request.sort else "desc"
        data = self._get({
            "module": "account",
            "action": "tokentx",
            "address": request.address,
            "startblock": start_block,
            "endblock": end_block,
            "sort": sort,
        })
        resp = pb.GetTokenTransfersResponse()
        result = data.get("result", [])
        if isinstance(result, list):
            for t in result:
                resp.transfers.append(_parse_token_transfer(t))
        return resp

    def GetGasPrice(self, request: Any, context: Any = None) -> pb.GetGasPriceResponse:
        data = self._get({
            "module": "gastracker",
            "action": "gasoracle",
        })
        result = data.get("result", {})
        gas_oracle = pb.GasOracle(
            safe_gas_price=str(result.get("SafeGasPrice", "")),
            propose_gas_price=str(result.get("ProposeGasPrice", "")),
            fast_gas_price=str(result.get("FastGasPrice", "")),
            suggest_base_fee=str(result.get("suggestBaseFee", "")),
            gas_used_ratio=str(result.get("gasUsedRatio", "")),
        )
        return pb.GetGasPriceResponse(gas_oracle=gas_oracle)

    def GetETHPrice(self, request: Any, context: Any = None) -> pb.GetETHPriceResponse:
        data = self._get({
            "module": "stats",
            "action": "ethprice",
        })
        result = data.get("result", {})
        eth_price = pb.ETHPrice(
            ethusd=str(result.get("ethusd", "")),
            ethbtc=str(result.get("ethbtc", "")),
            ethusd_timestamp=str(result.get("ethusd_timestamp", "")),
            ethbtc_timestamp=str(result.get("ethbtc_timestamp", "")),
        )
        return pb.GetETHPriceResponse(eth_price=eth_price)

    def GetContractABI(self, request: Any, context: Any = None) -> pb.GetContractABIResponse:
        data = self._get({
            "module": "contract",
            "action": "getabi",
            "address": request.address,
        })
        return pb.GetContractABIResponse(abi=str(data.get("result", "")))

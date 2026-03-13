"""Shared fixtures for Etherscan MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from etherscan_mcp.gen.etherscan.v1 import etherscan_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Etherscan API return shapes
# ---------------------------------------------------------------------------

FAKE_BALANCE_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": "40891626854930000000000",
}

FAKE_TOKEN_BALANCE_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": "135499000000",
}

FAKE_TX_1 = {
    "blockNumber": "19000000",
    "timeStamp": "1700000000",
    "hash": "0xabc123def456789",
    "from": "0xSenderAddress1",
    "to": "0xRecipientAddress1",
    "value": "1000000000000000000",
    "gasUsed": "21000",
    "gasPrice": "20000000000",
    "isError": "0",
    "contractAddress": "",
    "input": "0x",
    "nonce": "42",
    "transactionIndex": "5",
    "gas": "21000",
    "confirmations": "100",
}

FAKE_TX_2 = {
    "blockNumber": "19000001",
    "timeStamp": "1700000012",
    "hash": "0xdef789abc012345",
    "from": "0xSenderAddress2",
    "to": "0xRecipientAddress2",
    "value": "2500000000000000000",
    "gasUsed": "21000",
    "gasPrice": "25000000000",
    "isError": "0",
    "contractAddress": "",
    "input": "0x",
    "nonce": "10",
    "transactionIndex": "3",
    "gas": "21000",
    "confirmations": "99",
}

FAKE_TRANSACTIONS_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": [FAKE_TX_1, FAKE_TX_2],
}

FAKE_TOKEN_TRANSFER_1 = {
    "blockNumber": "19000100",
    "timeStamp": "1700001200",
    "hash": "0xtokentx123",
    "from": "0xTokenSender1",
    "to": "0xTokenReceiver1",
    "value": "500000000",
    "tokenName": "USD Coin",
    "tokenSymbol": "USDC",
    "tokenDecimal": "6",
    "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "gasUsed": "65000",
    "gasPrice": "30000000000",
    "nonce": "15",
    "confirmations": "50",
}

FAKE_TOKEN_TRANSFER_2 = {
    "blockNumber": "19000200",
    "timeStamp": "1700002400",
    "hash": "0xtokentx456",
    "from": "0xTokenSender2",
    "to": "0xTokenReceiver2",
    "value": "1000000000000000000000",
    "tokenName": "Wrapped Ether",
    "tokenSymbol": "WETH",
    "tokenDecimal": "18",
    "contractAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "gasUsed": "85000",
    "gasPrice": "35000000000",
    "nonce": "20",
    "confirmations": "40",
}

FAKE_TOKEN_TRANSFERS_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": [FAKE_TOKEN_TRANSFER_1, FAKE_TOKEN_TRANSFER_2],
}

FAKE_GAS_ORACLE_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": {
        "LastBlock": "19000500",
        "SafeGasPrice": "15",
        "ProposeGasPrice": "20",
        "FastGasPrice": "30",
        "suggestBaseFee": "14.5",
        "gasUsedRatio": "0.45,0.67,0.32,0.89,0.55",
    },
}

FAKE_ETH_PRICE_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": {
        "ethbtc": "0.05234",
        "ethbtc_timestamp": "1700000000",
        "ethusd": "2150.45",
        "ethusd_timestamp": "1700000000",
    },
}

FAKE_CONTRACT_ABI_RESPONSE = {
    "status": "1",
    "message": "OK",
    "result": '[{"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"}]',
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        ("account", "balance"): FAKE_BALANCE_RESPONSE,
        ("account", "tokenbalance"): FAKE_TOKEN_BALANCE_RESPONSE,
        ("account", "txlist"): FAKE_TRANSACTIONS_RESPONSE,
        ("account", "tokentx"): FAKE_TOKEN_TRANSFERS_RESPONSE,
        ("gastracker", "gasoracle"): FAKE_GAS_ORACLE_RESPONSE,
        ("stats", "ethprice"): FAKE_ETH_PRICE_RESPONSE,
        ("contract", "getabi"): FAKE_CONTRACT_ABI_RESPONSE,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if params:
            key = (params.get("module", ""), params.get("action", ""))
            if key in defaults:
                resp.json.return_value = defaults[key]
                return resp
        resp.json.return_value = {"status": "0", "message": "NOTOK", "result": ""}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """EtherscanService with mocked HTTP client."""
    from etherscan_mcp.service import EtherscanService

    svc = EtherscanService.__new__(EtherscanService)
    svc._http = mock_http
    svc._api_key = "fake-api-key"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked EtherscanService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-etherscan", version="0.0.1")
    srv.register(service)
    return srv

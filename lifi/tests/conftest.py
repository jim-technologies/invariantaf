"""Shared fixtures for Li.Fi MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifi_mcp.gen.lifi.v1 import lifi_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Li.Fi API return shapes
# ---------------------------------------------------------------------------

FAKE_CHAINS = {
    "chains": [
        {
            "key": "eth",
            "chainType": "EVM",
            "name": "Ethereum",
            "coin": "ETH",
            "id": 1,
            "mainnet": True,
            "logoURI": "https://raw.githubusercontent.com/lifinance/types/main/src/assets/icons/chains/ethereum.svg",
            "nativeToken": {
                "address": "0x0000000000000000000000000000000000000000",
                "chainId": 1,
                "symbol": "ETH",
                "decimals": 18,
                "name": "Ethereum",
                "coinKey": "ETH",
                "logoURI": "https://static.debank.com/image/token/logo_url/eth/935ae4e4d1d12d59a99717a24f2540b5.png",
                "priceUSD": "3500.00",
            },
        },
        {
            "key": "arb",
            "chainType": "EVM",
            "name": "Arbitrum",
            "coin": "ETH",
            "id": 42161,
            "mainnet": True,
            "logoURI": "https://raw.githubusercontent.com/lifinance/types/main/src/assets/icons/chains/arbitrum.svg",
            "nativeToken": {
                "address": "0x0000000000000000000000000000000000000000",
                "chainId": 42161,
                "symbol": "ETH",
                "decimals": 18,
                "name": "Ethereum",
                "coinKey": "ETH",
                "logoURI": "https://static.debank.com/image/token/logo_url/eth/935ae4e4d1d12d59a99717a24f2540b5.png",
                "priceUSD": "3500.00",
            },
        },
    ]
}

FAKE_TOKENS = {
    "tokens": {
        "1": [
            {
                "address": "0x0000000000000000000000000000000000000000",
                "chainId": 1,
                "symbol": "ETH",
                "decimals": 18,
                "name": "Ethereum",
                "coinKey": "ETH",
                "logoURI": "https://example.com/eth.png",
                "priceUSD": "3500.00",
            },
            {
                "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "chainId": 1,
                "symbol": "USDC",
                "decimals": 6,
                "name": "USD Coin",
                "coinKey": "USDC",
                "logoURI": "https://example.com/usdc.png",
                "priceUSD": "1.00",
            },
        ],
        "42161": [
            {
                "address": "0x0000000000000000000000000000000000000000",
                "chainId": 42161,
                "symbol": "ETH",
                "decimals": 18,
                "name": "Ethereum",
                "coinKey": "ETH",
                "logoURI": "https://example.com/eth.png",
                "priceUSD": "3500.00",
            },
        ],
    }
}

FAKE_CONNECTIONS = {
    "connections": [
        {
            "fromChainId": 1,
            "toChainId": 42161,
            "fromTokens": [
                {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 1,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
            ],
            "toTokens": [
                {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 42161,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
            ],
        },
    ]
}

FAKE_TOOLS = {
    "bridges": [
        {
            "key": "stargate",
            "name": "Stargate",
            "logoURI": "https://example.com/stargate.png",
            "supportedChains": [
                {"fromChainId": 1, "toChainId": 42161},
                {"fromChainId": 42161, "toChainId": 1},
            ],
        },
        {
            "key": "hop",
            "name": "Hop",
            "logoURI": "https://example.com/hop.png",
            "supportedChains": [
                {"fromChainId": 1, "toChainId": 10},
            ],
        },
    ],
    "exchanges": [
        {
            "key": "uniswap",
            "name": "Uniswap",
            "logoURI": "https://example.com/uniswap.png",
        },
        {
            "key": "sushiswap",
            "name": "SushiSwap",
            "logoURI": "https://example.com/sushiswap.png",
        },
    ],
}

FAKE_QUOTE = {
    "type": "lifi",
    "id": "quote-abc-123",
    "tool": "stargate",
    "toolDetails": {
        "name": "Stargate",
        "logoURI": "https://example.com/stargate.png",
    },
    "action": {
        "fromToken": {
            "address": "0x0000000000000000000000000000000000000000",
            "chainId": 1,
            "symbol": "ETH",
            "decimals": 18,
            "name": "Ethereum",
            "coinKey": "ETH",
            "logoURI": "https://example.com/eth.png",
            "priceUSD": "3500.00",
        },
        "fromAmount": "1000000000000000000",
        "toToken": {
            "address": "0x0000000000000000000000000000000000000000",
            "chainId": 42161,
            "symbol": "ETH",
            "decimals": 18,
            "name": "Ethereum",
            "coinKey": "ETH",
            "logoURI": "https://example.com/eth.png",
            "priceUSD": "3500.00",
        },
        "fromChainId": 1,
        "toChainId": 42161,
        "slippage": 0.03,
        "fromAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "toAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    },
    "estimate": {
        "tool": "stargate",
        "approvalAddress": "0x1231DEB6f5749ef6cE6943a275A1D3E7486F4EaE",
        "toAmountMin": "990000000000000000",
        "toAmount": "999000000000000000",
        "fromAmount": "1000000000000000000",
        "feeCosts": [
            {
                "name": "LP Fee",
                "description": "Liquidity provider fee",
                "token": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 1,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
                "amount": "1000000000000000",
                "amountUSD": "3.50",
            },
        ],
        "gasCosts": [
            {
                "name": "Gas",
                "description": "Estimated gas cost",
                "token": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 1,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
                "amount": "5000000000000000",
                "amountUSD": "17.50",
            },
        ],
        "executionDuration": 120,
        "fromAmountUSD": "3500.00",
        "toAmountUSD": "3496.50",
    },
    "includedSteps": [
        {
            "id": "step-1",
            "type": "cross",
            "tool": "stargate",
            "toolDetails": {
                "name": "Stargate",
                "logoURI": "https://example.com/stargate.png",
            },
            "action": {
                "fromToken": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 1,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
                "fromAmount": "1000000000000000000",
                "toToken": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "chainId": 42161,
                    "symbol": "ETH",
                    "decimals": 18,
                    "name": "Ethereum",
                    "coinKey": "ETH",
                    "logoURI": "https://example.com/eth.png",
                    "priceUSD": "3500.00",
                },
                "fromChainId": 1,
                "toChainId": 42161,
                "slippage": 0.03,
                "fromAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                "toAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            },
            "estimate": {
                "tool": "stargate",
                "approvalAddress": "0x1231DEB6f5749ef6cE6943a275A1D3E7486F4EaE",
                "toAmountMin": "990000000000000000",
                "toAmount": "999000000000000000",
                "fromAmount": "1000000000000000000",
                "feeCosts": [],
                "gasCosts": [],
                "executionDuration": 120,
                "fromAmountUSD": "3500.00",
                "toAmountUSD": "3496.50",
            },
        },
    ],
    "transactionRequest": {
        "value": "0xde0b6b3a7640000",
        "to": "0x1231DEB6f5749ef6cE6943a275A1D3E7486F4EaE",
        "data": "0xabcdef1234567890",
        "from": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "chainId": 1,
        "gasPrice": "0x6fc23ac00",
        "gasLimit": "0x3d090",
    },
}

FAKE_STATUS = {
    "transactionId": "0xabc123",
    "sending": {
        "txHash": "0xsend123",
        "chainId": 1,
    },
    "receiving": {
        "txHash": "0xrecv456",
        "chainId": 42161,
        "amount": "999000000000000000",
        "token": {
            "address": "0x0000000000000000000000000000000000000000",
            "chainId": 42161,
            "symbol": "ETH",
            "decimals": 18,
            "name": "Ethereum",
            "coinKey": "ETH",
            "logoURI": "https://example.com/eth.png",
            "priceUSD": "3500.00",
        },
    },
    "status": "DONE",
    "substatus": "COMPLETED",
    "substatusMessage": "Bridge transfer completed successfully",
    "bridge": "stargate",
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/chains": FAKE_CHAINS,
        "/tokens": FAKE_TOKENS,
        "/connections": FAKE_CONNECTIONS,
        "/tools": FAKE_TOOLS,
        "/quote": FAKE_QUOTE,
        "/status": FAKE_STATUS,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """LifiService with mocked HTTP client."""
    from lifi_mcp.service import LifiService

    svc = LifiService.__new__(LifiService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked LifiService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-lifi", version="0.0.1")
    srv.register(service)
    return srv

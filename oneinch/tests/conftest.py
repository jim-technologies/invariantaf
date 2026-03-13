"""Shared fixtures for 1inch MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oneinch_mcp.gen.oneinch.v1 import oneinch_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real 1inch API return shapes
# ---------------------------------------------------------------------------

# WETH and USDC on Ethereum mainnet
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
WALLET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

FAKE_QUOTE = {
    "srcToken": WETH_ADDRESS,
    "dstToken": USDC_ADDRESS,
    "srcAmount": "1000000000000000000",
    "dstAmount": "3500000000",
    "gas": 250000,
}

FAKE_SWAP = {
    "srcToken": WETH_ADDRESS,
    "dstToken": USDC_ADDRESS,
    "srcAmount": "1000000000000000000",
    "dstAmount": "3480000000",
    "tx": {
        "to": "0x1111111254EEB25477B68fb85Ed929f73A960582",
        "data": "0x12aa3caf0000000000000000000000000000000000000000abcdef",
        "value": "0",
        "gas": 250000,
        "gasPrice": "30000000000",
    },
}

FAKE_TOKEN_PRICES = {
    WETH_ADDRESS: 3500.42,
    USDC_ADDRESS: 1.0001,
}

FAKE_TOKEN_INFO = {
    "address": WETH_ADDRESS,
    "symbol": "WETH",
    "name": "Wrapped Ether",
    "decimals": 18,
    "logoURI": "https://tokens.1inch.io/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2.png",
    "tags": ["tokens", "PEG:ETH"],
}

FAKE_SEARCH_TOKENS = [
    {
        "address": USDC_ADDRESS,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "logoURI": "https://tokens.1inch.io/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.png",
        "tags": ["tokens", "stablecoin"],
    },
    {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "symbol": "USDT",
        "name": "Tether USD",
        "decimals": 6,
        "logoURI": "https://tokens.1inch.io/0xdac17f958d2ee523a2206206994597c13d831ec7.png",
        "tags": ["tokens", "stablecoin"],
    },
]

FAKE_BALANCES = {
    WETH_ADDRESS: "500000000000000000",
    USDC_ADDRESS: "10000000000",
    NATIVE_TOKEN: "2000000000000000000",
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/quote": FAKE_QUOTE,
        "/swap": FAKE_SWAP,
        "/price/v1.1/": FAKE_TOKEN_PRICES,
        "/token/v1.2/1/search": FAKE_SEARCH_TOKENS,
        "/token/v1.2/1": FAKE_TOKEN_INFO,
        "/balances/": FAKE_BALANCES,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix — order matters (more specific first).
        if "/search" in url:
            resp.json.return_value = defaults["/token/v1.2/1/search"]
        elif "/quote" in url:
            resp.json.return_value = defaults["/quote"]
        elif "/swap" in url:
            resp.json.return_value = defaults["/swap"]
        elif "/price/" in url:
            resp.json.return_value = defaults["/price/v1.1/"]
        elif "/balances/" in url:
            resp.json.return_value = defaults["/balances/"]
        elif "/token/" in url:
            resp.json.return_value = defaults["/token/v1.2/1"]
        else:
            resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """OneInchService with mocked HTTP client."""
    from oneinch_mcp.service import OneInchService

    svc = OneInchService.__new__(OneInchService)
    svc._api_key = "test-key"
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked OneInchService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-oneinch", version="0.0.1")
    srv.register(service)
    return srv

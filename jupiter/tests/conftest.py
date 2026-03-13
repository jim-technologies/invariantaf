"""Shared fixtures for Jupiter MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jupiter_mcp.gen.jupiter.v1 import jupiter_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Jupiter API return shapes
# ---------------------------------------------------------------------------

# SOL and USDC mint addresses (well-known)
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Price v3 response — keys are mint addresses, values are price info dicts.
FAKE_PRICE = {
    SOL_MINT: {
        "createdAt": "2024-06-05T08:55:25.527Z",
        "liquidity": 621679197.67,
        "usdPrice": 172.50,
        "blockId": 348004023,
        "decimals": 9,
        "priceChange24h": 1.29,
    },
    USDC_MINT: {
        "createdAt": "2024-06-05T08:55:25.527Z",
        "liquidity": 1500000000.00,
        "usdPrice": 1.0001,
        "blockId": 348004023,
        "decimals": 6,
        "priceChange24h": 0.01,
    },
}

FAKE_QUOTE = {
    "inputMint": SOL_MINT,
    "outputMint": USDC_MINT,
    "inAmount": "1000000000",
    "outAmount": "172350000",
    "otherAmountThreshold": "171488250",
    "priceImpactPct": "0.001",
    "swapMode": "ExactIn",
    "slippageBps": 50,
    "routePlan": [
        {
            "swapInfo": {
                "ammKey": "HWy1jotHpo6UqeQxx49dpYYdQB8wj9Qk9MdxwjLvDHB8",
                "label": "Raydium",
                "inputMint": SOL_MINT,
                "outputMint": USDC_MINT,
                "inAmount": "1000000000",
                "outAmount": "172350000",
                "feeAmount": "250000",
                "feeMint": USDC_MINT,
            },
            "percent": 100,
        },
    ],
}

FAKE_SWAP = {
    "swapTransaction": "AQAAAA...base64encodedtransaction...==",
    "lastValidBlockHeight": 280000000,
    "prioritizationFeeLamports": 5000,
}

# Token v2 search response — array of token objects.
FAKE_TOKENS = [
    {
        "id": SOL_MINT,
        "symbol": "SOL",
        "name": "Wrapped SOL",
        "decimals": 9,
        "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
        "daily_volume": 500000000,
        "isVerified": True,
    },
    {
        "id": USDC_MINT,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png",
        "daily_volume": 1200000000,
        "isVerified": True,
    },
    {
        "id": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "symbol": "JUP",
        "name": "Jupiter",
        "decimals": 6,
        "icon": "https://static.jup.ag/jup/icon.png",
        "daily_volume": 80000000,
        "isVerified": True,
    },
]

# Token v2 tag response (verified) — array of token objects.
FAKE_VERIFIED_TOKENS = [
    {
        "id": SOL_MINT,
        "symbol": "SOL",
        "name": "Wrapped SOL",
        "decimals": 9,
        "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
        "daily_volume": 500000000,
        "isVerified": True,
    },
    {
        "id": USDC_MINT,
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": 6,
        "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png",
        "daily_volume": 1200000000,
        "isVerified": True,
    },
]

FAKE_MARKETS = [
    {
        "id": "market-001",
        "baseMint": SOL_MINT,
        "quoteMint": USDC_MINT,
        "label": "Raydium",
        "liquidity": 50000000,
    },
    {
        "id": "market-002",
        "baseMint": SOL_MINT,
        "quoteMint": USDC_MINT,
        "label": "Orca",
        "liquidity": 30000000,
    },
]


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/price/v3": FAKE_PRICE,
        "/swap/v1/quote": FAKE_QUOTE,
        "/swap/v1/swap": FAKE_SWAP,
        "/tokens/v2/search": FAKE_TOKENS,
        "/tokens/v2/tag": FAKE_VERIFIED_TOKENS,
        "/swap/v1/markets": FAKE_MARKETS,
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

    def mock_post(url, json=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    http.post = MagicMock(side_effect=mock_post)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """JupiterService with mocked HTTP client."""
    from jupiter_mcp.service import JupiterService

    svc = JupiterService.__new__(JupiterService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked JupiterService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-jup", version="0.0.1")
    srv.register(service)
    return srv

"""Shared fixtures for Solscan MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solscan_mcp.gen.solscan.v1 import solscan_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Solscan API v2 return shapes
# ---------------------------------------------------------------------------

FAKE_ACCOUNT_INFO = {
    "success": True,
    "data": {
        "address": "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",
        "lamports": 1000000000,
        "owner": "11111111111111111111111111111111",
        "type": "system",
        "rentEpoch": 361,
        "executable": False,
    },
}

FAKE_ACCOUNT_TOKENS = {
    "success": True,
    "data": [
        {
            "tokenAddress": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "tokenAccount": "3emsAVdmGKoHve6pchAm15mfKgAsHnWnoZFpoKSfGBJJ",
            "amount": "50000000",
            "tokenInfo": {
                "name": "USD Coin",
                "symbol": "USDC",
                "decimals": 6,
                "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png",
            },
        },
        {
            "tokenAddress": "So11111111111111111111111111111111111111112",
            "tokenAccount": "4pJFMBEwxdsMkPa5xnyUQ7fBGhTEKUTS81oZPjz6GTjN",
            "amount": "2000000000",
            "tokenInfo": {
                "name": "Wrapped SOL",
                "symbol": "SOL",
                "decimals": 9,
                "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
            },
        },
    ],
}

FAKE_ACCOUNT_TRANSACTIONS = {
    "success": True,
    "data": [
        {
            "txHash": "5jGv8dCGxB1Mh6wGBzRfhGLfpDhWfJqdeQ8Ka1u8n7Rg4jYVmV5gCR3Z7m1FCp8kF5zTgXjWdJwJjFrX8vN2nFe",
            "blockId": 250000000,
            "blockTime": 1700000000,
            "status": "Success",
            "fee": 5000,
            "signer": ["vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg"],
        },
        {
            "txHash": "2pQr8dBFxA1Nh7vGB9PfhJLfpDhWfJqdeQ8Ka1u8n7Rg4jYVmV5gCR3Z7m1FCp8kF5zTgXjWdJwJjFrX8vN2nAb",
            "blockId": 249999999,
            "blockTime": 1699999500,
            "status": "Success",
            "fee": 5000,
            "signer": ["vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg"],
        },
    ],
}

FAKE_TOKEN_META = {
    "success": True,
    "data": {
        "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "name": "USD Coin",
        "symbol": "USDC",
        "decimals": 6,
        "icon": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png",
        "website": "https://www.centre.io/",
        "twitter": "circle",
        "tag": "stablecoin",
    },
}

FAKE_TOKEN_PRICE = {
    "success": True,
    "data": {
        "priceUsdt": 1.0001,
    },
}

FAKE_TOKEN_HOLDERS = {
    "success": True,
    "data": {
        "total": 500000,
        "items": [
            {
                "address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
                "amount": "10000000000",
                "decimals": 6,
                "rank": 1,
                "ownerPercentage": 5.5,
            },
            {
                "address": "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT",
                "amount": "5000000000",
                "decimals": 6,
                "rank": 2,
                "ownerPercentage": 2.75,
            },
        ],
    },
}

FAKE_MARKET_INFO = {
    "success": True,
    "data": {
        "priceUsdt": 1.0001,
        "volume24h": 5000000000.0,
        "marketCap": 32000000000.0,
        "marketCapRank": 7,
        "totalSupply": "40000000000000000",
        "circulatingSupply": "32000000000000000",
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/account": FAKE_ACCOUNT_INFO,
        "/account/token-accounts": FAKE_ACCOUNT_TOKENS,
        "/account/transactions": FAKE_ACCOUNT_TRANSACTIONS,
        "/token/meta": FAKE_TOKEN_META,
        "/token/price": FAKE_TOKEN_PRICE,
        "/token/holders": FAKE_TOKEN_HOLDERS,
        "/market/token/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": FAKE_MARKET_INFO,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {"success": True, "data": {}}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """SolscanService with mocked HTTP client."""
    from solscan_mcp.service import SolscanService

    svc = SolscanService.__new__(SolscanService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked SolscanService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-solscan", version="0.0.1")
    srv.register(service)
    return srv

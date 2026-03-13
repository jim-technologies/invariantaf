"""Shared fixtures for Beefy MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from beefy_mcp.gen.beefy.v1 import beefy_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Beefy API return shapes
# ---------------------------------------------------------------------------

FAKE_VAULTS = [
    {
        "id": "curve-usdc-usdf",
        "name": "USDf/USDC",
        "type": "standard",
        "token": "USDC/USDf",
        "tokenAddress": "0x72310DAAed61321b02B08A547150c07522c6a976",
        "tokenDecimals": 18,
        "earnContractAddress": "0x0014E0be19De3118b5b29842dd1696a2A98EB9Db",
        "earnedToken": "mooCurveUSDC-USDf",
        "status": "active",
        "chain": "ethereum",
        "platformId": "convex",
        "assets": ["USDf", "USDC"],
        "strategyTypeId": "multi-lp",
        "risks": {
            "complex": False,
            "curated": False,
            "notAudited": False,
            "notBattleTested": False,
            "notCorrelated": False,
            "notTimelocked": True,
            "notVerified": False,
            "synthAsset": False,
        },
        "createdAt": 1747215194,
        "strategy": "0x3b7434ecaedD847fE2eF872dAf18094F4f386031",
        "lastHarvest": 1773299783,
        "pricePerFullShare": "1085030497437566950",
        "isGovVault": False,
    },
    {
        "id": "aero-weth-usdc",
        "name": "WETH-USDC",
        "type": "standard",
        "token": "WETH-USDC LP",
        "tokenAddress": "0xABCD1234567890",
        "tokenDecimals": 18,
        "earnContractAddress": "0xEEEE1234567890",
        "earnedToken": "mooAeroWETH-USDC",
        "status": "active",
        "chain": "base",
        "platformId": "aerodrome",
        "assets": ["WETH", "USDC"],
        "strategyTypeId": "lp",
        "risks": {
            "complex": False,
            "curated": True,
            "notAudited": False,
            "notBattleTested": False,
            "notCorrelated": True,
            "notTimelocked": False,
            "notVerified": False,
            "synthAsset": False,
        },
        "createdAt": 1700000000,
        "strategy": "0xAAAA1234567890",
        "lastHarvest": 1773200000,
        "pricePerFullShare": "1050000000000000000",
        "isGovVault": False,
    },
]

FAKE_APYS = {
    "curve-usdc-usdf": 0.0523,
    "aero-weth-usdc": 0.1847,
    "beefy-maxi": 0,
}

FAKE_APY_BREAKDOWN = {
    "curve-usdc-usdf": {
        "totalApy": 0.0523,
        "vaultApr": 0.048,
        "compoundingsPerYear": 2190,
        "beefyPerformanceFee": 0.045,
        "lpFee": 0.003,
        "tradingApr": 0.005,
        "boostApr": 0,
    },
    "aero-weth-usdc": {
        "totalApy": 0.1847,
        "vaultApr": 0.16,
        "compoundingsPerYear": 2190,
        "beefyPerformanceFee": 0.095,
        "lpFee": 0.003,
        "tradingApr": 0.02,
        "boostApr": 0.01,
    },
}

FAKE_TVL = {
    "1": {
        "curve-usdc-usdf": 1036888.59,
        "pendle-usdf": 2028.19,
    },
    "8453": {
        "aero-weth-usdc": 500000.0,
    },
}

FAKE_FEES = {
    "curve-usdc-usdf": {
        "performance": {
            "total": 0.045,
            "strategist": 0.005,
            "call": 0.005,
            "treasury": 0.022,
            "stakers": 0.013,
        },
        "withdraw": 0,
        "deposit": 0,
        "lastUpdated": 1773286654682,
    },
    "aero-weth-usdc": {
        "performance": {
            "total": 0.095,
            "strategist": 0.01,
            "call": 0.005,
            "treasury": 0.05,
            "stakers": 0.03,
        },
        "withdraw": 0.001,
        "lastUpdated": 1773286654682,
    },
}

FAKE_LP_PRICES = {
    "curve-usdc-usdf": 1.0012,
    "aero-weth-usdc": 245.67,
    "sushi-eth-dai": 0,
}

FAKE_BOOSTS = [
    {
        "id": "moo_lendle-mantle-weth-lendle",
        "name": "Lendle",
        "chain": "mantle",
        "poolId": "lendle-mantle-weth",
        "assets": ["ETH"],
        "status": "active",
        "earnContractAddress": "0x01e8881ed2Fb41E0B3dF29f382fAf707a0B26969",
        "earnedToken": "LEND",
        "earnedTokenDecimals": 18,
        "earnedTokenAddress": "0x25356aeca4210eF7553140edb9b8026089E49396",
        "partners": ["lendle"],
        "isMooStaked": True,
        "periodFinish": 1708274069,
    },
    {
        "id": "moo_fusefi-wfuse-usdc-fuse",
        "name": "Fuse",
        "chain": "fuse",
        "poolId": "voltage-wfuse-usdc-eol",
        "assets": ["USDC", "FUSE"],
        "status": "active",
        "earnContractAddress": "0x405EE7F4f067604b787346bC22ACb66b06b15A4B",
        "earnedToken": "mooFuse",
        "earnedTokenDecimals": 18,
        "earnedTokenAddress": "0x2C43DBef81ABa6b95799FD2aEc738Cd721ba77f3",
        "partners": ["fuse"],
        "isMooStaked": True,
        "periodFinish": 1644695605,
    },
]


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/vaults": FAKE_VAULTS,
        "/apy": FAKE_APYS,
        "/apy/breakdown": FAKE_APY_BREAKDOWN,
        "/tvl": FAKE_TVL,
        "/fees": FAKE_FEES,
        "/lps": FAKE_LP_PRICES,
        "/boosts": FAKE_BOOSTS,
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
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """BeefyService with mocked HTTP client."""
    from beefy_mcp.service import BeefyService

    svc = BeefyService.__new__(BeefyService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked BeefyService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-beefy", version="0.0.1")
    srv.register(service)
    return srv

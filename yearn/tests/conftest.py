"""Shared fixtures for Yearn MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yearn_mcp.gen.yearn.v1 import yearn_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real yDaemon API return shapes
# ---------------------------------------------------------------------------

FAKE_VAULT_1 = {
    "address": "0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213",
    "type": "Yearn Vault",
    "kind": "Legacy",
    "symbol": "yvCurve-YFIETH-f",
    "displaySymbol": "yvCurve-YFIETH-f",
    "formatedSymbol": "yvCurveYFIETH",
    "name": "Curve YFIETH Factory yVault",
    "displayName": "Curve YFIETH Factory yVault",
    "formatedName": "Curve YFIETH Factory",
    "icon": "https://assets.yearn.fi/icons/vault.png",
    "version": "0.4.6",
    "category": "Curve",
    "decimals": 18,
    "chainID": 1,
    "endorsed": True,
    "boosted": False,
    "emergency_shutdown": False,
    "token": {
        "address": "0x29059568bB40344487d62f7450E78b8E6C74e0e5",
        "underlyingTokensAddresses": [
            "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6AD93e",
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        ],
        "name": "Curve.fi Factory Crypto Pool: YFI/ETH",
        "symbol": "YFIETH-f",
        "type": "Curve",
        "display_name": "Curve YFIETH",
        "display_symbol": "crvYFIETH",
        "description": "",
        "icon": "https://assets.yearn.fi/icons/token.png",
        "decimals": 18,
    },
    "tvl": {
        "totalAssets": "11605289578737060000",
        "tvl": 15234567.89,
        "price": 1312.45,
    },
    "apr": {
        "type": "v2:averaged",
        "netAPR": 0.0523,
        "fees": {
            "performance": 0.1,
            "management": 0.02,
        },
        "points": {
            "weekAgo": 0.0498,
            "monthAgo": 0.0612,
            "inception": 0.0445,
        },
        "pricePerShare": {
            "today": 1.05,
            "weekAgo": 1.04,
            "monthAgo": 1.03,
        },
        "extra": {
            "stakingRewardsAPR": None,
            "gammaRewardAPR": None,
        },
        "forwardAPR": {
            "type": "crv",
            "netAPR": 0.0678,
            "composite": {
                "boost": 2.5,
                "poolAPY": 0.01,
                "boostedAPR": 0.05,
                "baseAPR": 0.02,
                "cvxAPR": 0.005,
                "rewardsAPR": 0.003,
            },
        },
    },
    "strategies": [
        {
            "address": "0xABC123def456",
            "name": "StrategyCurveBoostedFactory-YFIETH",
            "status": "Active",
            "details": {
                "totalDebt": "10000000000000000000",
                "totalLoss": "0",
                "totalGain": "500000000000000000",
                "performanceFee": 0,
                "lastReport": 1700000000,
                "debtRatio": 10000,
            },
        },
    ],
    "details": {
        "isRetired": False,
        "isHidden": False,
        "isAggregator": False,
        "isBoosted": False,
        "isAutomated": False,
        "isHighlighted": False,
        "isPool": True,
        "poolProvider": "Curve",
        "stability": "Volatile",
        "category": "Volatile",
        "stableBaseAsset": "",
    },
    "migration": {
        "available": False,
        "address": "0x0000000000000000000000000000000000000000",
        "contract": "0x0000000000000000000000000000000000000000",
    },
    "staking": {
        "address": "0x0000000000000000000000000000000000000000",
        "available": False,
        "source": "",
        "rewards": None,
    },
    "info": {
        "riskLevel": 3,
        "isRetired": False,
        "isHidden": False,
        "isBoosted": False,
        "isHighlighted": False,
        "riskScore": [1, 2, 3, 4, 5],
    },
    "featuringScore": 7890123.45,
    "pricePerShare": "1050000000000000000",
    "debts": [],
}

FAKE_VAULT_2 = {
    "address": "0xdA816459F1AB5631232FE5e97a05BBBb94970c95",
    "type": "Yearn Vault",
    "kind": "Legacy",
    "symbol": "yvDAI",
    "displaySymbol": "yvDAI",
    "formatedSymbol": "yvDAI",
    "name": "DAI yVault",
    "displayName": "DAI yVault",
    "formatedName": "DAI",
    "icon": "https://assets.yearn.fi/icons/vault.png",
    "version": "0.4.3",
    "category": "Stablecoin",
    "decimals": 18,
    "chainID": 1,
    "endorsed": True,
    "boosted": False,
    "emergency_shutdown": False,
    "token": {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "underlyingTokensAddresses": [],
        "name": "Dai Stablecoin",
        "symbol": "DAI",
        "type": "ERC20",
        "display_name": "DAI",
        "display_symbol": "DAI",
        "description": "",
        "icon": "https://assets.yearn.fi/icons/dai.png",
        "decimals": 18,
    },
    "tvl": {
        "totalAssets": "50000000000000000000000000",
        "tvl": 50000000.0,
        "price": 1.0,
    },
    "apr": {
        "type": "v2:averaged",
        "netAPR": 0.0312,
        "fees": {
            "performance": 0.2,
            "management": 0.0,
        },
        "points": {
            "weekAgo": 0.0305,
            "monthAgo": 0.0330,
            "inception": 0.0290,
        },
        "pricePerShare": {
            "today": 1.08,
            "weekAgo": 1.079,
            "monthAgo": 1.075,
        },
        "extra": {
            "stakingRewardsAPR": None,
            "gammaRewardAPR": None,
        },
        "forwardAPR": {
            "type": "v2:averaged",
            "netAPR": 0.035,
            "composite": {
                "boost": None,
                "poolAPY": None,
                "boostedAPR": None,
                "baseAPR": None,
                "cvxAPR": None,
                "rewardsAPR": None,
            },
        },
    },
    "strategies": [
        {
            "address": "0xDEF789abc012",
            "name": "StrategyLenderYieldOptimiser",
            "status": "Active",
            "details": {
                "totalDebt": "40000000000000000000000000",
                "totalLoss": "0",
                "totalGain": "1200000000000000000000000",
                "performanceFee": 0,
                "lastReport": 1699000000,
                "debtRatio": 8000,
            },
        },
        {
            "address": "0x111222333444",
            "name": "StrategyGenericLevCompFarm",
            "status": "Active",
            "details": {
                "totalDebt": "10000000000000000000000000",
                "totalLoss": "100000000000000000000",
                "totalGain": "300000000000000000000000",
                "performanceFee": 0,
                "lastReport": 1698500000,
                "debtRatio": 2000,
            },
        },
    ],
    "details": {
        "isRetired": False,
        "isHidden": False,
        "isAggregator": False,
        "isBoosted": False,
        "isAutomated": False,
        "isHighlighted": False,
        "isPool": False,
        "poolProvider": "",
        "stability": "Stable",
        "category": "Stable",
        "stableBaseAsset": "DAI",
    },
    "migration": {
        "available": False,
        "address": "0x0000000000000000000000000000000000000000",
        "contract": "0x0000000000000000000000000000000000000000",
    },
    "staking": {
        "address": "0x0000000000000000000000000000000000000000",
        "available": False,
        "source": "",
        "rewards": None,
    },
    "info": {
        "riskLevel": 1,
        "isRetired": False,
        "isHidden": False,
        "isBoosted": False,
        "isHighlighted": False,
        "riskScore": [1, 1, 1, 1, 1],
    },
    "featuringScore": 50000000.0,
    "pricePerShare": "1080000000000000000",
    "debts": [],
}

FAKE_OPTIMISM_VAULT = {
    "address": "0xOptimismVault123",
    "type": "Yearn Vault",
    "kind": "Multi Strategy",
    "symbol": "yvUSDC",
    "displaySymbol": "yvUSDC",
    "formatedSymbol": "yvUSDC",
    "name": "USDC yVault",
    "displayName": "USDC yVault",
    "formatedName": "USDC",
    "icon": "https://assets.yearn.fi/icons/vault.png",
    "version": "3.0.0",
    "category": "Stablecoin",
    "decimals": 6,
    "chainID": 10,
    "endorsed": True,
    "boosted": False,
    "emergency_shutdown": False,
    "token": {
        "address": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
        "underlyingTokensAddresses": [],
        "name": "USD Coin",
        "symbol": "USDC",
        "type": "ERC20",
        "display_name": "USDC",
        "display_symbol": "USDC",
        "description": "",
        "icon": "",
        "decimals": 6,
    },
    "tvl": {
        "totalAssets": "10000000000",
        "tvl": 10000000.0,
        "price": 1.0,
    },
    "apr": {
        "type": "v3:averaged",
        "netAPR": 0.045,
        "fees": {
            "performance": 0.1,
            "management": 0.0,
        },
        "points": {
            "weekAgo": 0.044,
            "monthAgo": 0.046,
            "inception": 0.043,
        },
        "pricePerShare": None,
        "extra": {},
        "forwardAPR": {
            "type": "v3:averaged",
            "netAPR": 0.048,
            "composite": {
                "boost": None,
                "poolAPY": None,
                "boostedAPR": None,
                "baseAPR": None,
                "cvxAPR": None,
                "rewardsAPR": None,
            },
        },
    },
    "strategies": [],
    "details": {
        "isRetired": False,
        "isHidden": False,
        "isAggregator": False,
        "isBoosted": False,
        "isAutomated": True,
        "isHighlighted": False,
        "isPool": False,
        "poolProvider": "",
        "stability": "Stable",
        "category": "Stable",
        "stableBaseAsset": "USDC",
    },
    "migration": {
        "available": False,
        "address": "0x0000000000000000000000000000000000000000",
        "contract": "0x0000000000000000000000000000000000000000",
    },
    "staking": {
        "address": "0x0000000000000000000000000000000000000000",
        "available": False,
        "source": "",
        "rewards": None,
    },
    "info": {
        "riskLevel": 1,
        "isRetired": False,
        "isHidden": False,
        "isBoosted": False,
        "isHighlighted": False,
        "riskScore": [1, 1, 1, 1, 1],
    },
    "featuringScore": 10000000.0,
    "pricePerShare": "1000000",
    "debts": [],
}

FAKE_ETH_VAULTS = [FAKE_VAULT_1, FAKE_VAULT_2]
FAKE_OP_VAULTS = [FAKE_OPTIMISM_VAULT]


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/1/vaults/all": FAKE_ETH_VAULTS,
        "/1/vaults/0x823976dA34aC45C23a8DfEa51B3Ff1Ae0D980213": FAKE_VAULT_1,
        "/1/vaults/0xdA816459F1AB5631232FE5e97a05BBBb94970c95": FAKE_VAULT_2,
        "/10/vaults/all": FAKE_OP_VAULTS,
        "/137/vaults/all": [],
        "/250/vaults/all": [],
        "/42161/vaults/all": [],
        "/8453/vaults/all": [],
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
        resp.json.return_value = []
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """YearnService with mocked HTTP client."""
    from yearn_mcp.service import YearnService

    svc = YearnService.__new__(YearnService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked YearnService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-yearn", version="0.0.1")
    srv.register(service)
    return srv

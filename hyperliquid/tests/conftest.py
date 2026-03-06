"""Shared fixtures for Hyperliquid MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src/ to path.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hyperliquid_mcp.gen.hyperliquid.v1 import hyperliquid_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")


# ---------------------------------------------------------------------------
# Fake SDK data — matches the real Hyperliquid Python SDK return shapes
# ---------------------------------------------------------------------------

FAKE_META = {
    "universe": [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 40},
        {"name": "ETH", "szDecimals": 4, "maxLeverage": 25},
        {"name": "SOL", "szDecimals": 2, "maxLeverage": 5},
    ],
}

FAKE_ALL_MIDS = {"BTC": "67000.0", "ETH": "3500.0", "SOL": "150.0"}

FAKE_L2_BOOK = {
    "coin": "BTC",
    "levels": [
        [
            {"px": "66990.0", "sz": "1.5", "n": 3},
            {"px": "66985.0", "sz": "2.0", "n": 5},
        ],
        [
            {"px": "67010.0", "sz": "0.8", "n": 2},
            {"px": "67015.0", "sz": "3.2", "n": 7},
        ],
    ],
    "time": 1700000000000,
}

FAKE_CANDLES = [
    {
        "t": 1700000000000,
        "T": 1700000060000,
        "s": "BTC",
        "i": "1h",
        "o": "67000.0",
        "c": "67100.0",
        "h": "67200.0",
        "l": "66900.0",
        "v": "500.5",
        "n": 1200,
    },
    {
        "t": 1700003600000,
        "T": 1700007200000,
        "s": "BTC",
        "i": "1h",
        "o": "67100.0",
        "c": "67050.0",
        "h": "67150.0",
        "l": "66950.0",
        "v": "300.2",
        "n": 800,
    },
]

FAKE_USER_STATE = {
    "assetPositions": [
        {
            "position": {
                "coin": "ETH",
                "szi": "2.5",
                "entryPx": "3400.0",
                "positionValue": "8500.0",
                "unrealizedPnl": "250.0",
                "returnOnEquity": "0.03",
                "liquidationPx": "2800.0",
                "leverage": {"type": "cross", "value": 10},
                "marginUsed": "850.0",
            },
            "type": "oneWay",
        },
    ],
    "crossMarginSummary": {
        "accountValue": "10000.0",
        "totalNtlPos": "8500.0",
        "totalMarginUsed": "850.0",
        "totalRawUsd": "1500.0",
    },
    "marginSummary": {
        "accountValue": "10000.0",
        "totalNtlPos": "8500.0",
        "totalMarginUsed": "850.0",
        "totalRawUsd": "1500.0",
    },
    "withdrawable": "9150.0",
}

FAKE_OPEN_ORDERS = [
    {
        "coin": "BTC",
        "side": "A",
        "limitPx": "65000.0",
        "sz": "0.1",
        "oid": 12345,
        "timestamp": 1700000000000,
    },
    {
        "coin": "ETH",
        "side": "B",
        "limitPx": "3800.0",
        "sz": "1.0",
        "oid": 12346,
        "timestamp": 1700000100000,
    },
]

FAKE_FILLS = [
    {
        "coin": "BTC",
        "px": "67000.0",
        "sz": "0.5",
        "side": "A",
        "time": 1700000000000,
        "fee": "3.35",
        "closedPnl": "0.0",
    },
    {
        "coin": "BTC",
        "px": "67500.0",
        "sz": "0.5",
        "side": "B",
        "time": 1700001000000,
        "fee": "3.375",
        "closedPnl": "250.0",
    },
]

FAKE_ORDER_RESTING = {
    "status": "ok",
    "response": {
        "type": "order",
        "data": {"statuses": [{"resting": {"oid": 99999}}]},
    },
}

FAKE_ORDER_FILLED = {
    "status": "ok",
    "response": {
        "type": "order",
        "data": {
            "statuses": [
                {"filled": {"totalSz": "0.1", "avgPx": "67000.0", "oid": 88888}}
            ]
        },
    },
}

FAKE_ORDER_ERROR = {
    "status": "ok",
    "response": {
        "type": "order",
        "data": {"statuses": [{"error": "Insufficient margin"}]},
    },
}

FAKE_CANCEL_OK = {
    "status": "ok",
    "response": {"type": "cancel", "data": {"statuses": ["success"]}},
}

FAKE_CANCEL_FAIL = {
    "status": "ok",
    "response": {"type": "cancel", "data": {"statuses": ["Order not found"]}},
}

FAKE_LEVERAGE_OK = {"status": "ok", "response": {"type": "default"}}

FAKE_TRANSFER_OK = {"status": "ok", "response": {"type": "default"}}


@pytest.fixture
def mock_info():
    """Return a MagicMock that behaves like hyperliquid.info.Info."""
    info = MagicMock()
    info.meta.return_value = FAKE_META
    info.all_mids.return_value = FAKE_ALL_MIDS
    info.l2_snapshot.return_value = FAKE_L2_BOOK
    info.candles_snapshot.return_value = FAKE_CANDLES
    info.user_state.return_value = FAKE_USER_STATE
    info.open_orders.return_value = FAKE_OPEN_ORDERS
    info.user_fills.return_value = FAKE_FILLS
    return info


@pytest.fixture
def mock_exchange():
    """Return a MagicMock that behaves like hyperliquid.exchange.Exchange."""
    exchange = MagicMock()
    exchange.order.return_value = FAKE_ORDER_RESTING
    exchange.cancel.return_value = FAKE_CANCEL_OK
    exchange.market_open.return_value = FAKE_ORDER_FILLED
    exchange.market_close.return_value = FAKE_ORDER_FILLED
    exchange.update_leverage.return_value = FAKE_LEVERAGE_OK
    exchange.usd_transfer.return_value = FAKE_TRANSFER_OK
    return exchange


@pytest.fixture
def service(mock_info, mock_exchange):
    """HyperliquidService with mocked SDK clients."""
    from hyperliquid_mcp.service import HyperliquidService

    svc = HyperliquidService.__new__(HyperliquidService)
    svc._info = mock_info
    svc._exchange = mock_exchange
    return svc


@pytest.fixture
def service_no_auth(mock_info):
    """HyperliquidService without exchange (no private key)."""
    from hyperliquid_mcp.service import HyperliquidService

    svc = HyperliquidService.__new__(HyperliquidService)
    svc._info = mock_info
    svc._exchange = None
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked HyperliquidService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-hl", version="0.0.1")
    srv.register(service)
    return srv

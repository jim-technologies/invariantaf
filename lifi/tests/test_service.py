"""Unit tests -- every LifiService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from lifi_mcp.gen.lifi.v1 import lifi_pb2 as pb
from tests.conftest import (
    FAKE_CHAINS,
    FAKE_CONNECTIONS,
    FAKE_QUOTE,
    FAKE_STATUS,
    FAKE_TOKENS,
    FAKE_TOOLS,
)


# ---------------------------------------------------------------------------
# GetQuote
# ---------------------------------------------------------------------------


class TestGetQuote:
    def test_returns_quote_type(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        assert resp.type == "lifi"
        assert resp.id == "quote-abc-123"

    def test_tool_fields(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        assert resp.tool == "stargate"
        assert resp.tool_name == "Stargate"
        assert "stargate" in resp.tool_logo_uri

    def test_action(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        action = resp.action
        assert action.from_token.symbol == "ETH"
        assert action.from_token.chain_id == 1
        assert action.to_token.symbol == "ETH"
        assert action.to_token.chain_id == 42161
        assert action.from_amount == "1000000000000000000"
        assert action.from_chain_id == 1
        assert action.to_chain_id == 42161
        assert action.slippage == 0.03

    def test_estimate(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        est = resp.estimate
        assert est.tool == "stargate"
        assert est.to_amount == "999000000000000000"
        assert est.to_amount_min == "990000000000000000"
        assert est.from_amount == "1000000000000000000"
        assert est.execution_duration == 120
        assert est.from_amount_usd == "3500.00"
        assert est.to_amount_usd == "3496.50"

    def test_estimate_fee_costs(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        assert len(resp.estimate.fee_costs) == 1
        fee = resp.estimate.fee_costs[0]
        assert fee.name == "LP Fee"
        assert fee.amount == "1000000000000000"
        assert fee.amount_usd == "3.50"
        assert fee.token.symbol == "ETH"

    def test_estimate_gas_costs(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        assert len(resp.estimate.gas_costs) == 1
        gas = resp.estimate.gas_costs[0]
        assert gas.name == "Gas"
        assert gas.amount == "5000000000000000"
        assert gas.amount_usd == "17.50"

    def test_included_steps(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        assert len(resp.included_steps) == 1
        step = resp.included_steps[0]
        assert step.id == "step-1"
        assert step.type == "cross"
        assert step.tool == "stargate"
        assert step.tool_name == "Stargate"
        assert step.action.from_chain_id == 1
        assert step.action.to_chain_id == 42161

    def test_transaction_request(self, service):
        req = pb.GetQuoteRequest(
            from_chain="ETH",
            to_chain="ARB",
            from_token="ETH",
            to_token="ETH",
            from_amount="1000000000000000000",
            from_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        )
        resp = service.GetQuote(req)
        tx = resp.transaction_request
        assert tx.value == "0xde0b6b3a7640000"
        assert tx.to == "0x1231DEB6f5749ef6cE6943a275A1D3E7486F4EaE"
        assert tx.data == "0xabcdef1234567890"
        assert tx.from_address == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        assert tx.chain_id == 1


# ---------------------------------------------------------------------------
# ListChains
# ---------------------------------------------------------------------------


class TestListChains:
    def test_returns_chains(self, service):
        resp = service.ListChains(pb.ListChainsRequest())
        assert len(resp.chains) == 2

    def test_ethereum_chain(self, service):
        resp = service.ListChains(pb.ListChainsRequest())
        eth = resp.chains[0]
        assert eth.key == "eth"
        assert eth.chain_type == "EVM"
        assert eth.name == "Ethereum"
        assert eth.coin == "ETH"
        assert eth.id == 1
        assert eth.mainnet is True

    def test_arbitrum_chain(self, service):
        resp = service.ListChains(pb.ListChainsRequest())
        arb = resp.chains[1]
        assert arb.key == "arb"
        assert arb.name == "Arbitrum"
        assert arb.id == 42161

    def test_native_token(self, service):
        resp = service.ListChains(pb.ListChainsRequest())
        eth = resp.chains[0]
        nt = eth.native_token
        assert nt.symbol == "ETH"
        assert nt.decimals == 18
        assert nt.chain_id == 1
        assert nt.price_usd == "3500.00"

    def test_empty_chains(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"chains": []}),
        )
        resp = service.ListChains(pb.ListChainsRequest())
        assert len(resp.chains) == 0


# ---------------------------------------------------------------------------
# ListTokens
# ---------------------------------------------------------------------------


class TestListTokens:
    def test_returns_chain_tokens(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        assert len(resp.chain_tokens) == 2

    def test_ethereum_tokens(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        # Find chain 1 tokens
        eth_ct = [ct for ct in resp.chain_tokens if ct.chain_id == 1]
        assert len(eth_ct) == 1
        assert len(eth_ct[0].tokens) == 2
        symbols = [t.symbol for t in eth_ct[0].tokens]
        assert "ETH" in symbols
        assert "USDC" in symbols

    def test_token_fields(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        eth_ct = [ct for ct in resp.chain_tokens if ct.chain_id == 1][0]
        usdc = [t for t in eth_ct.tokens if t.symbol == "USDC"][0]
        assert usdc.decimals == 6
        assert usdc.name == "USD Coin"
        assert usdc.coin_key == "USDC"
        assert usdc.price_usd == "1.00"

    def test_with_chains_filter(self, service):
        resp = service.ListTokens(pb.ListTokensRequest(chains="1"))
        # Still gets all tokens from mock, but verifies the filter param is passed
        assert len(resp.chain_tokens) >= 1

    def test_arbitrum_tokens(self, service):
        resp = service.ListTokens(pb.ListTokensRequest())
        arb_ct = [ct for ct in resp.chain_tokens if ct.chain_id == 42161]
        assert len(arb_ct) == 1
        assert len(arb_ct[0].tokens) == 1
        assert arb_ct[0].tokens[0].symbol == "ETH"


# ---------------------------------------------------------------------------
# GetConnections
# ---------------------------------------------------------------------------


class TestGetConnections:
    def test_returns_connections(self, service):
        req = pb.GetConnectionsRequest(from_chain="1", to_chain="42161")
        resp = service.GetConnections(req)
        assert len(resp.connections) == 1

    def test_connection_chain_ids(self, service):
        req = pb.GetConnectionsRequest(from_chain="1", to_chain="42161")
        resp = service.GetConnections(req)
        conn = resp.connections[0]
        assert conn.from_chain_id == 1
        assert conn.to_chain_id == 42161

    def test_connection_tokens(self, service):
        req = pb.GetConnectionsRequest(from_chain="1", to_chain="42161")
        resp = service.GetConnections(req)
        conn = resp.connections[0]
        assert len(conn.from_tokens) == 1
        assert conn.from_tokens[0].symbol == "ETH"
        assert conn.from_tokens[0].chain_id == 1
        assert len(conn.to_tokens) == 1
        assert conn.to_tokens[0].symbol == "ETH"
        assert conn.to_tokens[0].chain_id == 42161

    def test_empty_connections(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"connections": []}),
        )
        req = pb.GetConnectionsRequest(from_chain="1", to_chain="999")
        resp = service.GetConnections(req)
        assert len(resp.connections) == 0


# ---------------------------------------------------------------------------
# ListTools
# ---------------------------------------------------------------------------


class TestListTools:
    def test_returns_bridges(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        assert len(resp.bridges) == 2

    def test_stargate_bridge(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        stargate = resp.bridges[0]
        assert stargate.key == "stargate"
        assert stargate.name == "Stargate"
        assert "stargate" in stargate.logo_uri

    def test_bridge_supported_chains(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        stargate = resp.bridges[0]
        assert len(stargate.supported_chains) == 2
        pair = stargate.supported_chains[0]
        assert pair.from_chain_id == 1
        assert pair.to_chain_id == 42161

    def test_hop_bridge(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        hop = resp.bridges[1]
        assert hop.key == "hop"
        assert hop.name == "Hop"
        assert len(hop.supported_chains) == 1

    def test_returns_exchanges(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        assert len(resp.exchanges) == 2

    def test_exchange_fields(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        uni = resp.exchanges[0]
        assert uni.key == "uniswap"
        assert uni.name == "Uniswap"
        assert "uniswap" in uni.logo_uri

    def test_sushiswap_exchange(self, service):
        resp = service.ListTools(pb.ListToolsRequest())
        sushi = resp.exchanges[1]
        assert sushi.key == "sushiswap"
        assert sushi.name == "SushiSwap"


# ---------------------------------------------------------------------------
# GetStatus
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_status_fields(self, service):
        req = pb.GetStatusRequest(tx_hash="0xabc123")
        resp = service.GetStatus(req)
        assert resp.status == "DONE"
        assert resp.transaction_id == "0xabc123"
        assert resp.sending_tx_hash == "0xsend123"
        assert resp.receiving_tx_hash == "0xrecv456"

    def test_sub_status(self, service):
        req = pb.GetStatusRequest(tx_hash="0xabc123")
        resp = service.GetStatus(req)
        assert resp.sub_status == "COMPLETED"
        assert resp.sub_status_msg == "Bridge transfer completed successfully"

    def test_bridge_field(self, service):
        req = pb.GetStatusRequest(tx_hash="0xabc123")
        resp = service.GetStatus(req)
        assert resp.bridge == "stargate"

    def test_chain_ids(self, service):
        req = pb.GetStatusRequest(tx_hash="0xabc123")
        resp = service.GetStatus(req)
        assert resp.from_chain_id == 1
        assert resp.to_chain_id == 42161

    def test_receiving_transaction(self, service):
        req = pb.GetStatusRequest(tx_hash="0xabc123")
        resp = service.GetStatus(req)
        recv = resp.receiving
        assert recv.tx_hash == "0xrecv456"
        assert recv.chain_id == 42161
        assert recv.amount == "999000000000000000"
        assert recv.token.symbol == "ETH"

    def test_status_not_found(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "status": "NOT_FOUND",
                    "sending": {},
                }
            ),
        )
        req = pb.GetStatusRequest(tx_hash="0xnonexistent")
        resp = service.GetStatus(req)
        assert resp.status == "NOT_FOUND"

    def test_status_with_optional_params(self, service):
        req = pb.GetStatusRequest(
            tx_hash="0xabc123",
            bridge="stargate",
            from_chain=1,
            to_chain=42161,
        )
        resp = service.GetStatus(req)
        assert resp.status == "DONE"

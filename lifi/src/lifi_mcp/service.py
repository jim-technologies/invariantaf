"""LifiService -- wraps the Li.Fi cross-chain bridge/DEX aggregator API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from lifi_mcp.gen.lifi.v1 import lifi_pb2 as pb

_BASE_URL = "https://li.quest/v1"


def _parse_token(raw: dict) -> pb.Token:
    """Convert a raw JSON token object to a Token proto."""
    return pb.Token(
        address=raw.get("address", ""),
        chain_id=raw.get("chainId", 0),
        symbol=raw.get("symbol", ""),
        decimals=raw.get("decimals", 0),
        name=raw.get("name", ""),
        coin_key=raw.get("coinKey", ""),
        logo_uri=raw.get("logoURI", ""),
        price_usd=raw.get("priceUSD", ""),
    )


def _parse_cost(raw: dict) -> pb.Cost:
    """Convert a raw JSON cost/fee object to a Cost proto."""
    return pb.Cost(
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        token=_parse_token(raw["token"]) if raw.get("token") else None,
        amount=raw.get("amount", ""),
        amount_usd=raw.get("amountUSD", ""),
    )


def _parse_estimate(raw: dict) -> pb.Estimate:
    """Convert a raw JSON estimate object to an Estimate proto."""
    fee_costs = [_parse_cost(c) for c in raw.get("feeCosts", []) or []]
    gas_costs = [_parse_cost(c) for c in raw.get("gasCosts", []) or []]
    return pb.Estimate(
        tool=raw.get("tool", ""),
        approval_address=raw.get("approvalAddress", ""),
        to_amount_min=raw.get("toAmountMin", ""),
        to_amount=raw.get("toAmount", ""),
        from_amount=raw.get("fromAmount", ""),
        fee_costs=fee_costs,
        gas_costs=gas_costs,
        execution_duration=raw.get("executionDuration", 0),
        from_amount_usd=raw.get("fromAmountUSD", ""),
        to_amount_usd=raw.get("toAmountUSD", ""),
    )


def _parse_action(raw: dict) -> pb.Action:
    """Convert a raw JSON action object to an Action proto."""
    return pb.Action(
        from_token=_parse_token(raw["fromToken"]) if raw.get("fromToken") else None,
        from_amount=raw.get("fromAmount", ""),
        to_token=_parse_token(raw["toToken"]) if raw.get("toToken") else None,
        from_chain_id=raw.get("fromChainId", 0),
        to_chain_id=raw.get("toChainId", 0),
        slippage=raw.get("slippage", 0),
        from_address=raw.get("fromAddress", ""),
        to_address=raw.get("toAddress", ""),
    )


def _parse_step(raw: dict) -> pb.Step:
    """Convert a raw JSON step object to a Step proto."""
    tool_details = raw.get("toolDetails", {})
    return pb.Step(
        id=raw.get("id", ""),
        type=raw.get("type", ""),
        tool=raw.get("tool", ""),
        tool_name=tool_details.get("name", ""),
        tool_logo_uri=tool_details.get("logoURI", ""),
        action=_parse_action(raw["action"]) if raw.get("action") else None,
        estimate=_parse_estimate(raw["estimate"]) if raw.get("estimate") else None,
    )


def _parse_tx_request(raw: dict) -> pb.TransactionRequest:
    """Convert a raw JSON transaction request to a TransactionRequest proto."""
    return pb.TransactionRequest(
        value=raw.get("value", ""),
        to=raw.get("to", ""),
        data=raw.get("data", ""),
        from_address=raw.get("from", ""),
        chain_id=raw.get("chainId", 0),
        gas_price=raw.get("gasPrice", ""),
        gas_limit=raw.get("gasLimit", ""),
    )


class LifiService:
    """Implements LifiService RPCs via the free Li.Fi API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    # ----- RPCs -----

    def GetQuote(self, request: Any, context: Any = None) -> pb.GetQuoteResponse:
        params = {
            "fromChain": request.from_chain,
            "toChain": request.to_chain,
            "fromToken": request.from_token,
            "toToken": request.to_token,
            "fromAmount": request.from_amount,
            "fromAddress": request.from_address,
        }
        raw = self._get("/quote", params=params)
        tool_details = raw.get("toolDetails", {})
        return pb.GetQuoteResponse(
            type=raw.get("type", ""),
            id=raw.get("id", ""),
            tool=raw.get("tool", ""),
            tool_name=tool_details.get("name", ""),
            tool_logo_uri=tool_details.get("logoURI", ""),
            action=_parse_action(raw["action"]) if raw.get("action") else None,
            estimate=_parse_estimate(raw["estimate"]) if raw.get("estimate") else None,
            included_steps=[_parse_step(s) for s in raw.get("includedSteps", [])],
            transaction_request=(
                _parse_tx_request(raw["transactionRequest"])
                if raw.get("transactionRequest")
                else None
            ),
        )

    def ListChains(self, request: Any, context: Any = None) -> pb.ListChainsResponse:
        raw = self._get("/chains")
        chains = []
        for c in raw.get("chains", []):
            nt = c.get("nativeToken")
            chains.append(
                pb.Chain(
                    key=c.get("key", ""),
                    chain_type=c.get("chainType", ""),
                    name=c.get("name", ""),
                    coin=c.get("coin", ""),
                    id=c.get("id", 0),
                    mainnet=c.get("mainnet", False),
                    logo_uri=c.get("logoURI", ""),
                    native_token=_parse_token(nt) if nt else None,
                )
            )
        return pb.ListChainsResponse(chains=chains)

    def ListTokens(self, request: Any, context: Any = None) -> pb.ListTokensResponse:
        params = {}
        chains_val = request.chains if hasattr(request, "chains") and request.chains else ""
        if chains_val:
            params["chains"] = chains_val
        raw = self._get("/tokens", params=params or None)
        chain_tokens = []
        tokens_map = raw.get("tokens", {})
        for chain_id_str, token_list in tokens_map.items():
            tokens = [_parse_token(t) for t in token_list]
            chain_tokens.append(
                pb.ChainTokens(
                    chain_id=int(chain_id_str),
                    tokens=tokens,
                )
            )
        return pb.ListTokensResponse(chain_tokens=chain_tokens)

    def GetConnections(
        self, request: Any, context: Any = None
    ) -> pb.GetConnectionsResponse:
        params = {}
        if hasattr(request, "from_chain") and request.from_chain:
            params["fromChain"] = request.from_chain
        if hasattr(request, "to_chain") and request.to_chain:
            params["toChain"] = request.to_chain
        raw = self._get("/connections", params=params or None)
        connections = []
        for conn in raw.get("connections", []):
            from_tokens = [_parse_token(t) for t in conn.get("fromTokens", [])]
            to_tokens = [_parse_token(t) for t in conn.get("toTokens", [])]
            connections.append(
                pb.Connection(
                    from_chain_id=conn.get("fromChainId", 0),
                    to_chain_id=conn.get("toChainId", 0),
                    from_tokens=from_tokens,
                    to_tokens=to_tokens,
                )
            )
        return pb.GetConnectionsResponse(connections=connections)

    def ListTools(self, request: Any, context: Any = None) -> pb.ListToolsResponse:
        raw = self._get("/tools")
        bridges = []
        for b in raw.get("bridges", []):
            supported = []
            for pair in b.get("supportedChains", []):
                supported.append(
                    pb.ChainPair(
                        from_chain_id=pair.get("fromChainId", 0),
                        to_chain_id=pair.get("toChainId", 0),
                    )
                )
            bridges.append(
                pb.BridgeTool(
                    key=b.get("key", ""),
                    name=b.get("name", ""),
                    logo_uri=b.get("logoURI", ""),
                    supported_chains=supported,
                )
            )
        exchanges = []
        for e in raw.get("exchanges", []):
            exchanges.append(
                pb.Tool(
                    key=e.get("key", ""),
                    name=e.get("name", ""),
                    logo_uri=e.get("logoURI", ""),
                )
            )
        return pb.ListToolsResponse(bridges=bridges, exchanges=exchanges)

    def GetStatus(self, request: Any, context: Any = None) -> pb.GetStatusResponse:
        params: dict[str, Any] = {"txHash": request.tx_hash}
        if hasattr(request, "bridge") and request.bridge:
            params["bridge"] = request.bridge
        if hasattr(request, "from_chain") and request.from_chain:
            params["fromChain"] = request.from_chain
        if hasattr(request, "to_chain") and request.to_chain:
            params["toChain"] = request.to_chain
        raw = self._get("/status", params=params)
        receiving_raw = raw.get("receiving", {})
        receiving = None
        if receiving_raw:
            receiving = pb.ReceivingTransaction(
                tx_hash=receiving_raw.get("txHash", ""),
                chain_id=receiving_raw.get("chainId", 0),
                amount=receiving_raw.get("amount", ""),
                token=(
                    _parse_token(receiving_raw["token"])
                    if receiving_raw.get("token")
                    else None
                ),
            )
        return pb.GetStatusResponse(
            transaction_id=raw.get("transactionId", ""),
            sending_tx_hash=raw.get("sending", {}).get("txHash", ""),
            receiving_tx_hash=receiving_raw.get("txHash", "") if receiving_raw else "",
            status=raw.get("status", ""),
            sub_status=raw.get("substatus", raw.get("subStatus", "")),
            sub_status_msg=raw.get("substatusMessage", raw.get("subStatusMsg", "")),
            bridge=raw.get("bridge", raw.get("tool", "")),
            from_chain_id=raw.get("sending", {}).get("chainId", 0),
            to_chain_id=raw.get("receiving", {}).get("chainId", 0) if raw.get("receiving") else 0,
            receiving=receiving,
        )

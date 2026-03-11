package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	pb "github.com/jim-technologies/invariantaf/quicknode/quicknode/v1"
)

// ─── Mock Servers ────────────────────────────────────────────────────────────

func mockRESTServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		// Chains
		case r.URL.Path == "/v0/chains" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"name": "ethereum", "network": "mainnet", "status": "available"},
					map[string]any{"name": "solana", "network": "mainnet-beta", "status": "available"},
				},
			})

		// List Endpoints
		case r.URL.Path == "/v0/endpoints" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"id": "ep-1", "name": "My Eth Node", "chain": "ethereum",
						"network": "mainnet", "http_url": "https://example.quiknode.pro/abc",
						"wss_url": "wss://example.quiknode.pro/abc", "status": "active",
						"created_at": "2024-01-01T00:00:00Z", "plan": "build",
					},
				},
			})

		// Create Endpoint
		case r.URL.Path == "/v0/endpoints" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "ep-new", "name": "New Node", "chain": "solana",
				"network": "mainnet-beta", "http_url": "https://new.quiknode.pro/xyz",
				"wss_url": "wss://new.quiknode.pro/xyz", "status": "active",
			})

		// Get Endpoint
		case strings.HasPrefix(r.URL.Path, "/v0/endpoints/") && r.Method == http.MethodGet && !strings.Contains(r.URL.Path, "/"):
			json.NewEncoder(w).Encode(map[string]any{
				"id": "ep-1", "name": "My Eth Node", "chain": "ethereum",
				"network": "mainnet", "status": "active",
			})

		// Delete Endpoint
		case strings.HasPrefix(r.URL.Path, "/v0/endpoints/") && r.Method == http.MethodDelete:
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]any{})

		// Endpoint Metrics
		case strings.HasSuffix(r.URL.Path, "/metrics") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"total_calls": float64(1000), "success_count": float64(950),
				"error_count": float64(50), "max_response_time_ms": 250.5,
				"avg_response_time_ms": 45.2,
			})

		// Endpoint Logs
		case strings.HasSuffix(r.URL.Path, "/logs") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"request_id": "req-1", "method": "eth_blockNumber",
						"status_code": float64(200), "response_time_ms": 12.5,
						"timestamp": "2024-01-01T00:00:00Z",
					},
				},
			})

		// Usage
		case r.URL.Path == "/v0/usage/rpc" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"total_credits": float64(5000), "total_requests": float64(10000),
			})

		// Usage by endpoint
		case r.URL.Path == "/v0/usage/rpc/by-endpoint" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"endpoint_id": "ep-1", "name": "My Eth Node", "credits": float64(3000), "requests": float64(6000)},
				},
			})

		// Usage by method
		case r.URL.Path == "/v0/usage/rpc/by-method" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"method": "eth_blockNumber", "credits": float64(100), "requests": float64(500)},
				},
			})

		// Usage by chain
		case r.URL.Path == "/v0/usage/rpc/by-chain" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"chain": "ethereum", "network": "mainnet", "credits": float64(4000), "requests": float64(8000)},
				},
			})

		// Billing - Invoices
		case r.URL.Path == "/v0/billing/invoices" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"id": "inv-1", "amount": float64(9900), "currency": "usd", "status": "paid", "date": "2024-01-01"},
				},
			})

		// Billing - Payments
		case r.URL.Path == "/v0/billing/payments" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"id": "pay-1", "amount": float64(9900), "currency": "usd", "status": "succeeded", "date": "2024-01-01"},
				},
			})

		// Security Options
		case strings.HasSuffix(r.URL.Path, "/security_options") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"token_auth_enabled": true, "jwt_auth_enabled": false,
				"ip_allowlist_enabled": true, "referrer_allowlist_enabled": false,
				"domain_mask_enabled": false,
			})

		// Endpoint Tags
		case strings.HasSuffix(r.URL.Path, "/tags") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"id": "tag-1", "key": "env", "value": "prod"},
				},
			})

		// Endpoint Tags - Create
		case strings.HasSuffix(r.URL.Path, "/tags") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "tag-2", "key": "team", "value": "backend",
			})

		// ─── Streams ─────────────────────────────────────────────────

		// Create Stream
		case r.URL.Path == "/streams/rest/v1/streams" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "stream-1", "name": "Eth Blocks", "network": "ethereum-mainnet",
				"dataset": "block", "status": "active", "region": "us-east-1",
			})

		// List Streams
		case r.URL.Path == "/streams/rest/v1/streams" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data":  []any{map[string]any{"id": "stream-1", "name": "Eth Blocks", "status": "active"}},
				"total": float64(1),
			})

		// Enabled stream count (must be before general /streams/ prefix match)
		case r.URL.Path == "/streams/rest/v1/streams/enabled_count":
			json.NewEncoder(w).Encode(map[string]any{"count": float64(5)})

		// Pause Stream
		case strings.HasSuffix(r.URL.Path, "/pause") && strings.Contains(r.URL.Path, "/streams/"):
			json.NewEncoder(w).Encode(map[string]any{
				"id": "stream-1", "name": "Eth Blocks", "status": "paused",
			})

		// Activate Stream
		case strings.HasSuffix(r.URL.Path, "/activate") && strings.Contains(r.URL.Path, "/streams/"):
			json.NewEncoder(w).Encode(map[string]any{
				"id": "stream-1", "name": "Eth Blocks", "status": "active",
			})

		// Get Stream
		case strings.HasPrefix(r.URL.Path, "/streams/rest/v1/streams/") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "stream-1", "name": "Eth Blocks", "status": "active",
			})

		// Delete Stream
		case strings.HasPrefix(r.URL.Path, "/streams/rest/v1/streams/") && r.Method == http.MethodDelete:
			json.NewEncoder(w).Encode(map[string]any{})

		// Test filter
		case r.URL.Path == "/streams/rest/v1/streams/test_filter":
			json.NewEncoder(w).Encode(map[string]any{
				"valid": true, "output": "filtered data",
			})

		// ─── Webhooks ────────────────────────────────────────────────

		// List Webhooks
		case r.URL.Path == "/webhooks" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{"id": "wh-1", "name": "My Webhook", "status": "active"},
				},
			})

		// Enabled webhook count (must be before general /webhooks/ prefix match)
		case r.URL.Path == "/webhooks/enabled-count":
			json.NewEncoder(w).Encode(map[string]any{"count": float64(3)})

		// Create Webhook
		case strings.HasPrefix(r.URL.Path, "/webhooks/template/") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "wh-new", "name": "New Webhook", "status": "active",
			})

		// Get Webhook
		case strings.HasPrefix(r.URL.Path, "/webhooks/") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"id": "wh-1", "name": "My Webhook", "status": "active",
			})

		// ─── Key-Value Store ─────────────────────────────────────────

		// Create List
		case r.URL.Path == "/kv/rest/v1/lists" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"key":   "my-list",
				"items": []any{"item1", "item2"},
			})

		// List Lists
		case r.URL.Path == "/kv/rest/v1/lists" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{"list-a", "list-b"},
			})

		// Get List
		case strings.HasPrefix(r.URL.Path, "/kv/rest/v1/lists/") && r.Method == http.MethodGet && !strings.Contains(r.URL.Path, "/contains/"):
			json.NewEncoder(w).Encode(map[string]any{
				"key":   "my-list",
				"items": []any{"item1", "item2", "item3"},
			})

		// Check Contains
		case strings.Contains(r.URL.Path, "/contains/"):
			json.NewEncoder(w).Encode(map[string]any{"contains": true})

		// Create Set
		case r.URL.Path == "/kv/rest/v1/sets" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"key": "my-key", "value": "my-value",
			})

		// List Sets
		case r.URL.Path == "/kv/rest/v1/sets" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{"set-a", "set-b"},
			})

		// Get Set
		case strings.HasPrefix(r.URL.Path, "/kv/rest/v1/sets/") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"key": "my-key", "value": "my-value",
			})

		// Bulk Sets
		case r.URL.Path == "/kv/rest/v1/sets/bulk" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"created": float64(2), "deleted": float64(1),
			})

		// ─── IPFS ────────────────────────────────────────────────────

		// Pin Object
		case r.URL.Path == "/ipfs/rest/v1/pinning" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"requestid": "req-ipfs-1", "cid": "QmTest123", "status": "pinned", "name": "test",
			})

		// List Pinned
		case r.URL.Path == "/ipfs/rest/v1/pinning" && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"data":  []any{map[string]any{"requestid": "req-ipfs-1", "cid": "QmTest123", "status": "pinned"}},
				"total": float64(1),
			})

		// IPFS Usage
		case r.URL.Path == "/ipfs/rest/v1/account/usage":
			json.NewEncoder(w).Encode(map[string]any{
				"bandwidth_bytes": float64(1048576), "storage_bytes": float64(524288), "pinned_count": float64(10),
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"error": "not found"})
		}
	}))
}

func mockRPCServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		var req map[string]any
		json.NewDecoder(r.Body).Decode(&req)
		method := req["method"].(string)
		id := req["id"]

		switch method {
		case "qn_fetchNFTs":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"owner":      "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
					"totalItems": float64(2), "totalPages": float64(1), "pageNumber": float64(1),
					"assets": []any{
						map[string]any{
							"collectionAddress": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
							"tokenId": "1234", "name": "Bored Ape #1234",
							"collectionName": "BAYC", "tokenType": "ERC-721",
						},
					},
				},
			})

		case "qn_getWalletTokenBalance":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"owner":      "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
					"totalItems": float64(1), "totalPages": float64(1), "pageNumber": float64(1),
					"result": []any{
						map[string]any{
							"contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
							"name": "USD Coin", "symbol": "USDC", "decimals": float64(6),
							"totalBalance": "1000000",
						},
					},
				},
			})

		case "qn_getTokenMetadataByContractAddress":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
					"name": "USD Coin", "symbol": "USDC", "decimals": float64(6),
					"totalSupply": "40000000000000000",
				},
			})

		case "qn_resolveENS":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
					"ensName": "vitalik.eth",
				},
			})

		case "qn_getContractABI":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"abi": `[{"type":"function","name":"transfer"}]`,
				},
			})

		case "qn_estimatePriorityFees":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"low":         map[string]any{"per_compute_unit": "100"},
					"medium":      map[string]any{"per_compute_unit": "500"},
					"high":        map[string]any{"per_compute_unit": "1000"},
					"extreme":     map[string]any{"per_compute_unit": "5000"},
					"recommended": map[string]any{"per_compute_unit": "750"},
				},
			})

		case "getAsset":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"id": "FNftbceNV8PEr...", "interface": "V1_NFT",
					"content": map[string]any{
						"metadata": map[string]any{"name": "Mad Lad #1", "symbol": "MAD", "description": "A mad lad"},
						"json_uri": "https://arweave.net/xxx",
						"links":    map[string]any{"image": "https://arweave.net/img"},
					},
					"ownership":   map[string]any{"owner": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"},
					"compression": map[string]any{"compressed": true},
					"mutable":     true,
					"royalty":     map[string]any{"basis_points": float64(500)},
					"grouping": []any{
						map[string]any{"group_key": "collection", "group_value": "J1S9H3QjnRtBbbuD4HjPV6RpRhwuk4zKbxsnCHuTgh9w"},
					},
				},
			})

		case "getAssetProof":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"id": "FNftbceNV8PEr...", "root": "root-hash",
					"proof":      []any{"proof-1", "proof-2"},
					"tree_id":    "tree-123",
					"node_index": float64(42),
				},
			})

		case "getAssetsByOwner":
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"result": map[string]any{
					"total": float64(1), "page": float64(1), "limit": float64(10),
					"items": []any{
						map[string]any{
							"id": "asset-1", "interface": "V1_NFT",
							"content": map[string]any{
								"metadata": map[string]any{"name": "My NFT"},
							},
							"ownership": map[string]any{"owner": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"},
						},
					},
				},
			})

		default:
			json.NewEncoder(w).Encode(map[string]any{
				"jsonrpc": "2.0", "id": id,
				"error": map[string]any{"code": -32601, "message": "method not found"},
			})
		}
	}))
}

func newTestClient(restURL, rpcURL string) *quickNodeClient {
	return &quickNodeClient{
		apiBaseURL:  restURL,
		endpointURL: rpcURL,
		apiKey:      "test-api-key",
		client:      &http.Client{},
	}
}

// ─── Console Service Tests ──────────────────────────────────────────────────

func TestListChains(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.ListChains(context.Background(), &pb.ListChainsRequest{})
	if err != nil {
		t.Fatalf("ListChains: %v", err)
	}
	if len(resp.Chains) != 2 {
		t.Fatalf("expected 2 chains, got %d", len(resp.Chains))
	}
	if resp.Chains[0].Name != "ethereum" {
		t.Errorf("expected ethereum, got %s", resp.Chains[0].Name)
	}
	if resp.Chains[1].Name != "solana" {
		t.Errorf("expected solana, got %s", resp.Chains[1].Name)
	}
}

func TestListEndpoints(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.ListEndpoints(context.Background(), &pb.ListEndpointsRequest{})
	if err != nil {
		t.Fatalf("ListEndpoints: %v", err)
	}
	if len(resp.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint, got %d", len(resp.Endpoints))
	}
	if resp.Endpoints[0].Id != "ep-1" {
		t.Errorf("expected id=ep-1, got %s", resp.Endpoints[0].Id)
	}
	if resp.Endpoints[0].Chain != "ethereum" {
		t.Errorf("expected chain=ethereum, got %s", resp.Endpoints[0].Chain)
	}
}

func TestCreateEndpoint(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.CreateEndpoint(context.Background(), &pb.CreateEndpointRequest{
		Name: "New Node", Chain: "solana", Network: "mainnet-beta",
	})
	if err != nil {
		t.Fatalf("CreateEndpoint: %v", err)
	}
	if resp.Id != "ep-new" {
		t.Errorf("expected id=ep-new, got %s", resp.Id)
	}
}

func TestGetEndpointMetrics(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetEndpointMetrics(context.Background(), &pb.GetEndpointMetricsRequest{
		EndpointId: "ep-1",
	})
	if err != nil {
		t.Fatalf("GetEndpointMetrics: %v", err)
	}
	if resp.TotalCalls != 1000 {
		t.Errorf("expected total_calls=1000, got %d", resp.TotalCalls)
	}
	if resp.SuccessCount != 950 {
		t.Errorf("expected success_count=950, got %d", resp.SuccessCount)
	}
}

func TestGetRPCUsage(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetRPCUsage(context.Background(), &pb.GetRPCUsageRequest{
		From: "2024-01-01", To: "2024-01-31",
	})
	if err != nil {
		t.Fatalf("GetRPCUsage: %v", err)
	}
	if resp.TotalCredits != 5000 {
		t.Errorf("expected total_credits=5000, got %d", resp.TotalCredits)
	}
	if resp.TotalRequests != 10000 {
		t.Errorf("expected total_requests=10000, got %d", resp.TotalRequests)
	}
}

func TestGetRPCUsageByEndpoint(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetRPCUsageByEndpoint(context.Background(), &pb.GetRPCUsageRequest{})
	if err != nil {
		t.Fatalf("GetRPCUsageByEndpoint: %v", err)
	}
	if len(resp.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint, got %d", len(resp.Endpoints))
	}
	if resp.Endpoints[0].EndpointId != "ep-1" {
		t.Errorf("expected endpoint_id=ep-1, got %s", resp.Endpoints[0].EndpointId)
	}
}

func TestGetRPCUsageByMethod(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetRPCUsageByMethod(context.Background(), &pb.GetRPCUsageRequest{})
	if err != nil {
		t.Fatalf("GetRPCUsageByMethod: %v", err)
	}
	if len(resp.Methods) != 1 {
		t.Fatalf("expected 1 method, got %d", len(resp.Methods))
	}
	if resp.Methods[0].Method != "eth_blockNumber" {
		t.Errorf("expected method=eth_blockNumber, got %s", resp.Methods[0].Method)
	}
}

func TestGetRPCUsageByChain(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetRPCUsageByChain(context.Background(), &pb.GetRPCUsageRequest{})
	if err != nil {
		t.Fatalf("GetRPCUsageByChain: %v", err)
	}
	if len(resp.Chains) != 1 {
		t.Fatalf("expected 1 chain, got %d", len(resp.Chains))
	}
	if resp.Chains[0].Chain != "ethereum" {
		t.Errorf("expected chain=ethereum, got %s", resp.Chains[0].Chain)
	}
}

func TestListInvoices(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.ListInvoices(context.Background(), &pb.ListInvoicesRequest{})
	if err != nil {
		t.Fatalf("ListInvoices: %v", err)
	}
	if len(resp.Invoices) != 1 {
		t.Fatalf("expected 1 invoice, got %d", len(resp.Invoices))
	}
	if resp.Invoices[0].Id != "inv-1" {
		t.Errorf("expected id=inv-1, got %s", resp.Invoices[0].Id)
	}
}

func TestGetSecurityOptions(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetSecurityOptions(context.Background(), &pb.GetSecurityOptionsRequest{
		EndpointId: "ep-1",
	})
	if err != nil {
		t.Fatalf("GetSecurityOptions: %v", err)
	}
	if !resp.TokenAuthEnabled {
		t.Error("expected token_auth_enabled=true")
	}
	if resp.JwtAuthEnabled {
		t.Error("expected jwt_auth_enabled=false")
	}
	if !resp.IpAllowlistEnabled {
		t.Error("expected ip_allowlist_enabled=true")
	}
}

func TestGetEndpointTags(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	resp, err := svc.GetEndpointTags(context.Background(), &pb.GetEndpointTagsRequest{EndpointId: "ep-1"})
	if err != nil {
		t.Fatalf("GetEndpointTags: %v", err)
	}
	if len(resp.Tags) != 1 {
		t.Fatalf("expected 1 tag, got %d", len(resp.Tags))
	}
	if resp.Tags[0].Key != "env" || resp.Tags[0].Value != "prod" {
		t.Errorf("expected env=prod, got %s=%s", resp.Tags[0].Key, resp.Tags[0].Value)
	}
}

// ─── Streams Service Tests ──────────────────────────────────────────────────

func TestCreateStream(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeStreamsService{newTestClient(ts.URL, "")}

	resp, err := svc.CreateStream(context.Background(), &pb.CreateStreamRequest{
		Name: "Eth Blocks", Network: "ethereum-mainnet", Dataset: "block",
	})
	if err != nil {
		t.Fatalf("CreateStream: %v", err)
	}
	if resp.Id != "stream-1" {
		t.Errorf("expected id=stream-1, got %s", resp.Id)
	}
	if resp.Status != "active" {
		t.Errorf("expected status=active, got %s", resp.Status)
	}
}

func TestListStreams(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeStreamsService{newTestClient(ts.URL, "")}

	resp, err := svc.ListStreams(context.Background(), &pb.ListStreamsRequest{})
	if err != nil {
		t.Fatalf("ListStreams: %v", err)
	}
	if len(resp.Streams) != 1 {
		t.Fatalf("expected 1 stream, got %d", len(resp.Streams))
	}
	if resp.Total != 1 {
		t.Errorf("expected total=1, got %d", resp.Total)
	}
}

func TestGetEnabledStreamCount(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeStreamsService{newTestClient(ts.URL, "")}

	resp, err := svc.GetEnabledStreamCount(context.Background(), &pb.GetEnabledStreamCountRequest{})
	if err != nil {
		t.Fatalf("GetEnabledStreamCount: %v", err)
	}
	if resp.Count != 5 {
		t.Errorf("expected count=5, got %d", resp.Count)
	}
}

// ─── Webhooks Service Tests ─────────────────────────────────────────────────

func TestListWebhooks(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeWebhooksService{newTestClient(ts.URL, "")}

	resp, err := svc.ListWebhooks(context.Background(), &pb.ListWebhooksRequest{})
	if err != nil {
		t.Fatalf("ListWebhooks: %v", err)
	}
	if len(resp.Webhooks) != 1 {
		t.Fatalf("expected 1 webhook, got %d", len(resp.Webhooks))
	}
	if resp.Webhooks[0].Id != "wh-1" {
		t.Errorf("expected id=wh-1, got %s", resp.Webhooks[0].Id)
	}
}

func TestCreateWebhook(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeWebhooksService{newTestClient(ts.URL, "")}

	resp, err := svc.CreateWebhook(context.Background(), &pb.CreateWebhookRequest{
		TemplateId: "tmpl-1", Name: "New Webhook",
	})
	if err != nil {
		t.Fatalf("CreateWebhook: %v", err)
	}
	if resp.Id != "wh-new" {
		t.Errorf("expected id=wh-new, got %s", resp.Id)
	}
}

func TestGetEnabledWebhookCount(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeWebhooksService{newTestClient(ts.URL, "")}

	resp, err := svc.GetEnabledWebhookCount(context.Background(), &pb.GetEnabledWebhookCountRequest{})
	if err != nil {
		t.Fatalf("GetEnabledWebhookCount: %v", err)
	}
	if resp.Count != 3 {
		t.Errorf("expected count=3, got %d", resp.Count)
	}
}

// ─── Key-Value Store Tests ──────────────────────────────────────────────────

func TestCreateList(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.CreateList(context.Background(), &pb.CreateKVListRequest{
		Key: "my-list", Items: []string{"item1", "item2"},
	})
	if err != nil {
		t.Fatalf("CreateList: %v", err)
	}
	if resp.Key != "my-list" {
		t.Errorf("expected key=my-list, got %s", resp.Key)
	}
	if len(resp.Items) != 2 {
		t.Errorf("expected 2 items, got %d", len(resp.Items))
	}
}

func TestListLists(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.ListLists(context.Background(), &pb.ListKVListsRequest{})
	if err != nil {
		t.Fatalf("ListLists: %v", err)
	}
	if len(resp.Keys) != 2 {
		t.Errorf("expected 2 keys, got %d", len(resp.Keys))
	}
}

func TestGetList(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.GetList(context.Background(), &pb.GetKVListRequest{Key: "my-list"})
	if err != nil {
		t.Fatalf("GetList: %v", err)
	}
	if len(resp.Items) != 3 {
		t.Errorf("expected 3 items, got %d", len(resp.Items))
	}
}

func TestCheckListContains(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.CheckListContains(context.Background(), &pb.CheckKVListContainsRequest{
		Key: "my-list", Item: "item1",
	})
	if err != nil {
		t.Fatalf("CheckListContains: %v", err)
	}
	if !resp.Contains {
		t.Error("expected contains=true")
	}
}

func TestCreateSet(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.CreateSet(context.Background(), &pb.CreateKVSetRequest{
		Key: "my-key", Value: "my-value",
	})
	if err != nil {
		t.Fatalf("CreateSet: %v", err)
	}
	if resp.Key != "my-key" || resp.Value != "my-value" {
		t.Errorf("expected my-key=my-value, got %s=%s", resp.Key, resp.Value)
	}
}

func TestBulkCreateSets(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeKeyValueService{newTestClient(ts.URL, "")}

	resp, err := svc.BulkCreateSets(context.Background(), &pb.BulkCreateKVSetsRequest{
		Sets: []*pb.KVSet{
			{Key: "k1", Value: "v1"},
			{Key: "k2", Value: "v2"},
		},
		DeleteKeys: []string{"old-key"},
	})
	if err != nil {
		t.Fatalf("BulkCreateSets: %v", err)
	}
	if resp.Created != 2 {
		t.Errorf("expected created=2, got %d", resp.Created)
	}
	if resp.Deleted != 1 {
		t.Errorf("expected deleted=1, got %d", resp.Deleted)
	}
}

// ─── IPFS Tests ─────────────────────────────────────────────────────────────

func TestPinObject(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeIPFSService{newTestClient(ts.URL, "")}

	resp, err := svc.PinObject(context.Background(), &pb.PinIPFSObjectRequest{
		Cid: "QmTest123", Name: "test",
	})
	if err != nil {
		t.Fatalf("PinObject: %v", err)
	}
	if resp.Cid != "QmTest123" {
		t.Errorf("expected cid=QmTest123, got %s", resp.Cid)
	}
	if resp.Status != "pinned" {
		t.Errorf("expected status=pinned, got %s", resp.Status)
	}
}

func TestListPinnedObjects(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeIPFSService{newTestClient(ts.URL, "")}

	resp, err := svc.ListPinnedObjects(context.Background(), &pb.ListIPFSPinnedObjectsRequest{})
	if err != nil {
		t.Fatalf("ListPinnedObjects: %v", err)
	}
	if len(resp.Objects) != 1 {
		t.Fatalf("expected 1 object, got %d", len(resp.Objects))
	}
	if resp.Total != 1 {
		t.Errorf("expected total=1, got %d", resp.Total)
	}
}

func TestGetIPFSUsage(t *testing.T) {
	ts := mockRESTServer()
	defer ts.Close()
	svc := &QuickNodeIPFSService{newTestClient(ts.URL, "")}

	resp, err := svc.GetIPFSUsage(context.Background(), &pb.GetIPFSUsageRequest{})
	if err != nil {
		t.Fatalf("GetIPFSUsage: %v", err)
	}
	if resp.BandwidthBytes != 1048576 {
		t.Errorf("expected bandwidth=1048576, got %d", resp.BandwidthBytes)
	}
	if resp.PinnedCount != 10 {
		t.Errorf("expected pinned=10, got %d", resp.PinnedCount)
	}
}

// ─── Token & NFT RPC Tests ─────────────────────────────────────────────────

func TestFetchNFTs(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.FetchNFTs(context.Background(), &pb.FetchNFTsRequest{
		Wallet: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
	})
	if err != nil {
		t.Fatalf("FetchNFTs: %v", err)
	}
	if resp.Owner != "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" {
		t.Errorf("expected owner, got %s", resp.Owner)
	}
	if resp.TotalItems != 2 {
		t.Errorf("expected total_items=2, got %d", resp.TotalItems)
	}
	if len(resp.Assets) != 1 {
		t.Fatalf("expected 1 asset, got %d", len(resp.Assets))
	}
	if resp.Assets[0].Name != "Bored Ape #1234" {
		t.Errorf("expected name=Bored Ape #1234, got %s", resp.Assets[0].Name)
	}
}

func TestGetWalletTokenBalance(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.GetWalletTokenBalance(context.Background(), &pb.GetWalletTokenBalanceRequest{
		Wallet: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
	})
	if err != nil {
		t.Fatalf("GetWalletTokenBalance: %v", err)
	}
	if len(resp.Tokens) != 1 {
		t.Fatalf("expected 1 token, got %d", len(resp.Tokens))
	}
	if resp.Tokens[0].Symbol != "USDC" {
		t.Errorf("expected symbol=USDC, got %s", resp.Tokens[0].Symbol)
	}
}

func TestGetTokenMetadataByContractAddress(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.GetTokenMetadataByContractAddress(context.Background(), &pb.GetTokenMetadataByContractAddressRequest{
		ContractAddress: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
	})
	if err != nil {
		t.Fatalf("GetTokenMetadataByContractAddress: %v", err)
	}
	if resp.Symbol != "USDC" {
		t.Errorf("expected symbol=USDC, got %s", resp.Symbol)
	}
	if resp.Decimals != 6 {
		t.Errorf("expected decimals=6, got %d", resp.Decimals)
	}
}

func TestResolveENS(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.ResolveENS(context.Background(), &pb.ResolveENSRequest{
		NameOrAddress: "vitalik.eth",
	})
	if err != nil {
		t.Fatalf("ResolveENS: %v", err)
	}
	if resp.Address != "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" {
		t.Errorf("expected vitalik address, got %s", resp.Address)
	}
	if resp.EnsName != "vitalik.eth" {
		t.Errorf("expected vitalik.eth, got %s", resp.EnsName)
	}
}

func TestGetContractABI(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.GetContractABI(context.Background(), &pb.GetContractABIRequest{
		ContractAddress: "0x1234",
	})
	if err != nil {
		t.Fatalf("GetContractABI: %v", err)
	}
	if !strings.Contains(resp.Abi, "transfer") {
		t.Errorf("expected ABI to contain 'transfer', got %s", resp.Abi)
	}
}

func TestEstimatePriorityFees(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeTokenNFTService{newTestClient("", ts.URL)}

	resp, err := svc.EstimatePriorityFees(context.Background(), &pb.EstimatePriorityFeesRequest{})
	if err != nil {
		t.Fatalf("EstimatePriorityFees: %v", err)
	}
	if resp.Low == nil || resp.Low.PerComputeUnit != "100" {
		t.Errorf("expected low=100, got %v", resp.Low)
	}
	if resp.Recommended == nil || resp.Recommended.PerComputeUnit != "750" {
		t.Errorf("expected recommended=750, got %v", resp.Recommended)
	}
}

// ─── Solana DAS Tests ───────────────────────────────────────────────────────

func TestGetAsset(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeSolanaDASService{newTestClient("", ts.URL)}

	resp, err := svc.GetAsset(context.Background(), &pb.GetDASAssetRequest{
		Id: "FNftbceNV8PEr...",
	})
	if err != nil {
		t.Fatalf("GetAsset: %v", err)
	}
	if resp.Name != "Mad Lad #1" {
		t.Errorf("expected name=Mad Lad #1, got %s", resp.Name)
	}
	if resp.Symbol != "MAD" {
		t.Errorf("expected symbol=MAD, got %s", resp.Symbol)
	}
	if !resp.Compressed {
		t.Error("expected compressed=true")
	}
	if resp.RoyaltyBasisPoints != 500 {
		t.Errorf("expected royalty=500, got %d", resp.RoyaltyBasisPoints)
	}
	if resp.Collection != "J1S9H3QjnRtBbbuD4HjPV6RpRhwuk4zKbxsnCHuTgh9w" {
		t.Errorf("expected collection, got %s", resp.Collection)
	}
	if resp.ImageUri != "https://arweave.net/img" {
		t.Errorf("expected image_uri, got %s", resp.ImageUri)
	}
}

func TestGetAssetProof(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeSolanaDASService{newTestClient("", ts.URL)}

	resp, err := svc.GetAssetProof(context.Background(), &pb.GetDASAssetProofRequest{
		Id: "FNftbceNV8PEr...",
	})
	if err != nil {
		t.Fatalf("GetAssetProof: %v", err)
	}
	if resp.Root != "root-hash" {
		t.Errorf("expected root=root-hash, got %s", resp.Root)
	}
	if len(resp.Proof) != 2 {
		t.Errorf("expected 2 proof nodes, got %d", len(resp.Proof))
	}
	if resp.NodeIndex != 42 {
		t.Errorf("expected node_index=42, got %d", resp.NodeIndex)
	}
}

func TestGetAssetsByOwner(t *testing.T) {
	ts := mockRPCServer()
	defer ts.Close()
	svc := &QuickNodeSolanaDASService{newTestClient("", ts.URL)}

	resp, err := svc.GetAssetsByOwner(context.Background(), &pb.GetDASAssetsByOwnerRequest{
		OwnerAddress: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
		Page:         1,
		Limit:        10,
	})
	if err != nil {
		t.Fatalf("GetAssetsByOwner: %v", err)
	}
	if resp.Total != 1 {
		t.Errorf("expected total=1, got %d", resp.Total)
	}
	if len(resp.Items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(resp.Items))
	}
	if resp.Items[0].Name != "My NFT" {
		t.Errorf("expected name=My NFT, got %s", resp.Items[0].Name)
	}
}

// ─── Error Handling ─────────────────────────────────────────────────────────

func TestRESTErrorHandling(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte(`{"error": "invalid api key"}`))
	}))
	defer ts.Close()
	svc := &QuickNodeConsoleService{newTestClient(ts.URL, "")}

	_, err := svc.ListChains(context.Background(), &pb.ListChainsRequest{})
	if err == nil {
		t.Fatal("expected error for 401 response")
	}
	if !strings.Contains(err.Error(), "401") {
		t.Errorf("expected error to contain 401, got %s", err.Error())
	}
}

func TestRPCMissingEndpointURL(t *testing.T) {
	svc := &QuickNodeTokenNFTService{&quickNodeClient{
		apiBaseURL: "https://api.quicknode.com",
		client:     &http.Client{},
	}}

	_, err := svc.FetchNFTs(context.Background(), &pb.FetchNFTsRequest{
		Wallet: "0x123",
	})
	if err == nil {
		t.Fatal("expected error when QUICKNODE_ENDPOINT_URL is not set")
	}
	if !strings.Contains(err.Error(), "QUICKNODE_ENDPOINT_URL") {
		t.Errorf("expected actionable error about QUICKNODE_ENDPOINT_URL, got %s", err.Error())
	}
}

package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockPendleServer creates a test server that returns realistic Pendle API responses.
func mockPendleServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/v1/markets/all"):
			json.NewEncoder(w).Encode(map[string]any{
				"results": []any{
					map[string]any{
						"address":       "0x27b1dacd74688af24a64bd3c9c1b143118740784",
						"name":          "PT-stETH-26DEC2024",
						"chainId":       float64(1),
						"expiry":        "2024-12-26T00:00:00Z",
						"pt":            map[string]any{"address": "0xpt1111"},
						"yt":            map[string]any{"address": "0xyt1111"},
						"sy":            map[string]any{"address": "0xsy1111"},
						"underlyingAsset": map[string]any{"symbol": "stETH"},
						"tvl":           float64(15000000),
						"impliedApy":    0.05,
						"underlyingApy": 0.035,
					},
					map[string]any{
						"address":       "0xabc123def456789012345678901234567890abcd",
						"name":          "PT-aUSDC-27MAR2025",
						"chainId":       float64(42161),
						"expiry":        "2025-03-27T00:00:00Z",
						"pt":            map[string]any{"address": "0xpt2222"},
						"yt":            map[string]any{"address": "0xyt2222"},
						"sy":            map[string]any{"address": "0xsy2222"},
						"underlyingAsset": map[string]any{"symbol": "aUSDC"},
						"tvl":           float64(8000000),
						"impliedApy":    0.08,
						"underlyingApy": 0.045,
					},
				},
				"total": float64(2),
			})

		case strings.Contains(r.URL.Path, "/historical-data"):
			json.NewEncoder(w).Encode(map[string]any{
				"results": []any{
					map[string]any{
						"timestamp":     "2024-01-01T00:00:00Z",
						"tvl":           float64(12000000),
						"impliedApy":    0.042,
						"underlyingApy": 0.033,
						"volume":        float64(500000),
					},
					map[string]any{
						"timestamp":     "2024-01-02T00:00:00Z",
						"tvl":           float64(12500000),
						"impliedApy":    0.045,
						"underlyingApy": 0.034,
						"volume":        float64(600000),
					},
					map[string]any{
						"timestamp":     "2024-01-03T00:00:00Z",
						"tvl":           float64(13000000),
						"impliedApy":    0.048,
						"underlyingApy": 0.035,
						"volume":        float64(550000),
					},
				},
			})

		case strings.Contains(r.URL.Path, "/data"):
			json.NewEncoder(w).Encode(map[string]any{
				"address":       "0x27b1dacd74688af24a64bd3c9c1b143118740784",
				"chainId":       float64(1),
				"tvl":           float64(15000000),
				"impliedApy":    0.05,
				"underlyingApy": 0.035,
				"fixedApy":      0.048,
				"volume24h":     float64(1200000),
				"totalFees":     float64(50000),
				"ptPrice":       0.97,
				"ytPrice":       0.03,
				"liquidity":     float64(10000000),
				"expiry":        "2024-12-26T00:00:00Z",
			})

		case strings.Contains(r.URL.Path, "/v1/prices/assets"):
			json.NewEncoder(w).Encode(map[string]any{
				"0x27b1dacd74688af24a64bd3c9c1b143118740784": float64(2500.50),
				"0xabc123def456789012345678901234567890abcd":  float64(1.0),
				"0xpt1111": float64(2425.25),
				"0xyt1111": float64(75.25),
			})

		case strings.Contains(r.URL.Path, "/swapping-prices"):
			json.NewEncoder(w).Encode(map[string]any{
				"ptPrice": 0.97,
				"ytPrice": 0.03,
				"market":  "0x27b1dacd74688af24a64bd3c9c1b143118740784",
				"chainId": float64(1),
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *PendleService {
	return &PendleService{
		baseURL: serverURL,
		client:  &http.Client{},
	}
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

// --- Mock Tests ---

func TestListMarkets(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	results := fields["results"]
	if results == nil {
		t.Fatal("response has no 'results' field")
	}
	items := results.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 markets, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "PT-stETH-26DEC2024" {
		t.Errorf("name = %q, want %q", got, "PT-stETH-26DEC2024")
	}
	if got := first["chainId"].GetNumberValue(); got != 1 {
		t.Errorf("chainId = %v, want 1", got)
	}
	if got := first["tvl"].GetNumberValue(); got != 15000000 {
		t.Errorf("tvl = %v, want 15000000", got)
	}
	if got := first["impliedApy"].GetNumberValue(); got != 0.05 {
		t.Errorf("impliedApy = %v, want 0.05", got)
	}

	total := fields["total"].GetNumberValue()
	if total != 2 {
		t.Errorf("total = %v, want 2", total)
	}
}

func TestListMarketsWithChainFilter(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"limit":    float64(10),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	results := resp.GetFields()["results"]
	if results == nil {
		t.Fatal("response has no 'results' field")
	}
	items := results.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 market")
	}
}

func TestGetMarketData(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetMarketData(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"address":  "0x27b1dacd74688af24a64bd3c9c1b143118740784",
	}))
	if err != nil {
		t.Fatalf("GetMarketData: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["tvl"].GetNumberValue(); got != 15000000 {
		t.Errorf("tvl = %v, want 15000000", got)
	}
	if got := fields["impliedApy"].GetNumberValue(); got != 0.05 {
		t.Errorf("impliedApy = %v, want 0.05", got)
	}
	if got := fields["fixedApy"].GetNumberValue(); got != 0.048 {
		t.Errorf("fixedApy = %v, want 0.048", got)
	}
	if got := fields["ptPrice"].GetNumberValue(); got != 0.97 {
		t.Errorf("ptPrice = %v, want 0.97", got)
	}
	if got := fields["ytPrice"].GetNumberValue(); got != 0.03 {
		t.Errorf("ytPrice = %v, want 0.03", got)
	}
	if got := fields["volume24h"].GetNumberValue(); got != 1200000 {
		t.Errorf("volume24h = %v, want 1200000", got)
	}
}

func TestGetMarketDataRequiresChainID(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetMarketData(context.Background(), mustStruct(t, map[string]any{
		"address": "0x27b1dacd74688af24a64bd3c9c1b143118740784",
	}))
	if err == nil {
		t.Fatal("expected error for missing chain_id")
	}
	if !strings.Contains(err.Error(), "chain_id is required") {
		t.Errorf("error = %q, want to contain 'chain_id is required'", err.Error())
	}
}

func TestGetMarketDataRequiresAddress(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetMarketData(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing address")
	}
	if !strings.Contains(err.Error(), "address is required") {
		t.Errorf("error = %q, want to contain 'address is required'", err.Error())
	}
}

func TestGetPrices(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPrices(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetPrices: %v", err)
	}

	fields := resp.GetFields()
	prices := fields["prices"]
	if prices == nil {
		t.Fatal("response has no 'prices' field")
	}

	priceMap := prices.GetStructValue().GetFields()
	if len(priceMap) != 4 {
		t.Fatalf("expected 4 prices, got %d", len(priceMap))
	}

	if got := priceMap["0xpt1111"].GetNumberValue(); got != 2425.25 {
		t.Errorf("PT price = %v, want 2425.25", got)
	}
	if got := priceMap["0xyt1111"].GetNumberValue(); got != 75.25 {
		t.Errorf("YT price = %v, want 75.25", got)
	}
}

func TestGetPricesWithChainFilter(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPrices(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
	}))
	if err != nil {
		t.Fatalf("GetPrices: %v", err)
	}

	prices := resp.GetFields()["prices"]
	if prices == nil {
		t.Fatal("response has no 'prices' field")
	}
}

func TestGetHistoricalData(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetHistoricalData(context.Background(), mustStruct(t, map[string]any{
		"chain_id":   float64(1),
		"address":    "0x27b1dacd74688af24a64bd3c9c1b143118740784",
		"time_range": "1m",
	}))
	if err != nil {
		t.Fatalf("GetHistoricalData: %v", err)
	}

	fields := resp.GetFields()
	results := fields["results"]
	if results == nil {
		t.Fatal("response has no 'results' field")
	}
	items := results.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 data points, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["timestamp"].GetStringValue(); got != "2024-01-01T00:00:00Z" {
		t.Errorf("timestamp = %q, want %q", got, "2024-01-01T00:00:00Z")
	}
	if got := first["tvl"].GetNumberValue(); got != 12000000 {
		t.Errorf("tvl = %v, want 12000000", got)
	}
	if got := first["impliedApy"].GetNumberValue(); got != 0.042 {
		t.Errorf("impliedApy = %v, want 0.042", got)
	}
}

func TestGetHistoricalDataRequiresChainID(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetHistoricalData(context.Background(), mustStruct(t, map[string]any{
		"address": "0x27b1dacd74688af24a64bd3c9c1b143118740784",
	}))
	if err == nil {
		t.Fatal("expected error for missing chain_id")
	}
}

func TestGetHistoricalDataRequiresAddress(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetHistoricalData(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing address")
	}
}

func TestGetSwapPrices(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetSwapPrices(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"market":   "0x27b1dacd74688af24a64bd3c9c1b143118740784",
	}))
	if err != nil {
		t.Fatalf("GetSwapPrices: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["ptPrice"].GetNumberValue(); got != 0.97 {
		t.Errorf("ptPrice = %v, want 0.97", got)
	}
	if got := fields["ytPrice"].GetNumberValue(); got != 0.03 {
		t.Errorf("ytPrice = %v, want 0.03", got)
	}
	if got := fields["market"].GetStringValue(); got != "0x27b1dacd74688af24a64bd3c9c1b143118740784" {
		t.Errorf("market = %q", got)
	}
	if got := fields["chainId"].GetNumberValue(); got != 1 {
		t.Errorf("chainId = %v, want 1", got)
	}
}

func TestGetSwapPricesRequiresChainID(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSwapPrices(context.Background(), mustStruct(t, map[string]any{
		"market": "0x27b1dacd74688af24a64bd3c9c1b143118740784",
	}))
	if err == nil {
		t.Fatal("expected error for missing chain_id")
	}
}

func TestGetSwapPricesRequiresMarket(t *testing.T) {
	ts := mockPendleServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSwapPrices(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing market")
	}
}

// --- Live integration tests (hit the real Pendle API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("PENDLE_RUN_LIVE_TESTS") == "" {
		t.Skip("set PENDLE_RUN_LIVE_TESTS=1 to run live integration tests (hits real Pendle API)")
	}
}

func liveService() *PendleService {
	return NewPendleService()
}

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	// The response should have results or a list of markets.
	if len(fields) == 0 {
		t.Fatal("empty response from ListMarkets")
	}
	t.Logf("ListMarkets response keys: %v", keysOf(fields))
}

func TestLiveListMarketsWithChain(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"limit":    float64(3),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListMarkets with chain filter")
	}
}

func TestLiveGetPrices(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetPrices(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
	}))
	if err != nil {
		t.Fatalf("GetPrices: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPrices")
	}
	t.Logf("GetPrices response keys: %v", keysOf(fields))
}

func TestLiveGetMarketData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// First get a market address from ListMarkets.
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"limit":    float64(1),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	// Extract the first market address dynamically.
	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" {
		t.Skip("no Ethereum markets found to test GetMarketData")
	}

	resp, err := svc.GetMarketData(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(chainID),
		"address":  marketAddr,
	}))
	if err != nil {
		t.Fatalf("GetMarketData: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetMarketData")
	}
	t.Logf("GetMarketData response keys: %v", keysOf(fields))
}

func TestLiveGetHistoricalData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// First get a market address from ListMarkets.
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"limit":    float64(1),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" {
		t.Skip("no Ethereum markets found to test GetHistoricalData")
	}

	resp, err := svc.GetHistoricalData(context.Background(), mustStruct(t, map[string]any{
		"chain_id":   float64(chainID),
		"address":    marketAddr,
		"time_range": "1w",
	}))
	if err != nil {
		t.Fatalf("GetHistoricalData: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetHistoricalData")
	}
	t.Logf("GetHistoricalData response keys: %v", keysOf(fields))
}

func TestLiveGetSwapPrices(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// First get a market address from ListMarkets.
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(1),
		"limit":    float64(1),
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" {
		t.Skip("no Ethereum markets found to test GetSwapPrices")
	}

	resp, err := svc.GetSwapPrices(context.Background(), mustStruct(t, map[string]any{
		"chain_id": float64(chainID),
		"market":   marketAddr,
	}))
	if err != nil {
		// Swap prices endpoint may not be available for all markets.
		t.Logf("GetSwapPrices returned error (may be expected): %v", err)
		return
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetSwapPrices")
	}
	t.Logf("GetSwapPrices response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

func extractFirstMarket(t *testing.T, resp *structpb.Struct) (string, int64) {
	t.Helper()
	fields := resp.GetFields()

	// Try "results" key first (paginated response).
	if results, ok := fields["results"]; ok {
		items := results.GetListValue().GetValues()
		if len(items) > 0 {
			m := items[0].GetStructValue().GetFields()
			addr := m["address"].GetStringValue()
			chainID := int64(m["chainId"].GetNumberValue())
			return addr, chainID
		}
	}

	// Try direct array under "items".
	if items, ok := fields["items"]; ok {
		vals := items.GetListValue().GetValues()
		if len(vals) > 0 {
			m := vals[0].GetStructValue().GetFields()
			addr := m["address"].GetStringValue()
			chainID := int64(m["chainId"].GetNumberValue())
			return addr, chainID
		}
	}

	return "", 0
}

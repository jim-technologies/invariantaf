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

// mockRaydiumServer creates a test server that returns realistic Raydium API responses.
func mockRaydiumServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/pools/info/ids"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": []any{
					map[string]any{
						"id":         "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
						"type":       "Standard",
						"mintA":      map[string]any{"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
						"mintB":      map[string]any{"address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "symbol": "USDC"},
						"tvl":        float64(25000000),
						"day":        map[string]any{"volume": float64(5000000), "fee": float64(15000), "apr": float64(21.5)},
						"lpMint":     map[string]any{"address": "8HoQnePLqPj4M7PUDzfw8e3Ymdaf91fLXebQoN1iV2GR"},
						"lpPrice":    float64(12.5),
						"farmUpcoming": float64(0),
						"farmOngoing":  float64(1),
					},
				},
			})

		case strings.Contains(r.URL.Path, "/pools/info/mint"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": map[string]any{
					"count": float64(2),
					"data": []any{
						map[string]any{
							"id":    "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
							"type":  "Standard",
							"mintA": map[string]any{"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
							"mintB": map[string]any{"address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "symbol": "USDC"},
							"tvl":   float64(25000000),
							"day":   map[string]any{"volume": float64(5000000), "fee": float64(15000), "apr": float64(21.5)},
						},
						map[string]any{
							"id":    "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX",
							"type":  "Concentrated",
							"mintA": map[string]any{"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
							"mintB": map[string]any{"address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "symbol": "USDT"},
							"tvl":   float64(18000000),
							"day":   map[string]any{"volume": float64(3000000), "fee": float64(9000), "apr": float64(18.2)},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/pools/info/list"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": map[string]any{
					"count": float64(100),
					"data": []any{
						map[string]any{
							"id":    "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
							"type":  "Standard",
							"mintA": map[string]any{"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
							"mintB": map[string]any{"address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "symbol": "USDC"},
							"tvl":   float64(25000000),
							"day":   map[string]any{"volume": float64(5000000), "fee": float64(15000), "apr": float64(21.5)},
						},
						map[string]any{
							"id":    "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX",
							"type":  "Concentrated",
							"mintA": map[string]any{"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
							"mintB": map[string]any{"address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "symbol": "USDT"},
							"tvl":   float64(18000000),
							"day":   map[string]any{"volume": float64(3000000), "fee": float64(9000), "apr": float64(18.2)},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/farm/info/ids"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": []any{
					map[string]any{
						"id":       "CHYrUBX2RKX8iBg7gYTUYzaHqW7E1BQQSE5erWrh2Dnk",
						"lpMint":   "8HoQnePLqPj4M7PUDzfw8e3Ymdaf91fLXebQoN1iV2GR",
						"tvl":      float64(12000000),
						"apr":      float64(35.5),
						"rewardInfos": []any{
							map[string]any{
								"mint":   map[string]any{"address": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", "symbol": "RAY"},
								"apr":    float64(25.0),
								"status": "ongoing",
							},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/farm/info/list"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": map[string]any{
					"count": float64(50),
					"data": []any{
						map[string]any{
							"id":     "CHYrUBX2RKX8iBg7gYTUYzaHqW7E1BQQSE5erWrh2Dnk",
							"lpMint": "8HoQnePLqPj4M7PUDzfw8e3Ymdaf91fLXebQoN1iV2GR",
							"tvl":    float64(12000000),
							"apr":    float64(35.5),
						},
						map[string]any{
							"id":     "FarmABC123456789abcdefghijklmnopqrstuvwxyz",
							"lpMint": "MintABC123456789abcdefghijklmnopqrstuvwxyz",
							"tvl":    float64(8000000),
							"apr":    float64(22.0),
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/mint/price"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":      "some-request-id",
				"success": true,
				"data": map[string]any{
					"So11111111111111111111111111111111111111112":  float64(178.50),
					"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": float64(1.0),
					"4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R":  float64(2.35),
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *RaydiumService {
	return &RaydiumService{
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

func TestGetPoolInfo(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPoolInfo(context.Background(), mustStruct(t, map[string]any{
		"pool_id": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
	}))
	if err != nil {
		t.Fatalf("GetPoolInfo: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
	if !fields["success"].GetBoolValue() {
		t.Fatal("response success is false")
	}
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 pool, got %d", len(items))
	}

	pool := items[0].GetStructValue().GetFields()
	if got := pool["id"].GetStringValue(); got != "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2" {
		t.Errorf("id = %q, want %q", got, "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2")
	}
	if got := pool["type"].GetStringValue(); got != "Standard" {
		t.Errorf("type = %q, want %q", got, "Standard")
	}
	if got := pool["tvl"].GetNumberValue(); got != 25000000 {
		t.Errorf("tvl = %v, want 25000000", got)
	}
}

func TestGetPoolInfoRequiresPoolID(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetPoolInfo(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing pool_id")
	}
	if !strings.Contains(err.Error(), "pool_id is required") {
		t.Errorf("error = %q, want to contain 'pool_id is required'", err.Error())
	}
}

func TestListPools(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListPools: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
	data := fields["data"].GetStructValue().GetFields()
	count := data["count"].GetNumberValue()
	if count != 100 {
		t.Errorf("count = %v, want 100", count)
	}
	items := data["data"].GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 pools, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["id"].GetStringValue(); got != "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2" {
		t.Errorf("id = %q", got)
	}
}

func TestListPoolsWithParams(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{
		"pool_type":       "standard",
		"pool_sort_field": "liquidity",
		"sort_type":       "asc",
		"page_size":       float64(5),
		"page":            float64(2),
	}))
	if err != nil {
		t.Fatalf("ListPools: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
}

func TestGetPoolByMints(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPoolByMints(context.Background(), mustStruct(t, map[string]any{
		"mint1": "So11111111111111111111111111111111111111112",
	}))
	if err != nil {
		t.Fatalf("GetPoolByMints: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
	data := fields["data"].GetStructValue().GetFields()
	count := data["count"].GetNumberValue()
	if count != 2 {
		t.Errorf("count = %v, want 2", count)
	}
	items := data["data"].GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 pools, got %d", len(items))
	}
}

func TestGetPoolByMintsRequiresMint1(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetPoolByMints(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing mint1")
	}
	if !strings.Contains(err.Error(), "mint1 is required") {
		t.Errorf("error = %q, want to contain 'mint1 is required'", err.Error())
	}
}

func TestGetFarmInfo(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFarmInfo(context.Background(), mustStruct(t, map[string]any{
		"farm_id": "CHYrUBX2RKX8iBg7gYTUYzaHqW7E1BQQSE5erWrh2Dnk",
	}))
	if err != nil {
		t.Fatalf("GetFarmInfo: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 farm, got %d", len(items))
	}

	farm := items[0].GetStructValue().GetFields()
	if got := farm["id"].GetStringValue(); got != "CHYrUBX2RKX8iBg7gYTUYzaHqW7E1BQQSE5erWrh2Dnk" {
		t.Errorf("id = %q", got)
	}
	if got := farm["tvl"].GetNumberValue(); got != 12000000 {
		t.Errorf("tvl = %v, want 12000000", got)
	}
	if got := farm["apr"].GetNumberValue(); got != 35.5 {
		t.Errorf("apr = %v, want 35.5", got)
	}
}

func TestGetFarmInfoRequiresFarmID(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetFarmInfo(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing farm_id")
	}
	if !strings.Contains(err.Error(), "farm_id is required") {
		t.Errorf("error = %q, want to contain 'farm_id is required'", err.Error())
	}
}

func TestListFarms(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListFarms(context.Background(), mustStruct(t, map[string]any{})	)
	if err != nil {
		t.Fatalf("ListFarms: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
	data := fields["data"].GetStructValue().GetFields()
	count := data["count"].GetNumberValue()
	if count != 50 {
		t.Errorf("count = %v, want 50", count)
	}
	items := data["data"].GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 farms, got %d", len(items))
	}
}

func TestListFarmsWithPagination(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListFarms(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
		"page":      float64(2),
	}))
	if err != nil {
		t.Fatalf("ListFarms: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil {
		t.Fatal("response has no 'success' field")
	}
}

func TestGetTokenPrice(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{
		"mints": "So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
	}))
	if err != nil {
		t.Fatalf("GetTokenPrice: %v", err)
	}

	fields := resp.GetFields()
	prices := fields["prices"]
	if prices == nil {
		t.Fatal("response has no 'prices' field")
	}

	priceMap := prices.GetStructValue().GetFields()
	if len(priceMap) != 3 {
		t.Fatalf("expected 3 prices, got %d", len(priceMap))
	}

	if got := priceMap["So11111111111111111111111111111111111111112"].GetNumberValue(); got != 178.50 {
		t.Errorf("SOL price = %v, want 178.50", got)
	}
	if got := priceMap["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"].GetNumberValue(); got != 1.0 {
		t.Errorf("USDC price = %v, want 1.0", got)
	}
	if got := priceMap["4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R"].GetNumberValue(); got != 2.35 {
		t.Errorf("RAY price = %v, want 2.35", got)
	}
}

func TestGetTokenPriceRequiresMints(t *testing.T) {
	ts := mockRaydiumServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing mints")
	}
	if !strings.Contains(err.Error(), "mints is required") {
		t.Errorf("error = %q, want to contain 'mints is required'", err.Error())
	}
}

// --- Live integration tests (hit the real Raydium API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("RAYDIUM_RUN_LIVE_TESTS") == "" {
		t.Skip("set RAYDIUM_RUN_LIVE_TESTS=1 to run live integration tests (hits real Raydium API)")
	}
}

func liveService() *RaydiumService {
	return NewRaydiumService()
}

func TestLiveListPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{
		"page_size":       float64(3),
		"pool_sort_field": "default",
	}))
	if err != nil {
		if strings.Contains(err.Error(), "500") || strings.Contains(err.Error(), "400") {
			t.Skipf("ListPools API error: %v", err)
		}
		t.Fatalf("ListPools: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListPools")
	}
	t.Logf("ListPools response keys: %v", keysOf(fields))
}

func TestLiveGetPoolByMints(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// SOL mint address
	resp, err := svc.GetPoolByMints(context.Background(), mustStruct(t, map[string]any{
		"mint1":     "So11111111111111111111111111111111111111112",
		"page_size": float64(3),
	}))
	if err != nil {
		t.Fatalf("GetPoolByMints: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPoolByMints")
	}
	t.Logf("GetPoolByMints response keys: %v", keysOf(fields))
}

func TestLiveGetTokenPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// SOL mint
	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{
		"mints": "So11111111111111111111111111111111111111112",
	}))
	if err != nil {
		t.Fatalf("GetTokenPrice: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTokenPrice")
	}
	t.Logf("GetTokenPrice response keys: %v", keysOf(fields))
}

func TestLiveListFarms(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListFarms(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(3),
	}))
	if err != nil {
		if strings.Contains(err.Error(), "404") {
			t.Skip("ListFarms endpoint not available (404)")
		}
		t.Fatalf("ListFarms: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListFarms")
	}
	t.Logf("ListFarms response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

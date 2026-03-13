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

// mockCryptoSignalServer creates a test server that returns realistic API responses.
func mockCryptoSignalServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/fng"):
			json.NewEncoder(w).Encode(map[string]any{
				"name":     "Fear and Greed Index",
				"metadata": map[string]any{"error": nil},
				"data": []any{
					map[string]any{
						"value":                "72",
						"value_classification": "Greed",
						"timestamp":            "1710288000",
						"time_until_update":    "23 hours",
					},
					map[string]any{
						"value":                "68",
						"value_classification": "Greed",
						"timestamp":            "1710201600",
						"time_until_update":    "",
					},
					map[string]any{
						"value":                "45",
						"value_classification": "Neutral",
						"timestamp":            "1710115200",
						"time_until_update":    "",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/global"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": map[string]any{
					"active_cryptocurrencies":            float64(14532),
					"total_market_cap":                   map[string]any{"usd": 2.65e12},
					"total_volume":                       map[string]any{"usd": 98.5e9},
					"market_cap_percentage":              map[string]any{"btc": 52.3, "eth": 17.8},
					"market_cap_change_percentage_24h_usd": -1.25,
				},
			})

		case strings.Contains(r.URL.Path, "/search/trending"):
			json.NewEncoder(w).Encode(map[string]any{
				"coins": []any{
					map[string]any{
						"item": map[string]any{
							"id":              "bitcoin",
							"name":            "Bitcoin",
							"symbol":          "BTC",
							"market_cap_rank": float64(1),
							"thumb":           "https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png",
							"price_btc":       float64(1.0),
							"score":           float64(0),
						},
					},
					map[string]any{
						"item": map[string]any{
							"id":              "ethereum",
							"name":            "Ethereum",
							"symbol":          "ETH",
							"market_cap_rank": float64(2),
							"thumb":           "https://assets.coingecko.com/coins/images/279/thumb/ethereum.png",
							"price_btc":       0.053,
							"score":           float64(1),
						},
					},
					map[string]any{
						"item": map[string]any{
							"id":              "solana",
							"name":            "Solana",
							"symbol":          "SOL",
							"market_cap_rank": float64(5),
							"thumb":           "https://assets.coingecko.com/coins/images/4128/thumb/solana.png",
							"price_btc":       0.0025,
							"score":           float64(2),
						},
					},
				},
			})

		case strings.Contains(r.URL.RawQuery, "gastracker"):
			json.NewEncoder(w).Encode(map[string]any{
				"status":  "1",
				"message": "OK",
				"result": map[string]any{
					"SafeGasPrice":    "15",
					"ProposeGasPrice": "20",
					"FastGasPrice":    "25",
					"suggestBaseFee":  "14.5",
					"gasUsedRatio":    "0.45,0.52,0.38,0.61,0.49",
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

func newTestService(serverURL string) *CryptoSignalService {
	return &CryptoSignalService{
		fngBaseURL:       serverURL,
		coingeckoBaseURL: serverURL,
		etherscanBaseURL: serverURL,
		client:           &http.Client{},
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

func TestGetFearGreedIndex(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetFearGreedIndex: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 entries, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["value"].GetStringValue(); got != "72" {
		t.Errorf("value = %q, want %q", got, "72")
	}
	if got := first["value_classification"].GetStringValue(); got != "Greed" {
		t.Errorf("value_classification = %q, want %q", got, "Greed")
	}
	if got := first["timestamp"].GetStringValue(); got != "1710288000" {
		t.Errorf("timestamp = %q, want %q", got, "1710288000")
	}

	name := fields["name"]
	if name == nil || name.GetStringValue() != "Fear and Greed Index" {
		t.Errorf("name = %v, want 'Fear and Greed Index'", name)
	}
}

func TestGetFearGreedIndexWithLimit(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetFearGreedIndex: %v", err)
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 entry")
	}
}

func TestGetFearGreedIndexClampsLimit(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	// Should not error even with a large limit (gets clamped to 30).
	_, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(100),
	}))
	if err != nil {
		t.Fatalf("GetFearGreedIndex: %v", err)
	}
}

func TestGetGlobalMetrics(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetGlobalMetrics(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetGlobalMetrics: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}

	dataFields := data.GetStructValue().GetFields()
	if got := dataFields["active_cryptocurrencies"].GetNumberValue(); got != 14532 {
		t.Errorf("active_cryptocurrencies = %v, want 14532", got)
	}

	mcap := dataFields["total_market_cap"].GetStructValue().GetFields()
	if got := mcap["usd"].GetNumberValue(); got != 2.65e12 {
		t.Errorf("total_market_cap.usd = %v, want 2.65e12", got)
	}

	pct := dataFields["market_cap_percentage"].GetStructValue().GetFields()
	if got := pct["btc"].GetNumberValue(); got != 52.3 {
		t.Errorf("btc dominance = %v, want 52.3", got)
	}
	if got := pct["eth"].GetNumberValue(); got != 17.8 {
		t.Errorf("eth dominance = %v, want 17.8", got)
	}

	if got := dataFields["market_cap_change_percentage_24h_usd"].GetNumberValue(); got != -1.25 {
		t.Errorf("market_cap_change_percentage_24h_usd = %v, want -1.25", got)
	}
}

func TestGetTrendingCoins(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTrendingCoins(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTrendingCoins: %v", err)
	}

	fields := resp.GetFields()
	coins := fields["coins"]
	if coins == nil {
		t.Fatal("response has no 'coins' field")
	}
	items := coins.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 trending coins, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	item := first["item"].GetStructValue().GetFields()
	if got := item["id"].GetStringValue(); got != "bitcoin" {
		t.Errorf("id = %q, want %q", got, "bitcoin")
	}
	if got := item["name"].GetStringValue(); got != "Bitcoin" {
		t.Errorf("name = %q, want %q", got, "Bitcoin")
	}
	if got := item["symbol"].GetStringValue(); got != "BTC" {
		t.Errorf("symbol = %q, want %q", got, "BTC")
	}
	if got := item["market_cap_rank"].GetNumberValue(); got != 1 {
		t.Errorf("market_cap_rank = %v, want 1", got)
	}
	if got := item["price_btc"].GetNumberValue(); got != 1.0 {
		t.Errorf("price_btc = %v, want 1.0", got)
	}

	// Check second coin
	second := items[1].GetStructValue().GetFields()
	item2 := second["item"].GetStructValue().GetFields()
	if got := item2["symbol"].GetStringValue(); got != "ETH" {
		t.Errorf("symbol = %q, want %q", got, "ETH")
	}
}

func TestGetGasPrice(t *testing.T) {
	ts := mockCryptoSignalServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetGasPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetGasPrice: %v", err)
	}

	fields := resp.GetFields()
	result := fields["result"]
	if result == nil {
		t.Fatal("response has no 'result' field")
	}

	resultFields := result.GetStructValue().GetFields()
	if got := resultFields["SafeGasPrice"].GetStringValue(); got != "15" {
		t.Errorf("SafeGasPrice = %q, want %q", got, "15")
	}
	if got := resultFields["ProposeGasPrice"].GetStringValue(); got != "20" {
		t.Errorf("ProposeGasPrice = %q, want %q", got, "20")
	}
	if got := resultFields["FastGasPrice"].GetStringValue(); got != "25" {
		t.Errorf("FastGasPrice = %q, want %q", got, "25")
	}
	if got := resultFields["suggestBaseFee"].GetStringValue(); got != "14.5" {
		t.Errorf("suggestBaseFee = %q, want %q", got, "14.5")
	}
	if got := resultFields["gasUsedRatio"].GetStringValue(); got != "0.45,0.52,0.38,0.61,0.49" {
		t.Errorf("gasUsedRatio = %q, want %q", got, "0.45,0.52,0.38,0.61,0.49")
	}

	if got := fields["status"].GetStringValue(); got != "1" {
		t.Errorf("status = %q, want %q", got, "1")
	}
	if got := fields["message"].GetStringValue(); got != "OK" {
		t.Errorf("message = %q, want %q", got, "OK")
	}
}

func TestGetGasPriceServerError(t *testing.T) {
	// Server that returns 500.
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"error": "internal server error"}`))
	}))
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetGasPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for server error response")
	}
	if !strings.Contains(err.Error(), "API error") {
		t.Errorf("error = %q, want to contain 'API error'", err.Error())
	}
}

// --- Live integration tests (hit the real APIs) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("CRYPTOSIGNAL_RUN_LIVE_TESTS") == "" {
		t.Skip("set CRYPTOSIGNAL_RUN_LIVE_TESTS=1 to run live integration tests (hits real APIs)")
	}
}

func liveService() *CryptoSignalService {
	return NewCryptoSignalService()
}

func TestLiveGetFearGreedIndex(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetFearGreedIndex: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFearGreedIndex")
	}
	t.Logf("GetFearGreedIndex response keys: %v", keysOf(fields))
}

func TestLiveGetGlobalMetrics(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetGlobalMetrics(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetGlobalMetrics: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetGlobalMetrics")
	}
	t.Logf("GetGlobalMetrics response keys: %v", keysOf(fields))
}

func TestLiveGetTrendingCoins(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTrendingCoins(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTrendingCoins: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTrendingCoins")
	}
	t.Logf("GetTrendingCoins response keys: %v", keysOf(fields))
}

func TestLiveGetGasPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetGasPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetGasPrice: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetGasPrice")
	}
	t.Logf("GetGasPrice response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

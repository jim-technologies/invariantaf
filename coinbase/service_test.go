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

// mockCoinbaseServer creates a test server that returns realistic Coinbase API responses.
func mockCoinbaseServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/products" && r.Method == "GET":
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"id":              "BTC-USD",
					"base_currency":   "BTC",
					"quote_currency":  "USD",
					"base_min_size":   "0.00000001",
					"base_max_size":   "280",
					"base_increment":  "0.00000001",
					"quote_increment": "0.01",
					"display_name":    "BTC/USD",
					"status":          "online",
				},
				map[string]any{
					"id":              "ETH-USD",
					"base_currency":   "ETH",
					"quote_currency":  "USD",
					"base_min_size":   "0.00022",
					"base_max_size":   "4600",
					"base_increment":  "0.00000001",
					"quote_increment": "0.01",
					"display_name":    "ETH/USD",
					"status":          "online",
				},
			})

		case strings.HasSuffix(r.URL.Path, "/ticker"):
			json.NewEncoder(w).Encode(map[string]any{
				"trade_id": float64(123456789),
				"price":    "67234.56",
				"size":     "0.01234567",
				"bid":      "67234.55",
				"ask":      "67234.57",
				"volume":   "12345.67890123",
				"time":     "2024-01-15T10:30:00.000000Z",
			})

		case strings.HasSuffix(r.URL.Path, "/book"):
			json.NewEncoder(w).Encode(map[string]any{
				"sequence": float64(987654321),
				"bids": []any{
					[]any{"67234.55", "1.5", float64(3)},
					[]any{"67234.50", "2.1", float64(5)},
				},
				"asks": []any{
					[]any{"67234.57", "0.8", float64(2)},
					[]any{"67234.60", "1.2", float64(4)},
				},
			})

		case strings.HasSuffix(r.URL.Path, "/candles"):
			json.NewEncoder(w).Encode([]any{
				[]any{float64(1705315200), float64(67000.0), float64(67500.0), float64(67100.0), float64(67234.56), float64(150.5)},
				[]any{float64(1705311600), float64(66800.0), float64(67200.0), float64(66900.0), float64(67100.0), float64(200.3)},
			})

		case strings.HasSuffix(r.URL.Path, "/trades"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"time":     "2024-01-15T10:30:00.000000Z",
					"trade_id": float64(123456789),
					"price":    "67234.56",
					"size":     "0.01234567",
					"side":     "buy",
				},
				map[string]any{
					"time":     "2024-01-15T10:29:59.000000Z",
					"trade_id": float64(123456788),
					"price":    "67234.50",
					"size":     "0.05000000",
					"side":     "sell",
				},
			})

		case strings.HasSuffix(r.URL.Path, "/stats"):
			json.NewEncoder(w).Encode(map[string]any{
				"open":        "66500.00",
				"high":        "67800.00",
				"low":         "66200.00",
				"last":        "67234.56",
				"volume":      "12345.67890123",
				"volume_30day": "456789.12345678",
			})

		case strings.HasPrefix(r.URL.Path, "/products/"):
			// Single product: GET /products/{product_id}
			json.NewEncoder(w).Encode(map[string]any{
				"id":              "BTC-USD",
				"base_currency":   "BTC",
				"quote_currency":  "USD",
				"base_min_size":   "0.00000001",
				"base_max_size":   "280",
				"base_increment":  "0.00000001",
				"quote_increment": "0.01",
				"display_name":    "BTC/USD",
				"status":          "online",
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"message": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *CoinbaseService {
	return &CoinbaseService{
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

func TestListProducts(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListProducts(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListProducts: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	vals := items.GetListValue().GetValues()
	if len(vals) != 2 {
		t.Fatalf("expected 2 products, got %d", len(vals))
	}

	first := vals[0].GetStructValue().GetFields()
	if got := first["id"].GetStringValue(); got != "BTC-USD" {
		t.Errorf("id = %q, want %q", got, "BTC-USD")
	}
	if got := first["base_currency"].GetStringValue(); got != "BTC" {
		t.Errorf("base_currency = %q, want %q", got, "BTC")
	}
	if got := first["status"].GetStringValue(); got != "online" {
		t.Errorf("status = %q, want %q", got, "online")
	}
}

func TestGetProduct(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProduct(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProduct: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["id"].GetStringValue(); got != "BTC-USD" {
		t.Errorf("id = %q, want %q", got, "BTC-USD")
	}
	if got := fields["base_currency"].GetStringValue(); got != "BTC" {
		t.Errorf("base_currency = %q, want %q", got, "BTC")
	}
	if got := fields["quote_currency"].GetStringValue(); got != "USD" {
		t.Errorf("quote_currency = %q, want %q", got, "USD")
	}
	if got := fields["display_name"].GetStringValue(); got != "BTC/USD" {
		t.Errorf("display_name = %q, want %q", got, "BTC/USD")
	}
}

func TestGetProductRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProduct(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

func TestGetProductTicker(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProductTicker(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductTicker: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["price"].GetStringValue(); got != "67234.56" {
		t.Errorf("price = %q, want %q", got, "67234.56")
	}
	if got := fields["bid"].GetStringValue(); got != "67234.55" {
		t.Errorf("bid = %q, want %q", got, "67234.55")
	}
	if got := fields["ask"].GetStringValue(); got != "67234.57" {
		t.Errorf("ask = %q, want %q", got, "67234.57")
	}
	if got := fields["volume"].GetStringValue(); got != "12345.67890123" {
		t.Errorf("volume = %q, want %q", got, "12345.67890123")
	}
	if got := fields["trade_id"].GetNumberValue(); got != 123456789 {
		t.Errorf("trade_id = %v, want 123456789", got)
	}
}

func TestGetProductTickerRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProductTicker(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

func TestGetProductOrderbook(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProductOrderbook(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["sequence"].GetNumberValue(); got != 987654321 {
		t.Errorf("sequence = %v, want 987654321", got)
	}

	bids := fields["bids"].GetListValue().GetValues()
	if len(bids) != 2 {
		t.Fatalf("expected 2 bids, got %d", len(bids))
	}

	asks := fields["asks"].GetListValue().GetValues()
	if len(asks) != 2 {
		t.Fatalf("expected 2 asks, got %d", len(asks))
	}
}

func TestGetProductOrderbookRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProductOrderbook(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

func TestGetProductCandles(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProductCandles(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductCandles: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	vals := items.GetListValue().GetValues()
	if len(vals) != 2 {
		t.Fatalf("expected 2 candles, got %d", len(vals))
	}
}

func TestGetProductCandlesRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProductCandles(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

func TestGetProductTrades(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProductTrades(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductTrades: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	vals := items.GetListValue().GetValues()
	if len(vals) != 2 {
		t.Fatalf("expected 2 trades, got %d", len(vals))
	}

	first := vals[0].GetStructValue().GetFields()
	if got := first["price"].GetStringValue(); got != "67234.56" {
		t.Errorf("price = %q, want %q", got, "67234.56")
	}
	if got := first["side"].GetStringValue(); got != "buy" {
		t.Errorf("side = %q, want %q", got, "buy")
	}
	if got := first["trade_id"].GetNumberValue(); got != 123456789 {
		t.Errorf("trade_id = %v, want 123456789", got)
	}
}

func TestGetProductTradesRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProductTrades(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

func TestGetProductStats(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetProductStats(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductStats: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["open"].GetStringValue(); got != "66500.00" {
		t.Errorf("open = %q, want %q", got, "66500.00")
	}
	if got := fields["high"].GetStringValue(); got != "67800.00" {
		t.Errorf("high = %q, want %q", got, "67800.00")
	}
	if got := fields["low"].GetStringValue(); got != "66200.00" {
		t.Errorf("low = %q, want %q", got, "66200.00")
	}
	if got := fields["last"].GetStringValue(); got != "67234.56" {
		t.Errorf("last = %q, want %q", got, "67234.56")
	}
	if got := fields["volume"].GetStringValue(); got != "12345.67890123" {
		t.Errorf("volume = %q, want %q", got, "12345.67890123")
	}
	if got := fields["volume_30day"].GetStringValue(); got != "456789.12345678" {
		t.Errorf("volume_30day = %q, want %q", got, "456789.12345678")
	}
}

func TestGetProductStatsRequiresProductID(t *testing.T) {
	ts := mockCoinbaseServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetProductStats(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing product_id")
	}
	if !strings.Contains(err.Error(), "product_id is required") {
		t.Errorf("error = %q, want to contain 'product_id is required'", err.Error())
	}
}

// --- Live integration tests (hit the real Coinbase API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("COINBASE_RUN_LIVE_TESTS") == "" {
		t.Skip("set COINBASE_RUN_LIVE_TESTS=1 to run live integration tests (hits real Coinbase API)")
	}
}

func liveService() *CoinbaseService {
	return NewCoinbaseService()
}

func TestLiveListProducts(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListProducts(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListProducts: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListProducts")
	}
	t.Logf("ListProducts response keys: %v", keysOf(fields))
}

func TestLiveGetProduct(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProduct(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProduct: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProduct")
	}
	t.Logf("GetProduct response keys: %v", keysOf(fields))
}

func TestLiveGetProductTicker(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProductTicker(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductTicker: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProductTicker")
	}
	t.Logf("GetProductTicker response keys: %v", keysOf(fields))
}

func TestLiveGetProductOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProductOrderbook(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProductOrderbook")
	}
	t.Logf("GetProductOrderbook response keys: %v", keysOf(fields))
}

func TestLiveGetProductCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProductCandles(context.Background(), mustStruct(t, map[string]any{
		"product_id":  "BTC-USD",
		"granularity": float64(3600),
	}))
	if err != nil {
		t.Fatalf("GetProductCandles: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProductCandles")
	}
	t.Logf("GetProductCandles response keys: %v", keysOf(fields))
}

func TestLiveGetProductTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProductTrades(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
		"limit":      float64(10),
	}))
	if err != nil {
		t.Fatalf("GetProductTrades: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProductTrades")
	}
	t.Logf("GetProductTrades response keys: %v", keysOf(fields))
}

func TestLiveGetProductStats(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetProductStats(context.Background(), mustStruct(t, map[string]any{
		"product_id": "BTC-USD",
	}))
	if err != nil {
		t.Fatalf("GetProductStats: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetProductStats")
	}
	t.Logf("GetProductStats response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

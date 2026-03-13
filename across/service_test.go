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

// mockAcrossServer creates a test server that returns realistic Across API responses.
func mockAcrossServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/suggested-fees"):
			json.NewEncoder(w).Encode(map[string]any{
				"totalRelayFee": map[string]any{
					"pct":    "50000000000000",
					"total":  "50000000000000",
				},
				"relayerCapitalFee": map[string]any{
					"pct":   "10000000000000",
					"total": "10000000000000",
				},
				"relayerGasFee": map[string]any{
					"pct":   "20000000000000",
					"total": "20000000000000",
				},
				"lpFee": map[string]any{
					"pct":   "20000000000000",
					"total": "20000000000000",
				},
				"timestamp":            "1700000000",
				"estimatedFillTimeSec": float64(120),
				"isAmountTooLow":       false,
			})

		case strings.Contains(r.URL.Path, "/available-routes"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"originChainId":          float64(1),
					"destinationChainId":     float64(10),
					"originToken":            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
					"destinationToken":       "0x4200000000000000000000000000000000000006",
					"originTokenSymbol":      "WETH",
					"destinationTokenSymbol": "WETH",
					"isEnabled":              true,
				},
				map[string]any{
					"originChainId":          float64(1),
					"destinationChainId":     float64(10),
					"originToken":            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
					"destinationToken":       "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
					"originTokenSymbol":      "USDC",
					"destinationTokenSymbol": "USDC.e",
					"isEnabled":              true,
				},
			})

		case strings.Contains(r.URL.Path, "/limits"):
			json.NewEncoder(w).Encode(map[string]any{
				"minDeposit":           "10000000000000000",
				"maxDeposit":           "1000000000000000000000",
				"maxDepositInstant":    "500000000000000000000",
				"maxDepositShortDelay": "750000000000000000000",
			})

		case strings.Contains(r.URL.Path, "/pools"):
			json.NewEncoder(w).Encode(map[string]any{
				"estimatedApy":       "0.05",
				"exchangeRateCurrent": 1.02,
				"totalPoolSize":      "50000000000000000000000",
				"liquidReserves":     "35000000000000000000000",
				"utilizationCurrent": 0.3,
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *AcrossService {
	return &AcrossService{
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

func TestGetSuggestedFees(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"amount":               "1000000000000000000",
		"origin_chain_id":      float64(1),
	}))
	if err != nil {
		t.Fatalf("GetSuggestedFees: %v", err)
	}

	fields := resp.GetFields()
	if fields["totalRelayFee"] == nil {
		t.Fatal("response has no 'totalRelayFee' field")
	}
	totalRelayFee := fields["totalRelayFee"].GetStructValue().GetFields()
	if got := totalRelayFee["pct"].GetStringValue(); got != "50000000000000" {
		t.Errorf("totalRelayFee.pct = %q, want %q", got, "50000000000000")
	}
	if got := fields["estimatedFillTimeSec"].GetNumberValue(); got != 120 {
		t.Errorf("estimatedFillTimeSec = %v, want 120", got)
	}
}

func TestGetSuggestedFeesRequiresToken(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"destination_chain_id": float64(10),
		"amount":               "1000000000000000000",
		"origin_chain_id":      float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing token")
	}
	if !strings.Contains(err.Error(), "token is required") {
		t.Errorf("error = %q, want to contain 'token is required'", err.Error())
	}
}

func TestGetSuggestedFeesRequiresDestinationChainID(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"token":           "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"amount":          "1000000000000000000",
		"origin_chain_id": float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing destination_chain_id")
	}
	if !strings.Contains(err.Error(), "destination_chain_id is required") {
		t.Errorf("error = %q, want to contain 'destination_chain_id is required'", err.Error())
	}
}

func TestGetSuggestedFeesRequiresAmount(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"origin_chain_id":      float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing amount")
	}
	if !strings.Contains(err.Error(), "amount is required") {
		t.Errorf("error = %q, want to contain 'amount is required'", err.Error())
	}
}

func TestGetSuggestedFeesRequiresOriginChainID(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"amount":               "1000000000000000000",
	}))
	if err == nil {
		t.Fatal("expected error for missing origin_chain_id")
	}
	if !strings.Contains(err.Error(), "origin_chain_id is required") {
		t.Errorf("error = %q, want to contain 'origin_chain_id is required'", err.Error())
	}
}

func TestGetAvailableRoutes(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetAvailableRoutes(context.Background(), mustStruct(t, map[string]any{
		"origin_chain_id":      float64(1),
		"destination_chain_id": float64(10),
	}))
	if err != nil {
		t.Fatalf("GetAvailableRoutes: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	routes := items.GetListValue().GetValues()
	if len(routes) != 2 {
		t.Fatalf("expected 2 routes, got %d", len(routes))
	}

	first := routes[0].GetStructValue().GetFields()
	if got := first["originChainId"].GetNumberValue(); got != 1 {
		t.Errorf("originChainId = %v, want 1", got)
	}
	if got := first["destinationChainId"].GetNumberValue(); got != 10 {
		t.Errorf("destinationChainId = %v, want 10", got)
	}
	if got := first["originTokenSymbol"].GetStringValue(); got != "WETH" {
		t.Errorf("originTokenSymbol = %q, want %q", got, "WETH")
	}
	if got := first["isEnabled"].GetBoolValue(); got != true {
		t.Errorf("isEnabled = %v, want true", got)
	}
}

func TestGetAvailableRoutesNoFilters(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetAvailableRoutes(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetAvailableRoutes: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	routes := items.GetListValue().GetValues()
	if len(routes) == 0 {
		t.Fatal("expected at least 1 route")
	}
}

func TestGetLimits(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetLimits(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"origin_chain_id":      float64(1),
	}))
	if err != nil {
		t.Fatalf("GetLimits: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["minDeposit"].GetStringValue(); got != "10000000000000000" {
		t.Errorf("minDeposit = %q, want %q", got, "10000000000000000")
	}
	if got := fields["maxDeposit"].GetStringValue(); got != "1000000000000000000000" {
		t.Errorf("maxDeposit = %q, want %q", got, "1000000000000000000000")
	}
	if got := fields["maxDepositInstant"].GetStringValue(); got != "500000000000000000000" {
		t.Errorf("maxDepositInstant = %q, want %q", got, "500000000000000000000")
	}
	if got := fields["maxDepositShortDelay"].GetStringValue(); got != "750000000000000000000" {
		t.Errorf("maxDepositShortDelay = %q, want %q", got, "750000000000000000000")
	}
}

func TestGetLimitsRequiresToken(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetLimits(context.Background(), mustStruct(t, map[string]any{
		"destination_chain_id": float64(10),
		"origin_chain_id":      float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing token")
	}
	if !strings.Contains(err.Error(), "token is required") {
		t.Errorf("error = %q, want to contain 'token is required'", err.Error())
	}
}

func TestGetLimitsRequiresDestinationChainID(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetLimits(context.Background(), mustStruct(t, map[string]any{
		"token":           "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"origin_chain_id": float64(1),
	}))
	if err == nil {
		t.Fatal("expected error for missing destination_chain_id")
	}
	if !strings.Contains(err.Error(), "destination_chain_id is required") {
		t.Errorf("error = %q, want to contain 'destination_chain_id is required'", err.Error())
	}
}

func TestGetLimitsRequiresOriginChainID(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetLimits(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
	}))
	if err == nil {
		t.Fatal("expected error for missing origin_chain_id")
	}
	if !strings.Contains(err.Error(), "origin_chain_id is required") {
		t.Errorf("error = %q, want to contain 'origin_chain_id is required'", err.Error())
	}
}

func TestGetPoolState(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPoolState(context.Background(), mustStruct(t, map[string]any{
		"token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
	}))
	if err != nil {
		t.Fatalf("GetPoolState: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["estimatedApy"].GetStringValue(); got != "0.05" {
		t.Errorf("estimatedApy = %q, want %q", got, "0.05")
	}
	if got := fields["exchangeRateCurrent"].GetNumberValue(); got != 1.02 {
		t.Errorf("exchangeRateCurrent = %v, want 1.02", got)
	}
	if got := fields["totalPoolSize"].GetStringValue(); got != "50000000000000000000000" {
		t.Errorf("totalPoolSize = %q, want %q", got, "50000000000000000000000")
	}
	if got := fields["liquidReserves"].GetStringValue(); got != "35000000000000000000000" {
		t.Errorf("liquidReserves = %q, want %q", got, "35000000000000000000000")
	}
	if got := fields["utilizationCurrent"].GetNumberValue(); got != 0.3 {
		t.Errorf("utilizationCurrent = %v, want 0.3", got)
	}
}

func TestGetPoolStateRequiresToken(t *testing.T) {
	ts := mockAcrossServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetPoolState(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing token")
	}
	if !strings.Contains(err.Error(), "token is required") {
		t.Errorf("error = %q, want to contain 'token is required'", err.Error())
	}
}

// --- Live integration tests (hit the real Across API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("ACROSS_RUN_LIVE_TESTS") == "" {
		t.Skip("set ACROSS_RUN_LIVE_TESTS=1 to run live integration tests (hits real Across API)")
	}
}

func liveService() *AcrossService {
	return NewAcrossService()
}

func TestLiveGetSuggestedFees(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetSuggestedFees(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"amount":               "1000000000000000000",
		"origin_chain_id":      float64(1),
	}))
	if err != nil {
		t.Fatalf("GetSuggestedFees: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetSuggestedFees")
	}
	t.Logf("GetSuggestedFees response keys: %v", keysOf(fields))
}

func TestLiveGetAvailableRoutes(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetAvailableRoutes(context.Background(), mustStruct(t, map[string]any{
		"origin_chain_id":      float64(1),
		"destination_chain_id": float64(10),
	}))
	if err != nil {
		t.Fatalf("GetAvailableRoutes: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetAvailableRoutes")
	}
	t.Logf("GetAvailableRoutes response keys: %v", keysOf(fields))
}

func TestLiveGetLimits(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetLimits(context.Background(), mustStruct(t, map[string]any{
		"token":                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
		"destination_chain_id": float64(10),
		"origin_chain_id":      float64(1),
	}))
	if err != nil {
		t.Fatalf("GetLimits: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetLimits")
	}
	t.Logf("GetLimits response keys: %v", keysOf(fields))
}

func TestLiveGetPoolState(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetPoolState(context.Background(), mustStruct(t, map[string]any{
		"token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
	}))
	if err != nil {
		t.Fatalf("GetPoolState: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPoolState")
	}
	t.Logf("GetPoolState response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

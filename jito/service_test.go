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

// mockJitoServer creates a test server that returns realistic Jito API responses.
func mockJitoServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Tip floor is a GET endpoint on a different path.
		if r.Method == "GET" && strings.Contains(r.URL.Path, "/tip_floor") {
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"time":                            "2024-01-15T12:00:00Z",
					"landed_tips_25th_percentile":     0.00001,
					"landed_tips_50th_percentile":     0.00001,
					"landed_tips_75th_percentile":     0.000011,
					"landed_tips_95th_percentile":     0.00005,
					"landed_tips_99th_percentile":     0.001,
					"ema_landed_tips_50th_percentile": 0.000012,
				},
			})
			return
		}

		// JSON-RPC POST endpoint for bundles.
		if r.Method == "POST" {
			var rpcReq struct {
				JSONRPC string `json:"jsonrpc"`
				ID      int64  `json:"id"`
				Method  string `json:"method"`
				Params  []any  `json:"params"`
			}
			if err := json.NewDecoder(r.Body).Decode(&rpcReq); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]any{
					"jsonrpc": "2.0",
					"id":      0,
					"error":   map[string]any{"code": -32700, "message": "Parse error"},
				})
				return
			}

			switch rpcReq.Method {
			case "sendBundle":
				json.NewEncoder(w).Encode(map[string]any{
					"jsonrpc": "2.0",
					"id":      rpcReq.ID,
					"result":  "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
				})

			case "getBundleStatuses":
				json.NewEncoder(w).Encode(map[string]any{
					"jsonrpc": "2.0",
					"id":      rpcReq.ID,
					"result": map[string]any{
						"context": map[string]any{"slot": float64(242806119)},
						"value": []any{
							map[string]any{
								"bundle_id":   "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
								"status":      "Landed",
								"landed_slot": float64(242806100),
							},
							map[string]any{
								"bundle_id": "deadbeef0000000000000000000000000000000000000000000000000000dead",
								"status":    "Failed",
								"error":     "Bundle simulation failed",
							},
						},
					},
				})

			default:
				json.NewEncoder(w).Encode(map[string]any{
					"jsonrpc": "2.0",
					"id":      rpcReq.ID,
					"error":   map[string]any{"code": -32601, "message": "Method not found"},
				})
			}
			return
		}

		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]any{"error": "not found"})
	}))
}

func newTestService(bundleURL, tipFloorURL string) *JitoService {
	return &JitoService{
		bundleURL:   bundleURL,
		tipFloorURL: tipFloorURL,
		client:      &http.Client{},
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

func TestSendBundle(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	resp, err := svc.SendBundle(context.Background(), mustStruct(t, map[string]any{
		"transactions": []any{
			"5KtPn1LGuxhFiwjxErkxTb7XQ1hVeHYGTnKPs8CcRH3mF1t7GramLHBkJkWpSfEkC5X",
			"3nGUvCWHmQBYBSxjfwNmqWCfNBn8eAkRGHPxFCsmNxYh7kHVgVdDkbczXxC6sdgv3E9",
		},
	}))
	if err != nil {
		t.Fatalf("SendBundle: %v", err)
	}

	fields := resp.GetFields()
	bundleID := fields["bundle_id"].GetStringValue()
	if bundleID == "" {
		t.Fatal("response has no 'bundle_id' field")
	}
	if bundleID != "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2" {
		t.Errorf("bundle_id = %q, want expected hash", bundleID)
	}
}

func TestSendBundleRequiresTransactions(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	_, err := svc.SendBundle(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing transactions")
	}
	if !strings.Contains(err.Error(), "transactions is required") {
		t.Errorf("error = %q, want to contain 'transactions is required'", err.Error())
	}
}

func TestSendBundleEmptyTransactions(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	_, err := svc.SendBundle(context.Background(), mustStruct(t, map[string]any{
		"transactions": []any{},
	}))
	if err == nil {
		t.Fatal("expected error for empty transactions list")
	}
}

func TestGetBundleStatuses(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	resp, err := svc.GetBundleStatuses(context.Background(), mustStruct(t, map[string]any{
		"bundle_ids": []any{
			"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
			"deadbeef0000000000000000000000000000000000000000000000000000dead",
		},
	}))
	if err != nil {
		t.Fatalf("GetBundleStatuses: %v", err)
	}

	fields := resp.GetFields()
	statuses := fields["statuses"]
	if statuses == nil {
		t.Fatal("response has no 'statuses' field")
	}

	items := statuses.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 statuses, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["status"].GetStringValue(); got != "Landed" {
		t.Errorf("first status = %q, want 'Landed'", got)
	}
	if got := first["landed_slot"].GetNumberValue(); got != 242806100 {
		t.Errorf("landed_slot = %v, want 242806100", got)
	}

	second := items[1].GetStructValue().GetFields()
	if got := second["status"].GetStringValue(); got != "Failed" {
		t.Errorf("second status = %q, want 'Failed'", got)
	}
	if got := second["error"].GetStringValue(); got != "Bundle simulation failed" {
		t.Errorf("error = %q, want 'Bundle simulation failed'", got)
	}
}

func TestGetBundleStatusesRequiresBundleIDs(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	_, err := svc.GetBundleStatuses(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing bundle_ids")
	}
	if !strings.Contains(err.Error(), "bundle_ids is required") {
		t.Errorf("error = %q, want to contain 'bundle_ids is required'", err.Error())
	}
}

func TestGetTipFloor(t *testing.T) {
	ts := mockJitoServer()
	defer ts.Close()
	svc := newTestService(ts.URL+"/api/v1/bundles", ts.URL+"/api/v1/bundles/tip_floor")

	resp, err := svc.GetTipFloor(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTipFloor: %v", err)
	}

	fields := resp.GetFields()
	entries := fields["entries"]
	if entries == nil {
		t.Fatal("response has no 'entries' field")
	}

	items := entries.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(items))
	}

	entry := items[0].GetStructValue().GetFields()
	if got := entry["time"].GetStringValue(); got != "2024-01-15T12:00:00Z" {
		t.Errorf("time = %q, want '2024-01-15T12:00:00Z'", got)
	}
	if got := entry["landed_tips_50th_percentile"].GetNumberValue(); got != 0.00001 {
		t.Errorf("landed_tips_50th_percentile = %v, want 0.00001", got)
	}
	if got := entry["landed_tips_25th_percentile"].GetNumberValue(); got != 0.00001 {
		t.Errorf("landed_tips_25th_percentile = %v, want 0.00001", got)
	}
	if got := entry["landed_tips_75th_percentile"].GetNumberValue(); got != 0.000011 {
		t.Errorf("landed_tips_75th_percentile = %v, want 0.000011", got)
	}
	if got := entry["landed_tips_95th_percentile"].GetNumberValue(); got != 0.00005 {
		t.Errorf("landed_tips_95th_percentile = %v, want 0.00005", got)
	}
	if got := entry["landed_tips_99th_percentile"].GetNumberValue(); got != 0.001 {
		t.Errorf("landed_tips_99th_percentile = %v, want 0.001", got)
	}
	if got := entry["ema_landed_tips_50th_percentile"].GetNumberValue(); got != 0.000012 {
		t.Errorf("ema_landed_tips_50th_percentile = %v, want 0.000012", got)
	}
}

// --- Live integration tests (hit the real Jito API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("JITO_RUN_LIVE_TESTS") == "" {
		t.Skip("set JITO_RUN_LIVE_TESTS=1 to run live integration tests (hits real Jito API)")
	}
}

func liveService() *JitoService {
	return NewJitoService()
}

func TestLiveGetTipFloor(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTipFloor(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTipFloor: %v", err)
	}

	fields := resp.GetFields()
	entries := fields["entries"]
	if entries == nil {
		t.Fatal("response has no 'entries' field")
	}

	items := entries.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 tip floor entry")
	}

	// Verify the first entry has expected fields.
	entry := items[0].GetStructValue().GetFields()
	if len(entry) == 0 {
		t.Fatal("tip floor entry is empty")
	}

	// The 50th percentile should be a positive number.
	p50 := entry["landed_tips_50th_percentile"].GetNumberValue()
	if p50 <= 0 {
		t.Errorf("landed_tips_50th_percentile = %v, want > 0", p50)
	}

	t.Logf("Tip floor entries: %d", len(items))
	t.Logf("50th percentile tip: %v SOL", p50)
	t.Logf("Entry keys: %v", keysOf(entry))
}

// --- helpers ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

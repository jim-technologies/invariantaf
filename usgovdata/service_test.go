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

// mockTreasuryServer creates a test server that returns realistic Treasury Fiscal Data API responses.
func mockTreasuryServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/v2/accounting/od/debt_to_penny"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"record_date":                  "2024-12-20",
						"tot_pub_debt_out_amt":          "36167364212079.59",
						"debt_held_public_amt":          "28908004857498.45",
						"intragov_hold_amt":             "7259359354581.14",
					},
					map[string]any{
						"record_date":                  "2024-12-19",
						"tot_pub_debt_out_amt":          "36150223891029.12",
						"debt_held_public_amt":          "28895004857498.45",
						"intragov_hold_amt":             "7255219033530.67",
					},
				},
				"meta": map[string]any{
					"count":       float64(2),
					"total-count": float64(9500),
					"total-pages": float64(950),
				},
			})

		case strings.Contains(r.URL.Path, "/v2/accounting/od/avg_interest_rates"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"record_date":      "2024-12-31",
						"security_type_desc": "Treasury Bills",
						"security_desc":    "Treasury Bills",
						"avg_interest_rate_amt": "5.123",
					},
					map[string]any{
						"record_date":      "2024-12-31",
						"security_type_desc": "Treasury Notes",
						"security_desc":    "Treasury Notes",
						"avg_interest_rate_amt": "2.876",
					},
					map[string]any{
						"record_date":      "2024-12-31",
						"security_type_desc": "Treasury Bonds",
						"security_desc":    "Treasury Bonds",
						"avg_interest_rate_amt": "3.456",
					},
				},
				"meta": map[string]any{
					"count":       float64(3),
					"total-count": float64(5000),
					"total-pages": float64(500),
				},
			})

		case strings.Contains(r.URL.Path, "/v1/accounting/od/securities_sales"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"record_date":    "2024-12-19",
						"security_type":  "Bill",
						"security_desc":  "4-Week Bill",
						"issue_date":     "2024-12-24",
						"maturity_date":  "2025-01-21",
					},
					map[string]any{
						"record_date":    "2024-12-18",
						"security_type":  "Note",
						"security_desc":  "5-Year Note",
						"issue_date":     "2024-12-31",
						"maturity_date":  "2029-12-31",
					},
				},
				"meta": map[string]any{
					"count":       float64(2),
					"total-count": float64(3000),
					"total-pages": float64(300),
				},
			})

		case strings.Contains(r.URL.Path, "/v1/accounting/od/rates_of_exchange"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"record_date":      "2024-12-31",
						"country":          "Japan",
						"currency":         "Yen",
						"exchange_rate":     "157.35",
					},
					map[string]any{
						"record_date":      "2024-12-31",
						"country":          "Euro Zone",
						"currency":         "Euro",
						"exchange_rate":     "0.962",
					},
					map[string]any{
						"record_date":      "2024-12-31",
						"country":          "United Kingdom",
						"currency":         "Pound",
						"exchange_rate":     "0.805",
					},
				},
				"meta": map[string]any{
					"count":       float64(3),
					"total-count": float64(8000),
					"total-pages": float64(800),
				},
			})

		case strings.Contains(r.URL.Path, "/v1/accounting/mts/mts_table_5"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"record_date":        "2024-11-30",
						"classification_desc": "National Defense",
						"current_month_gross_outly_amt": "67890",
						"current_fytd_gross_outly_amt":  "135780",
					},
					map[string]any{
						"record_date":        "2024-11-30",
						"classification_desc": "Social Security",
						"current_month_gross_outly_amt": "123456",
						"current_fytd_gross_outly_amt":  "246912",
					},
					map[string]any{
						"record_date":        "2024-11-30",
						"classification_desc": "Medicare",
						"current_month_gross_outly_amt": "89012",
						"current_fytd_gross_outly_amt":  "178024",
					},
				},
				"meta": map[string]any{
					"count":       float64(3),
					"total-count": float64(2000),
					"total-pages": float64(200),
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

func newTestService(serverURL string) *USGovDataService {
	return &USGovDataService{
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

func TestGetDebtToThePenny(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetDebtToThePenny(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetDebtToThePenny: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 debt records, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["record_date"].GetStringValue(); got != "2024-12-20" {
		t.Errorf("record_date = %q, want %q", got, "2024-12-20")
	}
	if got := first["tot_pub_debt_out_amt"].GetStringValue(); got != "36167364212079.59" {
		t.Errorf("tot_pub_debt_out_amt = %q, want %q", got, "36167364212079.59")
	}
	if got := first["debt_held_public_amt"].GetStringValue(); got != "28908004857498.45" {
		t.Errorf("debt_held_public_amt = %q, want %q", got, "28908004857498.45")
	}
	if got := first["intragov_hold_amt"].GetStringValue(); got != "7259359354581.14" {
		t.Errorf("intragov_hold_amt = %q, want %q", got, "7259359354581.14")
	}
}

func TestGetDebtToThePennyWithPageSize(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetDebtToThePenny(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetDebtToThePenny: %v", err)
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 debt record")
	}
}

func TestGetTreasuryYields(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTreasuryYields(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTreasuryYields: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 rate records, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["record_date"].GetStringValue(); got != "2024-12-31" {
		t.Errorf("record_date = %q, want %q", got, "2024-12-31")
	}
	if got := first["security_type_desc"].GetStringValue(); got != "Treasury Bills" {
		t.Errorf("security_type_desc = %q, want %q", got, "Treasury Bills")
	}
	if got := first["avg_interest_rate_amt"].GetStringValue(); got != "5.123" {
		t.Errorf("avg_interest_rate_amt = %q, want %q", got, "5.123")
	}
}

func TestGetTreasuryAuctions(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTreasuryAuctions(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTreasuryAuctions: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 auction records, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["record_date"].GetStringValue(); got != "2024-12-19" {
		t.Errorf("record_date = %q, want %q", got, "2024-12-19")
	}
	if got := first["security_type"].GetStringValue(); got != "Bill" {
		t.Errorf("security_type = %q, want %q", got, "Bill")
	}
	if got := first["security_desc"].GetStringValue(); got != "4-Week Bill" {
		t.Errorf("security_desc = %q, want %q", got, "4-Week Bill")
	}
	if got := first["issue_date"].GetStringValue(); got != "2024-12-24" {
		t.Errorf("issue_date = %q, want %q", got, "2024-12-24")
	}
	if got := first["maturity_date"].GetStringValue(); got != "2025-01-21" {
		t.Errorf("maturity_date = %q, want %q", got, "2025-01-21")
	}
}

func TestGetExchangeRates(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetExchangeRates(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetExchangeRates: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 exchange rate records, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["record_date"].GetStringValue(); got != "2024-12-31" {
		t.Errorf("record_date = %q, want %q", got, "2024-12-31")
	}
	if got := first["country"].GetStringValue(); got != "Japan" {
		t.Errorf("country = %q, want %q", got, "Japan")
	}
	if got := first["currency"].GetStringValue(); got != "Yen" {
		t.Errorf("currency = %q, want %q", got, "Yen")
	}
	if got := first["exchange_rate"].GetStringValue(); got != "157.35" {
		t.Errorf("exchange_rate = %q, want %q", got, "157.35")
	}
}

func TestGetFederalSpending(t *testing.T) {
	ts := mockTreasuryServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFederalSpending(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetFederalSpending: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 spending records, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["record_date"].GetStringValue(); got != "2024-11-30" {
		t.Errorf("record_date = %q, want %q", got, "2024-11-30")
	}
	if got := first["classification_desc"].GetStringValue(); got != "National Defense" {
		t.Errorf("classification_desc = %q, want %q", got, "National Defense")
	}
	if got := first["current_month_gross_outly_amt"].GetStringValue(); got != "67890" {
		t.Errorf("current_month_gross_outly_amt = %q, want %q", got, "67890")
	}
	if got := first["current_fytd_gross_outly_amt"].GetStringValue(); got != "135780" {
		t.Errorf("current_fytd_gross_outly_amt = %q, want %q", got, "135780")
	}
}

func TestGetDebtToThePennyAPIError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"error": "internal server error"}`))
	}))
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetDebtToThePenny(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for API error response")
	}
	if !strings.Contains(err.Error(), "API error") {
		t.Errorf("error = %q, want to contain 'API error'", err.Error())
	}
}

// --- Live integration tests (hit the real Treasury API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("USGOVDATA_RUN_LIVE_TESTS") == "" {
		t.Skip("set USGOVDATA_RUN_LIVE_TESTS=1 to run live integration tests (hits real Treasury API)")
	}
}

func liveService() *USGovDataService {
	return NewUSGovDataService()
}

func TestLiveGetDebtToThePenny(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetDebtToThePenny(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(3),
	}))
	if err != nil {
		t.Fatalf("GetDebtToThePenny: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetDebtToThePenny")
	}
	t.Logf("GetDebtToThePenny response keys: %v", keysOf(fields))
}

func TestLiveGetTreasuryYields(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTreasuryYields(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetTreasuryYields: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTreasuryYields")
	}
	t.Logf("GetTreasuryYields response keys: %v", keysOf(fields))
}

func TestLiveGetTreasuryAuctions(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTreasuryAuctions(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetTreasuryAuctions: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTreasuryAuctions")
	}
	t.Logf("GetTreasuryAuctions response keys: %v", keysOf(fields))
}

func TestLiveGetExchangeRates(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetExchangeRates(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetExchangeRates: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetExchangeRates")
	}
	t.Logf("GetExchangeRates response keys: %v", keysOf(fields))
}

func TestLiveGetFederalSpending(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFederalSpending(context.Background(), mustStruct(t, map[string]any{
		"page_size": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetFederalSpending: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFederalSpending")
	}
	t.Logf("GetFederalSpending response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

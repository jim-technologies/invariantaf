package main

import (
	"context"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

func skipUnlessIntegration(t *testing.T) {
	t.Helper()
	if os.Getenv("TEST_PREDICTFUN") == "" {
		t.Skip("set TEST_PREDICTFUN=1 to run integration tests (hits testnet API)")
	}
}

func testService() *PredictFunService {
	if os.Getenv("PREDICTFUN_BASE_URL") == "" {
		os.Setenv("PREDICTFUN_BASE_URL", "https://api-testnet.predict.fun")
	}
	return NewPredictFunService()
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

// --- Integration tests (hit the real testnet API) ---

func TestListMarkets(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	if got := resp.GetFields()["success"].GetBoolValue(); !got {
		t.Fatal("expected success = true")
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 market")
	}

	// Verify market structure
	first := items[0].GetStructValue().GetFields()
	if first["id"] == nil {
		t.Error("market missing 'id' field")
	}
	if first["title"].GetStringValue() == "" {
		t.Error("market has empty title")
	}
	if first["question"].GetStringValue() == "" {
		t.Error("market has empty question")
	}
	status := first["status"].GetStringValue()
	if status != "REGISTERED" && status != "RESOLVED" {
		t.Errorf("unexpected status %q", status)
	}
	tradingStatus := first["tradingStatus"].GetStringValue()
	if tradingStatus != "OPEN" && tradingStatus != "CLOSED" {
		t.Errorf("unexpected tradingStatus %q", tradingStatus)
	}
	outcomes := first["outcomes"].GetListValue().GetValues()
	if len(outcomes) < 2 {
		t.Errorf("expected at least 2 outcomes, got %d", len(outcomes))
	}
	for _, o := range outcomes {
		of := o.GetStructValue().GetFields()
		if of["name"].GetStringValue() == "" {
			t.Error("outcome missing name")
		}
		if of["onChainId"].GetStringValue() == "" {
			t.Error("outcome missing onChainId")
		}
	}

	// Pagination cursor should be present when there are more results
	if resp.GetFields()["cursor"].GetStringValue() == "" {
		t.Log("no cursor returned (may be last page)")
	}
}

func TestListMarketsPagination(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	// Fetch first page
	resp1, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets page 1: %v", err)
	}

	cursor := resp1.GetFields()["cursor"].GetStringValue()
	if cursor == "" {
		t.Skip("no second page available")
	}

	// Fetch second page with cursor - verify it succeeds and returns data
	resp2, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"cursor": cursor,
	}))
	if err != nil {
		t.Fatalf("ListMarkets page 2: %v", err)
	}

	if got := resp2.GetFields()["success"].GetBoolValue(); !got {
		t.Fatal("expected success = true on page 2")
	}

	page2Items := resp2.GetFields()["data"].GetListValue().GetValues()
	if len(page2Items) == 0 {
		t.Fatal("expected results on page 2")
	}
}

func TestListMarketsWithStatusFilter(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"status": "RESOLVED",
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	items := resp.GetFields()["data"].GetListValue().GetValues()
	for _, item := range items {
		got := item.GetStructValue().GetFields()["status"].GetStringValue()
		if got != "RESOLVED" {
			t.Errorf("expected status=RESOLVED, got %q", got)
		}
	}
}

func TestGetMarket(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	// First get a valid market ID from listing
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}
	items := listResp.GetFields()["data"].GetListValue().GetValues()
	if len(items) == 0 {
		t.Skip("no markets available on testnet")
	}
	marketID := items[0].GetStructValue().GetFields()["id"].GetNumberValue()

	// Now get that specific market
	resp, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{
		"id": marketID,
	}))
	if err != nil {
		t.Fatalf("GetMarket(%v): %v", marketID, err)
	}

	if got := resp.GetFields()["success"].GetBoolValue(); !got {
		t.Fatal("expected success = true")
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}

	m := data.GetStructValue().GetFields()
	if got := m["id"].GetNumberValue(); got != marketID {
		t.Errorf("id = %v, want %v", got, marketID)
	}
	if m["title"].GetStringValue() == "" {
		t.Error("market has empty title")
	}
	if m["question"].GetStringValue() == "" {
		t.Error("market has empty question")
	}
	if m["description"].GetStringValue() == "" {
		t.Error("market has empty description")
	}
	if m["conditionId"].GetStringValue() == "" {
		t.Error("market missing conditionId")
	}
	if m["resolverAddress"].GetStringValue() == "" {
		t.Error("market missing resolverAddress")
	}
	outcomes := m["outcomes"].GetListValue().GetValues()
	if len(outcomes) < 2 {
		t.Errorf("expected at least 2 outcomes, got %d", len(outcomes))
	}
}

func TestGetMarketRequiresID(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	_, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
	if !strings.Contains(err.Error(), "id is required") {
		t.Errorf("error = %q, want to contain 'id is required'", err.Error())
	}
}

func TestGetOrderbook(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	// Find a market that's actively trading
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}
	items := listResp.GetFields()["data"].GetListValue().GetValues()
	if len(items) == 0 {
		t.Skip("no markets available on testnet")
	}

	// Pick the first market with OPEN trading
	var marketID float64
	for _, item := range items {
		f := item.GetStructValue().GetFields()
		if f["tradingStatus"].GetStringValue() == "OPEN" {
			marketID = f["id"].GetNumberValue()
			break
		}
	}
	if marketID == 0 {
		// Fall back to first market
		marketID = items[0].GetStructValue().GetFields()["id"].GetNumberValue()
	}

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"id": marketID,
	}))
	if err != nil {
		t.Fatalf("GetOrderbook(%v): %v", marketID, err)
	}

	if got := resp.GetFields()["success"].GetBoolValue(); !got {
		t.Fatal("expected success = true")
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}

	ob := data.GetStructValue().GetFields()
	if ob["marketId"] == nil {
		t.Error("orderbook missing marketId")
	}
	if ob["updateTimestampMs"] == nil {
		t.Error("orderbook missing updateTimestampMs")
	}

	// asks and bids should be arrays (may be empty for inactive markets)
	if ob["asks"] == nil {
		t.Error("orderbook missing asks field")
	}
	if ob["bids"] == nil {
		t.Error("orderbook missing bids field")
	}
}

func TestGetOrderbookRequiresID(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	_, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
}

func TestListCategories(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	resp, err := svc.ListCategories(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListCategories: %v", err)
	}

	if got := resp.GetFields()["success"].GetBoolValue(); !got {
		t.Fatal("expected success = true")
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 category")
	}

	// Categories are market objects returned from /v1/categories
	// Each should have basic market fields
	first := items[0].GetStructValue().GetFields()
	if first["id"] == nil {
		t.Error("category missing id")
	}
	if first["title"].GetStringValue() == "" {
		t.Error("category has empty title")
	}
}

func TestListCategoriesPagination(t *testing.T) {
	skipUnlessIntegration(t)
	svc := testService()

	resp1, err := svc.ListCategories(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListCategories page 1: %v", err)
	}

	cursor := resp1.GetFields()["cursor"].GetStringValue()
	if cursor == "" {
		t.Skip("no second page available for categories")
	}

	resp2, err := svc.ListCategories(context.Background(), mustStruct(t, map[string]any{
		"cursor": cursor,
	}))
	if err != nil {
		t.Fatalf("ListCategories page 2: %v", err)
	}

	page2Items := resp2.GetFields()["data"].GetListValue().GetValues()
	if len(page2Items) == 0 {
		t.Fatal("expected results on page 2")
	}
}

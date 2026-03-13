package main

import (
	"context"
	"os"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil { t.Fatalf("failed to create struct: %v", err) }
	return s
}

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("PENDLE_RUN_LIVE_TESTS") == "" {
		t.Skip("set PENDLE_RUN_LIVE_TESTS=1 to run live integration tests (hits real Pendle API)")
	}
}

func liveService() *PendleService { return NewPendleService() }

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"limit": float64(5)}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListMarkets") }
	t.Logf("ListMarkets response keys: %v", keysOf(fields))
}

func TestLiveListMarketsWithChain(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(1), "limit": float64(3)}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListMarkets with chain filter") }
}

func TestLiveGetPrices(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPrices(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(1)}))
	if err != nil { t.Fatalf("GetPrices: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPrices") }
	t.Logf("GetPrices response keys: %v", keysOf(fields))
}

func TestLiveGetMarketData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(1), "limit": float64(1)}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" { t.Skip("no Ethereum markets found to test GetMarketData") }
	resp, err := svc.GetMarketData(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(chainID), "address": marketAddr}))
	if err != nil { t.Fatalf("GetMarketData: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMarketData") }
	t.Logf("GetMarketData response keys: %v", keysOf(fields))
}

func TestLiveGetHistoricalData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(1), "limit": float64(1)}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" { t.Skip("no Ethereum markets found to test GetHistoricalData") }
	resp, err := svc.GetHistoricalData(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(chainID), "address": marketAddr, "time_range": "1w"}))
	if err != nil { t.Fatalf("GetHistoricalData: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHistoricalData") }
	t.Logf("GetHistoricalData response keys: %v", keysOf(fields))
}

func TestLiveGetSwapPrices(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	listResp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(1), "limit": float64(1)}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	marketAddr, chainID := extractFirstMarket(t, listResp)
	if marketAddr == "" { t.Skip("no Ethereum markets found to test GetSwapPrices") }
	resp, err := svc.GetSwapPrices(context.Background(), mustStruct(t, map[string]any{"chain_id": float64(chainID), "market": marketAddr}))
	if err != nil {
		t.Logf("GetSwapPrices returned error (may be expected): %v", err)
		return
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetSwapPrices") }
	t.Logf("GetSwapPrices response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

func extractFirstMarket(t *testing.T, resp *structpb.Struct) (string, int64) {
	t.Helper()
	fields := resp.GetFields()
	if results, ok := fields["results"]; ok {
		items := results.GetListValue().GetValues()
		if len(items) > 0 {
			m := items[0].GetStructValue().GetFields()
			addr := m["address"].GetStringValue()
			chainID := int64(m["chainId"].GetNumberValue())
			return addr, chainID
		}
	}
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

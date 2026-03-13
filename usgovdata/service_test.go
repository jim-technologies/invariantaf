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
	if os.Getenv("USGOVDATA_RUN_LIVE_TESTS") == "" {
		t.Skip("set USGOVDATA_RUN_LIVE_TESTS=1 to run live integration tests (hits real Treasury API)")
	}
}

func liveService() *USGovDataService { return NewUSGovDataService() }

func TestLiveGetDebtToThePenny(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetDebtToThePenny(context.Background(), mustStruct(t, map[string]any{"page_size": float64(3)}))
	if err != nil { t.Fatalf("GetDebtToThePenny: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetDebtToThePenny") }
	t.Logf("GetDebtToThePenny response keys: %v", keysOf(fields))
}

func TestLiveGetTreasuryYields(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTreasuryYields(context.Background(), mustStruct(t, map[string]any{"page_size": float64(5)}))
	if err != nil { t.Fatalf("GetTreasuryYields: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTreasuryYields") }
	t.Logf("GetTreasuryYields response keys: %v", keysOf(fields))
}

func TestLiveGetTreasuryAuctions(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTreasuryAuctions(context.Background(), mustStruct(t, map[string]any{"page_size": float64(5)}))
	if err != nil { t.Fatalf("GetTreasuryAuctions: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTreasuryAuctions") }
	t.Logf("GetTreasuryAuctions response keys: %v", keysOf(fields))
}

func TestLiveGetExchangeRates(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetExchangeRates(context.Background(), mustStruct(t, map[string]any{"page_size": float64(5)}))
	if err != nil { t.Fatalf("GetExchangeRates: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetExchangeRates") }
	t.Logf("GetExchangeRates response keys: %v", keysOf(fields))
}

func TestLiveGetFederalSpending(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFederalSpending(context.Background(), mustStruct(t, map[string]any{"page_size": float64(5)}))
	if err != nil { t.Fatalf("GetFederalSpending: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFederalSpending") }
	t.Logf("GetFederalSpending response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

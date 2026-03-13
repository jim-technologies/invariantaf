package main

import (
	"context"
	"os"
	"strings"
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
	if os.Getenv("RAYDIUM_RUN_LIVE_TESTS") == "" {
		t.Skip("set RAYDIUM_RUN_LIVE_TESTS=1 to run live integration tests (hits real Raydium API)")
	}
}

func liveService() *RaydiumService { return NewRaydiumService() }

func TestLiveListPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{"page_size": float64(3), "pool_sort_field": "default"}))
	if err != nil {
		if strings.Contains(err.Error(), "500") || strings.Contains(err.Error(), "400") { t.Skipf("ListPools API error: %v", err) }
		t.Fatalf("ListPools: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListPools") }
	t.Logf("ListPools response keys: %v", keysOf(fields))
}

func TestLiveGetPoolByMints(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPoolByMints(context.Background(), mustStruct(t, map[string]any{"mint1": "So11111111111111111111111111111111111111112", "page_size": float64(3)}))
	if err != nil { t.Fatalf("GetPoolByMints: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPoolByMints") }
	t.Logf("GetPoolByMints response keys: %v", keysOf(fields))
}

func TestLiveGetTokenPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{"mints": "So11111111111111111111111111111111111111112"}))
	if err != nil { t.Fatalf("GetTokenPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTokenPrice") }
	t.Logf("GetTokenPrice response keys: %v", keysOf(fields))
}

func TestLiveListFarms(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListFarms(context.Background(), mustStruct(t, map[string]any{"page_size": float64(3)}))
	if err != nil {
		if strings.Contains(err.Error(), "404") { t.Skip("ListFarms endpoint not available (404)") }
		t.Fatalf("ListFarms: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListFarms") }
	t.Logf("ListFarms response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

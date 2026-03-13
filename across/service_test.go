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
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
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

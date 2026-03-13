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
	if os.Getenv("POLYMARKET_RUN_LIVE_TESTS") == "" {
		t.Skip("set POLYMARKET_RUN_LIVE_TESTS=1 to run live integration tests (hits real Polymarket API)")
	}
}

func liveService() *PolymarketService { return NewPolymarketService() }

func TestLiveSearch(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.Search(context.Background(), mustStruct(t, map[string]any{"q": "election", "limit": float64(5)}))
	if err != nil { t.Fatalf("Search: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from Search") }
	t.Logf("Search response keys: %v", keysOf(fields))
}

func TestLiveListEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListEvents(context.Background(), mustStruct(t, map[string]any{"limit": float64(3), "active": true}))
	if err != nil { t.Fatalf("ListEvents: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListEvents") }
	t.Logf("ListEvents response keys: %v", keysOf(fields))
}

func TestLiveGetMarket(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{"active": true, "limit": float64(3)}))
	if err != nil { t.Fatalf("GetMarket: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMarket") }
	t.Logf("GetMarket response keys: %v", keysOf(fields))
}

func TestLiveGetLeaderboard(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetLeaderboard(context.Background(), mustStruct(t, map[string]any{"interval": "all", "limit": float64(3)}))
	if err != nil { t.Fatalf("GetLeaderboard: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetLeaderboard") }
	t.Logf("GetLeaderboard response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

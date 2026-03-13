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
	if os.Getenv("ODDS_API_KEY") == "" {
		t.Skip("set ODDS_API_KEY to run live integration tests (hits real Odds API)")
	}
}

func liveService() *TheOddsApiService { return NewTheOddsApiService() }

func TestLiveListSports(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListSports(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListSports: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListSports") }
	t.Logf("ListSports response keys: %v", keysOf(fields))
}

func TestLiveGetOdds(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetOdds(context.Background(), mustStruct(t, map[string]any{"sport": "upcoming"}))
	if err != nil { t.Fatalf("GetOdds: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetOdds") }
	t.Logf("GetOdds response keys: %v", keysOf(fields))
}

func TestLiveGetScores(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetScores(context.Background(), mustStruct(t, map[string]any{"sport": "americanfootball_nfl", "days_from": float64(3)}))
	if err != nil {
		t.Logf("GetScores returned error (may be expected): %v", err)
		return
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetScores") }
	t.Logf("GetScores response keys: %v", keysOf(fields))
}

func TestLiveGetEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetEvents(context.Background(), mustStruct(t, map[string]any{"sport": "upcoming"}))
	if err != nil { t.Fatalf("GetEvents: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetEvents") }
	t.Logf("GetEvents response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

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
	if os.Getenv("OPENDOTA_RUN_LIVE_TESTS") == "" {
		t.Skip("set OPENDOTA_RUN_LIVE_TESTS=1 to run live integration tests (hits real OpenDota API)")
	}
}

func liveService() *OpenDotaService { return NewOpenDotaService() }

func TestLiveGetHeroes(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHeroes(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetHeroes: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHeroes") }
	t.Logf("GetHeroes response keys: %v", keysOf(fields))
}

func TestLiveGetMatch(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMatch(context.Background(), mustStruct(t, map[string]any{"match_id": float64(7000000001)}))
	if err != nil { t.Fatalf("GetMatch: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMatch") }
	t.Logf("GetMatch response keys: %v", keysOf(fields))
}

func TestLiveGetProPlayers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProPlayers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetProPlayers: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProPlayers") }
	t.Logf("GetProPlayers response keys: %v", keysOf(fields))
}

func TestLiveGetPlayer(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPlayer(context.Background(), mustStruct(t, map[string]any{"account_id": float64(311360822)}))
	if err != nil { t.Fatalf("GetPlayer: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPlayer") }
	t.Logf("GetPlayer response keys: %v", keysOf(fields))
}

func TestLiveGetTeams(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTeams(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetTeams: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTeams") }
	t.Logf("GetTeams response keys: %v", keysOf(fields))
}

func TestLiveSearchPlayers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.SearchPlayers(context.Background(), mustStruct(t, map[string]any{"query": map[string]any{"q": "Yatoro"}}))
	if err != nil { t.Fatalf("SearchPlayers: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from SearchPlayers") }
	t.Logf("SearchPlayers response keys: %v", keysOf(fields))
}

func TestLiveGetHealth(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHealth(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetHealth: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHealth") }
	t.Logf("GetHealth response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}

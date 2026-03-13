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
	if err != nil { t.Fatalf("GetTipFloor: %v", err) }
	fields := resp.GetFields()
	entries := fields["entries"]
	if entries == nil { t.Fatal("response has no 'entries' field") }
	items := entries.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 tip floor entry") }
	entry := items[0].GetStructValue().GetFields()
	if len(entry) == 0 { t.Fatal("tip floor entry is empty") }
	p50 := entry["landed_tips_50th_percentile"].GetNumberValue()
	if p50 <= 0 { t.Errorf("landed_tips_50th_percentile = %v, want > 0", p50) }
	t.Logf("Tip floor entries: %d", len(items))
	t.Logf("50th percentile tip: %v SOL", p50)
	t.Logf("Entry keys: %v", keysOf(entry))
}



func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

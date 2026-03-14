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
	if os.Getenv("BRAVE_RUN_LIVE_TESTS") == "" {
		t.Skip("set BRAVE_RUN_LIVE_TESTS=1 to run live integration tests (hits real Brave Search API)")
	}
	if os.Getenv("BRAVE_API_KEY") == "" {
		t.Skip("BRAVE_API_KEY not set")
	}
}

func liveService() *BraveSearchService {
	return NewBraveSearchService()
}

func TestServiceCanBeCreated(t *testing.T) {
	svc := NewBraveSearchService()
	if svc == nil {
		t.Fatal("NewBraveSearchService returned nil")
	}
	if svc.baseURL == "" {
		t.Fatal("baseURL is empty")
	}
}

func TestLiveWebSearch(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.WebSearch(context.Background(), mustStruct(t, map[string]any{"query": "golang programming", "count": float64(3)}))
	if err != nil {
		t.Fatalf("WebSearch: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from WebSearch")
	}
	t.Logf("WebSearch response keys: %v", keysOf(fields))
}

func TestLiveNewsSearch(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.NewsSearch(context.Background(), mustStruct(t, map[string]any{"query": "technology news", "count": float64(3)}))
	if err != nil {
		t.Fatalf("NewsSearch: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from NewsSearch")
	}
	t.Logf("NewsSearch response keys: %v", keysOf(fields))
}

func TestLiveImageSearch(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ImageSearch(context.Background(), mustStruct(t, map[string]any{"query": "golden gate bridge", "count": float64(3)}))
	if err != nil {
		t.Fatalf("ImageSearch: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ImageSearch")
	}
	t.Logf("ImageSearch response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

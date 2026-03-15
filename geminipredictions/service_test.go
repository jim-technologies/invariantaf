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
	if os.Getenv("GEMINI_RUN_LIVE_TESTS") == "" {
		t.Skip("set GEMINI_RUN_LIVE_TESTS=1 to run live integration tests (hits real Gemini API)")
	}
}

func liveService() *GeminiPredictionsService {
	return NewGeminiPredictionsService()
}

func TestLiveListEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListEvents(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListEvents: %v", err)
	}

	fields := resp.GetFields()
	events := fields["events"].GetListValue().GetValues()
	if len(events) == 0 {
		t.Fatal("empty response from ListEvents")
	}
	first := events[0].GetStructValue().GetFields()
	t.Logf("ListEvents returned %d events; first: title=%s category=%s status=%s",
		len(events),
		first["title"].GetStringValue(),
		first["category"].GetStringValue(),
		first["status"].GetStringValue())
}

func TestLiveListEventsWithFilters(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListEvents(context.Background(), mustStruct(t, map[string]any{
		"status":   "active",
		"category": "Crypto",
	}))
	if err != nil {
		t.Fatalf("ListEvents (filtered): %v", err)
	}

	fields := resp.GetFields()
	events := fields["events"].GetListValue().GetValues()
	t.Logf("ListEvents (active, Crypto) returned %d events", len(events))

	for _, e := range events {
		ef := e.GetStructValue().GetFields()
		cat := ef["category"].GetStringValue()
		if cat != "Crypto" {
			t.Errorf("expected category Crypto, got %s", cat)
		}
	}
}

func TestLiveGetEvent(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// First get an event ticker from the list
	listResp, err := svc.ListEvents(context.Background(), mustStruct(t, map[string]any{
		"status": "active",
	}))
	if err != nil {
		t.Fatalf("ListEvents: %v", err)
	}
	events := listResp.GetFields()["events"].GetListValue().GetValues()
	if len(events) == 0 {
		t.Skip("no active events to test GetEvent")
	}
	ticker := events[0].GetStructValue().GetFields()["ticker"].GetStringValue()
	if ticker == "" {
		t.Skip("first event has no ticker")
	}

	resp, err := svc.GetEvent(context.Background(), mustStruct(t, map[string]any{
		"event_ticker": ticker,
	}))
	if err != nil {
		t.Fatalf("GetEvent(%s): %v", ticker, err)
	}

	fields := resp.GetFields()
	event := fields["event"].GetStructValue().GetFields()
	t.Logf("GetEvent(%s): title=%s type=%s",
		ticker,
		event["title"].GetStringValue(),
		event["type"].GetStringValue())
}

func TestLiveListNewlyListedEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListNewlyListedEvents(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListNewlyListedEvents: %v", err)
	}

	fields := resp.GetFields()
	events := fields["events"].GetListValue().GetValues()
	t.Logf("ListNewlyListedEvents returned %d events", len(events))
}

func TestLiveListRecentlySettledEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListRecentlySettledEvents(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListRecentlySettledEvents: %v", err)
	}

	fields := resp.GetFields()
	events := fields["events"].GetListValue().GetValues()
	t.Logf("ListRecentlySettledEvents returned %d events", len(events))
}

func TestLiveListUpcomingEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListUpcomingEvents(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListUpcomingEvents: %v", err)
	}

	fields := resp.GetFields()
	events := fields["events"].GetListValue().GetValues()
	t.Logf("ListUpcomingEvents returned %d events", len(events))
}

func TestLiveListCategories(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListCategories(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListCategories: %v", err)
	}

	fields := resp.GetFields()
	categories := fields["categories"].GetListValue().GetValues()
	if len(categories) == 0 {
		t.Fatal("empty response from ListCategories")
	}
	names := make([]string, 0, len(categories))
	for _, c := range categories {
		names = append(names, c.GetStringValue())
	}
	t.Logf("ListCategories returned %d categories: %v", len(categories), names)
}

func TestSmokeNewGeminiPredictionsService(t *testing.T) {
	svc := NewGeminiPredictionsService()
	if svc == nil {
		t.Fatal("NewGeminiPredictionsService returned nil")
	}
	if svc.baseURL == "" {
		t.Fatal("baseURL is empty")
	}
	if svc.client == nil {
		t.Fatal("client is nil")
	}
}

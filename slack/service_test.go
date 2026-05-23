package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	invariant "github.com/jim-technologies/invariantprotocol/go"
	"google.golang.org/protobuf/types/known/structpb"
)

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("NewStruct: %v", err)
	}
	return s
}

func TestServerWiring(t *testing.T) {
	srv, err := invariant.ServerFromBytes(descriptorBytes)
	if err != nil {
		t.Fatalf("ServerFromBytes: %v", err)
	}
	if err := srv.Register(NewSlackService()); err != nil {
		t.Fatalf("Register: %v", err)
	}
	tools := srv.Tools()
	if len(tools) < 30 {
		t.Fatalf("expected at least 30 tools, got %d", len(tools))
	}
	if _, ok := tools["SlackService.ChatPostMessage"]; !ok {
		t.Fatalf("missing SlackService.ChatPostMessage")
	}
	if _, ok := tools["SlackService.AuthTest"]; !ok {
		t.Fatalf("missing SlackService.AuthTest")
	}
}

func TestChatPostMessageEncoding(t *testing.T) {
	var captured string
	var captureContentType string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		captureContentType = r.Header.Get("Content-Type")
		b := make([]byte, r.ContentLength)
		_, _ = r.Body.Read(b)
		captured = string(b)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"channel":"C1","ts":"1.0"}`))
	}))
	defer server.Close()

	t.Setenv("SLACK_BASE_URL", server.URL)
	t.Setenv("SLACK_BOT_TOKEN", "xoxb-test")

	svc := NewSlackService()
	resp, err := svc.ChatPostMessage(context.Background(), mustStruct(t, map[string]any{
		"channel": "C1",
		"text":    "hello world",
	}))
	if err != nil {
		t.Fatalf("ChatPostMessage: %v", err)
	}
	if resp.GetFields()["ok"].GetBoolValue() != true {
		t.Fatalf("expected ok=true, got %v", resp.AsMap())
	}
	if !strings.HasPrefix(captureContentType, "application/json") {
		t.Fatalf("expected JSON content type, got %q", captureContentType)
	}
	var parsed map[string]any
	if err := json.Unmarshal([]byte(captured), &parsed); err != nil {
		t.Fatalf("body not valid JSON: %v (raw: %q)", err, captured)
	}
	if parsed["channel"] != "C1" || parsed["text"] != "hello world" {
		t.Fatalf("unexpected body: %v", parsed)
	}
}

func TestConversationsListFormParams(t *testing.T) {
	var capturedBody string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b := make([]byte, r.ContentLength)
		_, _ = r.Body.Read(b)
		capturedBody = string(b)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"channels":[]}`))
	}))
	defer server.Close()

	t.Setenv("SLACK_BASE_URL", server.URL)
	t.Setenv("SLACK_BOT_TOKEN", "xoxb-test")

	svc := NewSlackService()
	_, err := svc.ConversationsList(context.Background(), mustStruct(t, map[string]any{
		"types":            "public_channel,private_channel",
		"exclude_archived": true,
		"limit":            50,
	}))
	if err != nil {
		t.Fatalf("ConversationsList: %v", err)
	}
	if !strings.Contains(capturedBody, "types=public_channel") {
		t.Fatalf("missing types param in body: %q", capturedBody)
	}
	if !strings.Contains(capturedBody, "exclude_archived=true") {
		t.Fatalf("missing exclude_archived in body: %q", capturedBody)
	}
	if !strings.Contains(capturedBody, "limit=50") {
		t.Fatalf("missing limit in body: %q", capturedBody)
	}
}

func TestMissingTokenFails(t *testing.T) {
	t.Setenv("SLACK_BASE_URL", "https://example.invalid")
	t.Setenv("SLACK_BOT_TOKEN", "")
	svc := NewSlackService()
	_, err := svc.AuthTest(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatalf("expected error with missing token")
	}
}

// Live test (skipped unless explicitly enabled).
func TestLiveAuthTest(t *testing.T) {
	if os.Getenv("SLACK_RUN_LIVE_TESTS") != "1" {
		t.Skip("set SLACK_RUN_LIVE_TESTS=1 + SLACK_BOT_TOKEN to run")
	}
	if os.Getenv("SLACK_BOT_TOKEN") == "" {
		t.Skip("SLACK_BOT_TOKEN not set")
	}
	svc := NewSlackService()
	resp, err := svc.AuthTest(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("AuthTest: %v", err)
	}
	if resp.GetFields()["ok"].GetBoolValue() != true {
		t.Fatalf("auth.test returned ok=false: %v", resp.AsMap())
	}
}

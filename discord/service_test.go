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
	if err := srv.Register(NewDiscordService()); err != nil {
		t.Fatalf("Register: %v", err)
	}
	tools := srv.Tools()
	if len(tools) < 40 {
		t.Fatalf("expected at least 40 tools, got %d", len(tools))
	}
	for _, name := range []string{
		"DiscordService.CreateMessage",
		"DiscordService.GetCurrentUser",
		"DiscordService.GetChannel",
		"DiscordService.ExecuteWebhook",
	} {
		if _, ok := tools[name]; !ok {
			t.Fatalf("missing tool %s", name)
		}
	}
}

func TestCreateMessageBody(t *testing.T) {
	var capturedPath, capturedAuth string
	var capturedBody map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedPath = r.URL.Path
		capturedAuth = r.Header.Get("Authorization")
		_ = json.NewDecoder(r.Body).Decode(&capturedBody)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"123","content":"hi"}`))
	}))
	defer server.Close()

	t.Setenv("DISCORD_BASE_URL", server.URL)
	t.Setenv("DISCORD_BOT_TOKEN", "test-token")

	svc := NewDiscordService()
	body, _ := structpb.NewStruct(map[string]any{"content": "hi", "tts": false})
	resp, err := svc.CreateMessage(context.Background(), mustStruct(t, map[string]any{
		"channel_id": "C999",
		"body":       body.AsMap(),
	}))
	if err != nil {
		t.Fatalf("CreateMessage: %v", err)
	}
	if resp.GetFields()["id"].GetStringValue() != "123" {
		t.Fatalf("expected id=123 in response, got %v", resp.AsMap())
	}
	if !strings.HasSuffix(capturedPath, "/channels/C999/messages") {
		t.Fatalf("unexpected path: %s", capturedPath)
	}
	if !strings.HasPrefix(capturedAuth, "Bot ") {
		t.Fatalf("expected Bot auth, got %q", capturedAuth)
	}
	if capturedBody["content"] != "hi" {
		t.Fatalf("unexpected body: %v", capturedBody)
	}
}

func TestReactionPathEncoding(t *testing.T) {
	var capturedRawPath string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Use EscapedPath to see the wire form before Go decodes %-escapes.
		capturedRawPath = r.URL.EscapedPath()
		w.WriteHeader(http.StatusNoContent)
	}))
	defer server.Close()

	t.Setenv("DISCORD_BASE_URL", server.URL)
	t.Setenv("DISCORD_BOT_TOKEN", "x")

	svc := NewDiscordService()
	_, err := svc.CreateReaction(context.Background(), mustStruct(t, map[string]any{
		"channel_id": "C1",
		"message_id": "M1",
		"emoji":      "🔥",
	}))
	if err != nil {
		t.Fatalf("CreateReaction: %v", err)
	}
	// 🔥 = U+1F525 = %F0%9F%94%A5 — path-escaped, no slashes corrupted.
	if !strings.HasSuffix(capturedRawPath, "/reactions/%F0%9F%94%A5/@me") {
		t.Fatalf("path escaping wrong: %s", capturedRawPath)
	}
}

func TestExecuteWebhookNoAuth(t *testing.T) {
	var capturedAuth string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedAuth = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusNoContent)
	}))
	defer server.Close()

	t.Setenv("DISCORD_BASE_URL", server.URL)
	t.Setenv("DISCORD_BOT_TOKEN", "irrelevant")

	svc := NewDiscordService()
	body, _ := structpb.NewStruct(map[string]any{"content": "hello"})
	_, err := svc.ExecuteWebhook(context.Background(), mustStruct(t, map[string]any{
		"webhook_id":    "W",
		"webhook_token": "T",
		"body":          body.AsMap(),
	}))
	if err != nil {
		t.Fatalf("ExecuteWebhook: %v", err)
	}
	if capturedAuth != "" {
		t.Fatalf("expected no auth header for webhook, got %q", capturedAuth)
	}
}

func TestMissingTokenFailsForAuthedEndpoint(t *testing.T) {
	t.Setenv("DISCORD_BASE_URL", "https://example.invalid")
	t.Setenv("DISCORD_BOT_TOKEN", "")
	svc := NewDiscordService()
	_, err := svc.GetCurrentUser(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatalf("expected error for missing token")
	}
}

// Live test (skipped unless explicitly enabled).
func TestLiveGetCurrentUser(t *testing.T) {
	if os.Getenv("DISCORD_RUN_LIVE_TESTS") != "1" {
		t.Skip("set DISCORD_RUN_LIVE_TESTS=1 + DISCORD_BOT_TOKEN to run")
	}
	if os.Getenv("DISCORD_BOT_TOKEN") == "" {
		t.Skip("DISCORD_BOT_TOKEN not set")
	}
	svc := NewDiscordService()
	resp, err := svc.GetCurrentUser(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetCurrentUser: %v", err)
	}
	if resp.GetFields()["id"].GetStringValue() == "" {
		t.Fatalf("expected user id in response: %v", resp.AsMap())
	}
}

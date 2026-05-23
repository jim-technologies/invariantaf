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
	if err := srv.Register(NewTelegramService()); err != nil {
		t.Fatalf("Register: %v", err)
	}
	tools := srv.Tools()
	if len(tools) < 40 {
		t.Fatalf("expected at least 40 tools, got %d", len(tools))
	}
	for _, n := range []string{
		"TelegramService.GetMe",
		"TelegramService.SendMessage",
		"TelegramService.EditMessageText",
		"TelegramService.SetWebhook",
	} {
		if _, ok := tools[n]; !ok {
			t.Fatalf("missing tool %s", n)
		}
	}
}

func TestSendMessageBody(t *testing.T) {
	var capturedPath string
	var capturedBody map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedPath = r.URL.Path
		_ = json.NewDecoder(r.Body).Decode(&capturedBody)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"result":{"message_id":42,"date":1,"chat":{"id":1}}}`))
	}))
	defer server.Close()

	t.Setenv("TELEGRAM_BASE_URL", server.URL)
	t.Setenv("TELEGRAM_BOT_TOKEN", "TEST_TOKEN")

	svc := NewTelegramService()
	resp, err := svc.SendMessage(context.Background(), mustStruct(t, map[string]any{
		"chat_id":    "@channel",
		"text":       "hello",
		"parse_mode": "MarkdownV2",
	}))
	if err != nil {
		t.Fatalf("SendMessage: %v", err)
	}
	if resp.GetFields()["message_id"].GetNumberValue() != 42 {
		t.Fatalf("expected message_id=42, got %v", resp.AsMap())
	}
	if !strings.HasSuffix(capturedPath, "/botTEST_TOKEN/sendMessage") {
		t.Fatalf("unexpected path: %s", capturedPath)
	}
	if capturedBody["text"] != "hello" {
		t.Fatalf("missing text: %v", capturedBody)
	}
	if capturedBody["parse_mode"] != "MarkdownV2" {
		t.Fatalf("missing parse_mode: %v", capturedBody)
	}
	// Optional zero-valued fields should not be sent.
	if _, ok := capturedBody["disable_notification"]; ok {
		t.Fatalf("zero-valued bool should be dropped: %v", capturedBody)
	}
}

func TestGetMeUsesEnvelopeResult(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"result":{"id":123,"is_bot":true,"username":"testbot"}}`))
	}))
	defer server.Close()

	t.Setenv("TELEGRAM_BASE_URL", server.URL)
	t.Setenv("TELEGRAM_BOT_TOKEN", "x")
	svc := NewTelegramService()
	resp, err := svc.GetMe(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetMe: %v", err)
	}
	if resp.GetFields()["username"].GetStringValue() != "testbot" {
		t.Fatalf("expected username=testbot, got %v", resp.AsMap())
	}
}

func TestErrorEnvelopeBecomesError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":false,"description":"Bad Request: chat not found","error_code":400}`))
	}))
	defer server.Close()

	t.Setenv("TELEGRAM_BASE_URL", server.URL)
	t.Setenv("TELEGRAM_BOT_TOKEN", "x")
	svc := NewTelegramService()
	_, err := svc.GetChat(context.Background(), mustStruct(t, map[string]any{"chat_id": "@missing"}))
	if err == nil {
		t.Fatalf("expected error for ok=false envelope")
	}
	if !strings.Contains(err.Error(), "chat not found") {
		t.Fatalf("expected error to include description, got: %v", err)
	}
}

func TestMissingTokenFails(t *testing.T) {
	t.Setenv("TELEGRAM_BASE_URL", "https://example.invalid")
	t.Setenv("TELEGRAM_BOT_TOKEN", "")
	svc := NewTelegramService()
	_, err := svc.GetMe(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatalf("expected error for missing token")
	}
}

// Live test (skipped unless explicitly enabled).
func TestLiveGetMe(t *testing.T) {
	if os.Getenv("TELEGRAM_RUN_LIVE_TESTS") != "1" {
		t.Skip("set TELEGRAM_RUN_LIVE_TESTS=1 + TELEGRAM_BOT_TOKEN to run")
	}
	if os.Getenv("TELEGRAM_BOT_TOKEN") == "" {
		t.Skip("TELEGRAM_BOT_TOKEN not set")
	}
	svc := NewTelegramService()
	resp, err := svc.GetMe(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetMe: %v", err)
	}
	if !resp.GetFields()["is_bot"].GetBoolValue() {
		t.Fatalf("expected is_bot=true, got %v", resp.AsMap())
	}
}

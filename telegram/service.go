package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"google.golang.org/protobuf/types/known/structpb"
)

// TelegramService proxies the Telegram Bot API. Authentication is via the
// token embedded in the path (.../bot<TOKEN>/method).
type TelegramService struct {
	baseURL string
	token   string
	client  *http.Client
}

func NewTelegramService() *TelegramService {
	base := os.Getenv("TELEGRAM_BASE_URL")
	if base == "" {
		base = "https://api.telegram.org"
	}
	return &TelegramService{
		baseURL: strings.TrimRight(base, "/"),
		token:   os.Getenv("TELEGRAM_BOT_TOKEN"),
		client:  &http.Client{},
	}
}

// call posts a JSON body to /bot<token>/<method> and returns the parsed
// "result" or the full envelope when no "result" key is present.
func (s *TelegramService) call(method string, body map[string]any) (any, error) {
	if s.token == "" {
		return nil, fmt.Errorf("TELEGRAM_BOT_TOKEN is not set")
	}
	url := fmt.Sprintf("%s/bot%s/%s", s.baseURL, s.token, method)
	cleaned := dropZeroValues(body)
	var reqBody io.Reader
	if len(cleaned) > 0 {
		buf, err := json.Marshal(cleaned)
		if err != nil {
			return nil, fmt.Errorf("encode body: %w", err)
		}
		reqBody = bytes.NewReader(buf)
	}
	req, err := http.NewRequest("POST", url, reqBody)
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	if reqBody != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Accept", "application/json")
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http %s: %w", method, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("telegram %s returned %d: %s", method, resp.StatusCode, string(raw))
	}
	var env map[string]any
	if err := json.Unmarshal(raw, &env); err != nil {
		return nil, fmt.Errorf("decode body: %w (raw: %s)", err, string(raw))
	}
	if ok, _ := env["ok"].(bool); !ok {
		desc, _ := env["description"].(string)
		return nil, fmt.Errorf("telegram %s: %s (raw: %s)", method, desc, string(raw))
	}
	if r, ok := env["result"]; ok {
		return r, nil
	}
	return env, nil
}

// wrap returns the response as Struct, wrapping primitives or arrays as needed.
func wrap(v any) (*structpb.Struct, error) {
	switch x := v.(type) {
	case map[string]any:
		return structpb.NewStruct(x)
	case []any:
		return structpb.NewStruct(map[string]any{"items": x})
	default:
		return structpb.NewStruct(map[string]any{"value": x})
	}
}

// dropZeroValues removes empty strings, zero numbers, false booleans, and
// empty maps/slices, matching Telegram's expectation that optional params be
// absent rather than zero-valued. Top-level only.
func dropZeroValues(m map[string]any) map[string]any {
	out := make(map[string]any, len(m))
	for k, v := range m {
		if isZero(v) {
			continue
		}
		out[k] = v
	}
	return out
}

func isZero(v any) bool {
	switch x := v.(type) {
	case nil:
		return true
	case string:
		return x == ""
	case bool:
		return !x
	case int, int32, int64, float32, float64:
		// reflect avoidance — quick coverage of the types we put into bodies.
		switch n := v.(type) {
		case int:
			return n == 0
		case int32:
			return n == 0
		case int64:
			return n == 0
		case float32:
			return n == 0
		case float64:
			return n == 0
		}
	case []any:
		return len(x) == 0
	case map[string]any:
		return len(x) == 0
	}
	return false
}

// -- field readers --

func getStr(fields map[string]*structpb.Value, key string) string {
	if v, ok := fields[key]; ok {
		return v.GetStringValue()
	}
	return ""
}

func getBool(fields map[string]*structpb.Value, key string) bool {
	if v, ok := fields[key]; ok {
		return v.GetBoolValue()
	}
	return false
}

func getInt(fields map[string]*structpb.Value, key string) int64 {
	if v, ok := fields[key]; ok {
		return int64(v.GetNumberValue())
	}
	return 0
}

func getFloat(fields map[string]*structpb.Value, key string) float64 {
	if v, ok := fields[key]; ok {
		return v.GetNumberValue()
	}
	return 0
}

// structField returns a Struct field's map representation, or nil if missing.
// Telegram accepts JSON objects for entities/markup/etc.
func structField(fields map[string]*structpb.Value, key string) any {
	if v, ok := fields[key]; ok {
		if s := v.GetStructValue(); s != nil {
			m := s.AsMap()
			// Treat {"items":[...]} as the underlying array.
			if items, ok := m["items"]; ok && len(m) == 1 {
				return items
			}
			if len(m) > 0 {
				return m
			}
		}
	}
	return nil
}

// listFieldStrings reads a repeated int field (or string) into a []any.
func intsField(fields map[string]*structpb.Value, key string) []any {
	if v, ok := fields[key]; ok {
		if l := v.GetListValue(); l != nil {
			out := make([]any, 0, len(l.Values))
			for _, val := range l.Values {
				out = append(out, int64(val.GetNumberValue()))
			}
			return out
		}
	}
	return nil
}

// -- handler helpers --

// commonOpts adds optional fields shared by many "send*" methods.
func addSendOpts(body map[string]any, f map[string]*structpb.Value) {
	if v := getBool(f, "disable_notification"); v {
		body["disable_notification"] = true
	}
	if v := getBool(f, "protect_content"); v {
		body["protect_content"] = true
	}
	if v := getInt(f, "reply_to_message_id"); v != 0 {
		body["reply_to_message_id"] = v
	}
	if rm := structField(f, "reply_markup"); rm != nil {
		body["reply_markup"] = rm
	}
}

// -- RPC handlers --

func (s *TelegramService) GetMe(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	r, err := s.call("getMe", nil)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) LogOut(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	r, err := s.call("logOut", nil)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) Close(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	r, err := s.call("close", nil)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"text":    getStr(f, "text"),
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if v := structField(f, "entities"); v != nil {
		body["entities"] = v
	}
	if getBool(f, "disable_web_page_preview") {
		body["disable_web_page_preview"] = true
	}
	if getBool(f, "allow_sending_without_reply") {
		body["allow_sending_without_reply"] = true
	}
	if v := getInt(f, "message_thread_id"); v != 0 {
		body["message_thread_id"] = v
	}
	if v := getStr(f, "business_connection_id"); v != "" {
		body["business_connection_id"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) ForwardMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":      getStr(f, "chat_id"),
		"from_chat_id": getStr(f, "from_chat_id"),
		"message_id":   getInt(f, "message_id"),
	}
	if getBool(f, "disable_notification") {
		body["disable_notification"] = true
	}
	if getBool(f, "protect_content") {
		body["protect_content"] = true
	}
	if v := getInt(f, "message_thread_id"); v != 0 {
		body["message_thread_id"] = v
	}
	r, err := s.call("forwardMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) CopyMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":      getStr(f, "chat_id"),
		"from_chat_id": getStr(f, "from_chat_id"),
		"message_id":   getInt(f, "message_id"),
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("copyMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendPhoto(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"photo":   getStr(f, "photo"),
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if getBool(f, "has_spoiler") {
		body["has_spoiler"] = true
	}
	addSendOpts(body, f)
	r, err := s.call("sendPhoto", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendAudio(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"audio":   getStr(f, "audio"),
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if v := getInt(f, "duration"); v != 0 {
		body["duration"] = v
	}
	if v := getStr(f, "performer"); v != "" {
		body["performer"] = v
	}
	if v := getStr(f, "title"); v != "" {
		body["title"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendAudio", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendDocument(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":  getStr(f, "chat_id"),
		"document": getStr(f, "document"),
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if getBool(f, "disable_content_type_detection") {
		body["disable_content_type_detection"] = true
	}
	addSendOpts(body, f)
	r, err := s.call("sendDocument", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendVideo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"video":   getStr(f, "video"),
	}
	if v := getInt(f, "duration"); v != 0 {
		body["duration"] = v
	}
	if v := getInt(f, "width"); v != 0 {
		body["width"] = v
	}
	if v := getInt(f, "height"); v != 0 {
		body["height"] = v
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if getBool(f, "has_spoiler") {
		body["has_spoiler"] = true
	}
	if getBool(f, "supports_streaming") {
		body["supports_streaming"] = true
	}
	addSendOpts(body, f)
	r, err := s.call("sendVideo", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendAnimation(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":   getStr(f, "chat_id"),
		"animation": getStr(f, "animation"),
	}
	if v := getInt(f, "duration"); v != 0 {
		body["duration"] = v
	}
	if v := getInt(f, "width"); v != 0 {
		body["width"] = v
	}
	if v := getInt(f, "height"); v != 0 {
		body["height"] = v
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if getBool(f, "has_spoiler") {
		body["has_spoiler"] = true
	}
	addSendOpts(body, f)
	r, err := s.call("sendAnimation", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendVoice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"voice":   getStr(f, "voice"),
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if v := getInt(f, "duration"); v != 0 {
		body["duration"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendVoice", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendVideoNote(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":    getStr(f, "chat_id"),
		"video_note": getStr(f, "video_note"),
	}
	if v := getInt(f, "duration"); v != 0 {
		body["duration"] = v
	}
	if v := getInt(f, "length"); v != 0 {
		body["length"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendVideoNote", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendLocation(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":   getStr(f, "chat_id"),
		"latitude":  getFloat(f, "latitude"),
		"longitude": getFloat(f, "longitude"),
	}
	if v := getFloat(f, "horizontal_accuracy"); v != 0 {
		body["horizontal_accuracy"] = v
	}
	if v := getInt(f, "live_period"); v != 0 {
		body["live_period"] = v
	}
	if v := getInt(f, "heading"); v != 0 {
		body["heading"] = v
	}
	if v := getInt(f, "proximity_alert_radius"); v != 0 {
		body["proximity_alert_radius"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendLocation", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendVenue(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":   getStr(f, "chat_id"),
		"latitude":  getFloat(f, "latitude"),
		"longitude": getFloat(f, "longitude"),
		"title":     getStr(f, "title"),
		"address":   getStr(f, "address"),
	}
	for _, k := range []string{"foursquare_id", "foursquare_type", "google_place_id", "google_place_type"} {
		if v := getStr(f, k); v != "" {
			body[k] = v
		}
	}
	addSendOpts(body, f)
	r, err := s.call("sendVenue", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendContact(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":      getStr(f, "chat_id"),
		"phone_number": getStr(f, "phone_number"),
		"first_name":   getStr(f, "first_name"),
	}
	if v := getStr(f, "last_name"); v != "" {
		body["last_name"] = v
	}
	if v := getStr(f, "vcard"); v != "" {
		body["vcard"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendContact", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendPoll(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":  getStr(f, "chat_id"),
		"question": getStr(f, "question"),
	}
	if v := structField(f, "options"); v != nil {
		body["options"] = v
	}
	if getBool(f, "is_anonymous") {
		body["is_anonymous"] = true
	}
	if v := getStr(f, "type"); v != "" {
		body["type"] = v
	}
	if getBool(f, "allows_multiple_answers") {
		body["allows_multiple_answers"] = true
	}
	if v := getInt(f, "correct_option_id"); v >= 0 && f["correct_option_id"] != nil {
		body["correct_option_id"] = v
	}
	if v := getStr(f, "explanation"); v != "" {
		body["explanation"] = v
	}
	if v := getInt(f, "open_period"); v != 0 {
		body["open_period"] = v
	}
	if v := getInt(f, "close_date"); v != 0 {
		body["close_date"] = v
	}
	if getBool(f, "is_closed") {
		body["is_closed"] = true
	}
	addSendOpts(body, f)
	r, err := s.call("sendPoll", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendDice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"chat_id": getStr(f, "chat_id")}
	if v := getStr(f, "emoji"); v != "" {
		body["emoji"] = v
	}
	addSendOpts(body, f)
	r, err := s.call("sendDice", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendChatAction(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"action":  getStr(f, "action"),
	}
	if v := getInt(f, "message_thread_id"); v != 0 {
		body["message_thread_id"] = v
	}
	r, err := s.call("sendChatAction", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) EditMessageText(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"text": getStr(f, "text")}
	if v := getStr(f, "chat_id"); v != "" {
		body["chat_id"] = v
	}
	if v := getInt(f, "message_id"); v != 0 {
		body["message_id"] = v
	}
	if v := getStr(f, "inline_message_id"); v != "" {
		body["inline_message_id"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if getBool(f, "disable_web_page_preview") {
		body["disable_web_page_preview"] = true
	}
	if rm := structField(f, "reply_markup"); rm != nil {
		body["reply_markup"] = rm
	}
	r, err := s.call("editMessageText", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) EditMessageCaption(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := getStr(f, "chat_id"); v != "" {
		body["chat_id"] = v
	}
	if v := getInt(f, "message_id"); v != 0 {
		body["message_id"] = v
	}
	if v := getStr(f, "inline_message_id"); v != "" {
		body["inline_message_id"] = v
	}
	if v := getStr(f, "caption"); v != "" {
		body["caption"] = v
	}
	if v := getStr(f, "parse_mode"); v != "" {
		body["parse_mode"] = v
	}
	if rm := structField(f, "reply_markup"); rm != nil {
		body["reply_markup"] = rm
	}
	r, err := s.call("editMessageCaption", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) EditMessageReplyMarkup(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := getStr(f, "chat_id"); v != "" {
		body["chat_id"] = v
	}
	if v := getInt(f, "message_id"); v != 0 {
		body["message_id"] = v
	}
	if v := getStr(f, "inline_message_id"); v != "" {
		body["inline_message_id"] = v
	}
	if rm := structField(f, "reply_markup"); rm != nil {
		body["reply_markup"] = rm
	}
	r, err := s.call("editMessageReplyMarkup", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) DeleteMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":    getStr(f, "chat_id"),
		"message_id": getInt(f, "message_id"),
	}
	r, err := s.call("deleteMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) DeleteMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":     getStr(f, "chat_id"),
		"message_ids": intsField(f, "message_ids"),
	}
	r, err := s.call("deleteMessages", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetChat(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("getChat", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetChatAdministrators(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("getChatAdministrators", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetChatMemberCount(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("getChatMemberCount", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetChatMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"user_id": getInt(f, "user_id"),
	}
	r, err := s.call("getChatMember", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) BanChatMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"user_id": getInt(f, "user_id"),
	}
	if v := getInt(f, "until_date"); v != 0 {
		body["until_date"] = v
	}
	if getBool(f, "revoke_messages") {
		body["revoke_messages"] = true
	}
	r, err := s.call("banChatMember", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) UnbanChatMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"user_id": getInt(f, "user_id"),
	}
	if getBool(f, "only_if_banned") {
		body["only_if_banned"] = true
	}
	r, err := s.call("unbanChatMember", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) RestrictChatMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":     getStr(f, "chat_id"),
		"user_id":     getInt(f, "user_id"),
		"permissions": structField(f, "permissions"),
	}
	if getBool(f, "use_independent_chat_permissions") {
		body["use_independent_chat_permissions"] = true
	}
	if v := getInt(f, "until_date"); v != 0 {
		body["until_date"] = v
	}
	r, err := s.call("restrictChatMember", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) PromoteChatMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"user_id": getInt(f, "user_id"),
	}
	for _, k := range []string{
		"is_anonymous", "can_manage_chat", "can_post_messages", "can_edit_messages",
		"can_delete_messages", "can_manage_video_chats", "can_restrict_members",
		"can_promote_members", "can_change_info", "can_invite_users",
		"can_pin_messages", "can_manage_topics", "can_post_stories",
		"can_edit_stories", "can_delete_stories",
	} {
		if getBool(f, k) {
			body[k] = true
		}
	}
	r, err := s.call("promoteChatMember", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetChatTitle(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id": getStr(f, "chat_id"),
		"title":   getStr(f, "title"),
	}
	r, err := s.call("setChatTitle", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetChatDescription(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":     getStr(f, "chat_id"),
		"description": getStr(f, "description"),
	}
	r, err := s.call("setChatDescription", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) PinChatMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":    getStr(f, "chat_id"),
		"message_id": getInt(f, "message_id"),
	}
	if getBool(f, "disable_notification") {
		body["disable_notification"] = true
	}
	if v := getStr(f, "business_connection_id"); v != "" {
		body["business_connection_id"] = v
	}
	r, err := s.call("pinChatMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) UnpinChatMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"chat_id": getStr(f, "chat_id")}
	if v := getInt(f, "message_id"); v != 0 {
		body["message_id"] = v
	}
	if v := getStr(f, "business_connection_id"); v != "" {
		body["business_connection_id"] = v
	}
	r, err := s.call("unpinChatMessage", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) UnpinAllChatMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("unpinAllChatMessages", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) LeaveChat(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("leaveChat", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetUpdates(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := getInt(f, "offset"); v != 0 {
		body["offset"] = v
	}
	if v := getInt(f, "limit"); v != 0 {
		body["limit"] = v
	}
	if v := getInt(f, "timeout"); v != 0 {
		body["timeout"] = v
	}
	if v := structField(f, "allowed_updates"); v != nil {
		body["allowed_updates"] = v
	}
	r, err := s.call("getUpdates", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetWebhook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"url": getStr(f, "url")}
	if v := getStr(f, "certificate"); v != "" {
		body["certificate"] = v
	}
	if v := getStr(f, "ip_address"); v != "" {
		body["ip_address"] = v
	}
	if v := getInt(f, "max_connections"); v != 0 {
		body["max_connections"] = v
	}
	if v := structField(f, "allowed_updates"); v != nil {
		body["allowed_updates"] = v
	}
	if getBool(f, "drop_pending_updates") {
		body["drop_pending_updates"] = true
	}
	if v := getStr(f, "secret_token"); v != "" {
		body["secret_token"] = v
	}
	r, err := s.call("setWebhook", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) DeleteWebhook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if getBool(f, "drop_pending_updates") {
		body["drop_pending_updates"] = true
	}
	r, err := s.call("deleteWebhook", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetWebhookInfo(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	r, err := s.call("getWebhookInfo", nil)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetFile(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("getFile", map[string]any{"file_id": getStr(f, "file_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) AnswerCallbackQuery(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"callback_query_id": getStr(f, "callback_query_id")}
	if v := getStr(f, "text"); v != "" {
		body["text"] = v
	}
	if getBool(f, "show_alert") {
		body["show_alert"] = true
	}
	if v := getStr(f, "url"); v != "" {
		body["url"] = v
	}
	if v := getInt(f, "cache_time"); v != 0 {
		body["cache_time"] = v
	}
	r, err := s.call("answerCallbackQuery", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetMyCommands(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := structField(f, "commands"); v != nil {
		body["commands"] = v
	}
	if v := structField(f, "scope"); v != nil {
		body["scope"] = v
	}
	if v := getStr(f, "language_code"); v != "" {
		body["language_code"] = v
	}
	r, err := s.call("setMyCommands", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) GetMyCommands(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := structField(f, "scope"); v != nil {
		body["scope"] = v
	}
	if v := getStr(f, "language_code"); v != "" {
		body["language_code"] = v
	}
	r, err := s.call("getMyCommands", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) DeleteMyCommands(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := structField(f, "scope"); v != nil {
		body["scope"] = v
	}
	if v := getStr(f, "language_code"); v != "" {
		body["language_code"] = v
	}
	r, err := s.call("deleteMyCommands", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetMyDescription(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := getStr(f, "description"); v != "" {
		body["description"] = v
	}
	if v := getStr(f, "language_code"); v != "" {
		body["language_code"] = v
	}
	r, err := s.call("setMyDescription", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SetMyShortDescription(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if v := getStr(f, "short_description"); v != "" {
		body["short_description"] = v
	}
	if v := getStr(f, "language_code"); v != "" {
		body["language_code"] = v
	}
	r, err := s.call("setMyShortDescription", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) SendInvoice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"chat_id":        getStr(f, "chat_id"),
		"title":          getStr(f, "title"),
		"description":    getStr(f, "description"),
		"payload":        getStr(f, "payload"),
		"provider_token": getStr(f, "provider_token"),
		"currency":       getStr(f, "currency"),
	}
	if v := structField(f, "prices"); v != nil {
		body["prices"] = v
	}
	if v := getInt(f, "max_tip_amount"); v != 0 {
		body["max_tip_amount"] = v
	}
	if v := structField(f, "suggested_tip_amounts"); v != nil {
		body["suggested_tip_amounts"] = v
	}
	for _, k := range []string{
		"start_parameter", "provider_data", "photo_url",
	} {
		if v := getStr(f, k); v != "" {
			body[k] = v
		}
	}
	for _, k := range []string{"photo_size", "photo_width", "photo_height"} {
		if v := getInt(f, k); v != 0 {
			body[k] = v
		}
	}
	for _, k := range []string{
		"need_name", "need_phone_number", "need_email", "need_shipping_address",
		"send_phone_number_to_provider", "send_email_to_provider", "is_flexible",
	} {
		if getBool(f, k) {
			body[k] = true
		}
	}
	addSendOpts(body, f)
	r, err := s.call("sendInvoice", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) ExportChatInviteLink(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	r, err := s.call("exportChatInviteLink", map[string]any{"chat_id": getStr(f, "chat_id")})
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

func (s *TelegramService) CreateChatInviteLink(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"chat_id": getStr(f, "chat_id")}
	if v := getStr(f, "name"); v != "" {
		body["name"] = v
	}
	if v := getInt(f, "expire_date"); v != 0 {
		body["expire_date"] = v
	}
	if v := getInt(f, "member_limit"); v != 0 {
		body["member_limit"] = v
	}
	if getBool(f, "creates_join_request") {
		body["creates_join_request"] = true
	}
	r, err := s.call("createChatInviteLink", body)
	if err != nil {
		return nil, err
	}
	return wrap(r)
}

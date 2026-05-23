package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"

	"google.golang.org/protobuf/types/known/structpb"
)

// SlackService proxies the Slack Web API. Authentication is via a bot token
// (xoxb-...) supplied in SLACK_BOT_TOKEN. The base URL can be overridden with
// SLACK_BASE_URL for testing against a mock server.
type SlackService struct {
	baseURL string
	token   string
	client  *http.Client
}

func NewSlackService() *SlackService {
	base := os.Getenv("SLACK_BASE_URL")
	if base == "" {
		base = "https://slack.com/api"
	}
	return &SlackService{
		baseURL: strings.TrimRight(base, "/"),
		token:   os.Getenv("SLACK_BOT_TOKEN"),
		client:  &http.Client{},
	}
}

// callForm calls a Slack Web API method with x-www-form-urlencoded params.
// Used for read endpoints that accept query/form params.
func (s *SlackService) callForm(method string, params url.Values) (map[string]any, error) {
	if s.token == "" {
		return nil, fmt.Errorf("SLACK_BOT_TOKEN is not set")
	}
	endpoint := fmt.Sprintf("%s/%s", s.baseURL, method)
	req, err := http.NewRequest("POST", endpoint, strings.NewReader(params.Encode()))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.token)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
	req.Header.Set("Accept", "application/json")
	return s.do(req, method)
}

// callJSON calls a Slack Web API method with a JSON body.
// Used for write endpoints (chat.postMessage etc.) that accept rich payloads
// like blocks/attachments.
func (s *SlackService) callJSON(method string, body map[string]any) (map[string]any, error) {
	if s.token == "" {
		return nil, fmt.Errorf("SLACK_BOT_TOKEN is not set")
	}
	endpoint := fmt.Sprintf("%s/%s", s.baseURL, method)
	buf, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("encode body: %w", err)
	}
	req, err := http.NewRequest("POST", endpoint, strings.NewReader(string(buf)))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.token)
	req.Header.Set("Content-Type", "application/json; charset=utf-8")
	req.Header.Set("Accept", "application/json")
	return s.do(req, method)
}

func (s *SlackService) do(req *http.Request, method string) (map[string]any, error) {
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
		return nil, fmt.Errorf("slack %s returned %d: %s", method, resp.StatusCode, string(raw))
	}
	var out map[string]any
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, fmt.Errorf("decode body: %w (raw: %s)", err, string(raw))
	}
	return out, nil
}

// -- request helpers --

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

func getInt(fields map[string]*structpb.Value, key string) int {
	if v, ok := fields[key]; ok {
		return int(v.GetNumberValue())
	}
	return 0
}

func getStruct(fields map[string]*structpb.Value, key string) *structpb.Struct {
	if v, ok := fields[key]; ok {
		return v.GetStructValue()
	}
	return nil
}

// addStr puts a non-empty string into the form values.
func addStr(v url.Values, key, val string) {
	if val != "" {
		v.Set(key, val)
	}
}

// addBool puts a bool into form values (only if true, since Slack treats
// presence-of-key as true).
func addBool(v url.Values, key string, val bool) {
	if val {
		v.Set(key, "true")
	}
}

// addInt puts a non-zero int into form values.
func addInt(v url.Values, key string, val int) {
	if val > 0 {
		v.Set(key, strconv.Itoa(val))
	}
}

func addInt64(v url.Values, key string, val int64) {
	if val > 0 {
		v.Set(key, strconv.FormatInt(val, 10))
	}
}

// putJSONStruct puts a structpb.Struct as a JSON string into form values.
// Slack accepts blocks/attachments/view as JSON strings when sent via form.
func putJSONStruct(v url.Values, key string, s *structpb.Struct) error {
	if s == nil || len(s.Fields) == 0 {
		return nil
	}
	b, err := json.Marshal(s.AsMap())
	if err != nil {
		return fmt.Errorf("encode %s: %w", key, err)
	}
	v.Set(key, string(b))
	return nil
}

// toStruct converts a map to a structpb.Struct, replacing nested types that
// aren't natively supported (lists, nested maps already work).
func toStruct(data map[string]any) (*structpb.Struct, error) {
	return structpb.NewStruct(normalize(data).(map[string]any))
}

// normalize walks the value, replacing types not supported by structpb
// (only json.Number really matters in practice; everything else is fine).
func normalize(v any) any {
	switch x := v.(type) {
	case map[string]any:
		out := make(map[string]any, len(x))
		for k, val := range x {
			out[k] = normalize(val)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, val := range x {
			out[i] = normalize(val)
		}
		return out
	case json.Number:
		if i, err := x.Int64(); err == nil {
			return float64(i)
		}
		if f, err := x.Float64(); err == nil {
			return f
		}
		return x.String()
	default:
		return v
	}
}

// -- RPC handlers --

func (s *SlackService) AuthTest(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.callForm("auth.test", url.Values{})
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatPostMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if c := getStr(f, "channel"); c != "" {
		body["channel"] = c
	}
	if t := getStr(f, "text"); t != "" {
		body["text"] = t
	}
	if ts := getStr(f, "thread_ts"); ts != "" {
		body["thread_ts"] = ts
	}
	if b := getStruct(f, "blocks"); b != nil && len(b.Fields) > 0 {
		body["blocks"] = b.AsMap()
	}
	if a := getStruct(f, "attachments"); a != nil && len(a.Fields) > 0 {
		body["attachments"] = a.AsMap()
	}
	if getBool(f, "reply_broadcast") {
		body["reply_broadcast"] = true
	}
	if u := getStr(f, "username"); u != "" {
		body["username"] = u
	}
	if iu := getStr(f, "icon_url"); iu != "" {
		body["icon_url"] = iu
	}
	if ie := getStr(f, "icon_emoji"); ie != "" {
		body["icon_emoji"] = ie
	}
	if p := getStr(f, "parse"); p != "" {
		body["parse"] = p
	}
	if getBool(f, "mrkdwn") {
		body["mrkdwn"] = true
	}
	if getBool(f, "unfurl_links") {
		body["unfurl_links"] = true
	}
	if getBool(f, "unfurl_media") {
		body["unfurl_media"] = true
	}
	if m := getStruct(f, "metadata"); m != nil && len(m.Fields) > 0 {
		body["metadata"] = m.AsMap()
	}
	data, err := s.callJSON("chat.postMessage", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatPostEphemeral(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"user":    getStr(f, "user"),
	}
	if t := getStr(f, "text"); t != "" {
		body["text"] = t
	}
	if b := getStruct(f, "blocks"); b != nil && len(b.Fields) > 0 {
		body["blocks"] = b.AsMap()
	}
	if a := getStruct(f, "attachments"); a != nil && len(a.Fields) > 0 {
		body["attachments"] = a.AsMap()
	}
	if ts := getStr(f, "thread_ts"); ts != "" {
		body["thread_ts"] = ts
	}
	if p := getStr(f, "parse"); p != "" {
		body["parse"] = p
	}
	data, err := s.callJSON("chat.postEphemeral", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatUpdate(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"ts":      getStr(f, "ts"),
	}
	if t := getStr(f, "text"); t != "" {
		body["text"] = t
	}
	if b := getStruct(f, "blocks"); b != nil && len(b.Fields) > 0 {
		body["blocks"] = b.AsMap()
	}
	if a := getStruct(f, "attachments"); a != nil && len(a.Fields) > 0 {
		body["attachments"] = a.AsMap()
	}
	if p := getStr(f, "parse"); p != "" {
		body["parse"] = p
	}
	data, err := s.callJSON("chat.update", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatDelete(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"ts":      getStr(f, "ts"),
	}
	if getBool(f, "as_user") {
		body["as_user"] = true
	}
	data, err := s.callJSON("chat.delete", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatScheduleMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"post_at": int64(getInt(f, "post_at")),
	}
	if t := getStr(f, "text"); t != "" {
		body["text"] = t
	}
	if b := getStruct(f, "blocks"); b != nil && len(b.Fields) > 0 {
		body["blocks"] = b.AsMap()
	}
	if a := getStruct(f, "attachments"); a != nil && len(a.Fields) > 0 {
		body["attachments"] = a.AsMap()
	}
	if ts := getStr(f, "thread_ts"); ts != "" {
		body["thread_ts"] = ts
	}
	if getBool(f, "reply_broadcast") {
		body["reply_broadcast"] = true
	}
	data, err := s.callJSON("chat.scheduleMessage", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatDeleteScheduledMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "scheduled_message_id", getStr(f, "scheduled_message_id"))
	data, err := s.callForm("chat.deleteScheduledMessage", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ChatGetPermalink(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "message_ts", getStr(f, "message_ts"))
	data, err := s.callForm("chat.getPermalink", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "types", getStr(f, "types"))
	addBool(v, "exclude_archived", getBool(f, "exclude_archived"))
	addInt(v, "limit", getInt(f, "limit"))
	addStr(v, "cursor", getStr(f, "cursor"))
	data, err := s.callForm("conversations.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsHistory(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addInt(v, "limit", getInt(f, "limit"))
	addStr(v, "cursor", getStr(f, "cursor"))
	addStr(v, "oldest", getStr(f, "oldest"))
	addStr(v, "latest", getStr(f, "latest"))
	addBool(v, "inclusive", getBool(f, "inclusive"))
	data, err := s.callForm("conversations.history", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsReplies(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "ts", getStr(f, "ts"))
	addInt(v, "limit", getInt(f, "limit"))
	addStr(v, "cursor", getStr(f, "cursor"))
	addStr(v, "oldest", getStr(f, "oldest"))
	addStr(v, "latest", getStr(f, "latest"))
	addBool(v, "inclusive", getBool(f, "inclusive"))
	data, err := s.callForm("conversations.replies", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addBool(v, "include_locale", getBool(f, "include_locale"))
	addBool(v, "include_num_members", getBool(f, "include_num_members"))
	data, err := s.callForm("conversations.info", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsCreate(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"name": getStr(f, "name"),
	}
	if getBool(f, "is_private") {
		body["is_private"] = true
	}
	if id := getStr(f, "team_id"); id != "" {
		body["team_id"] = id
	}
	data, err := s.callJSON("conversations.create", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsJoin(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	data, err := s.callForm("conversations.join", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsLeave(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	data, err := s.callForm("conversations.leave", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsInvite(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"users":   getStr(f, "users"),
	}
	if getBool(f, "force") {
		body["force"] = true
	}
	data, err := s.callJSON("conversations.invite", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsKick(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "user", getStr(f, "user"))
	data, err := s.callForm("conversations.kick", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsArchive(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	data, err := s.callForm("conversations.archive", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsUnarchive(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	data, err := s.callForm("conversations.unarchive", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsRename(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "name", getStr(f, "name"))
	data, err := s.callForm("conversations.rename", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsSetTopic(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"topic":   getStr(f, "topic"),
	}
	data, err := s.callJSON("conversations.setTopic", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsSetPurpose(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel": getStr(f, "channel"),
		"purpose": getStr(f, "purpose"),
	}
	data, err := s.callJSON("conversations.setPurpose", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsMembers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addInt(v, "limit", getInt(f, "limit"))
	addStr(v, "cursor", getStr(f, "cursor"))
	data, err := s.callForm("conversations.members", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ConversationsOpen(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if u := getStr(f, "users"); u != "" {
		body["users"] = u
	}
	if c := getStr(f, "channel"); c != "" {
		body["channel"] = c
	}
	if getBool(f, "return_im") {
		body["return_im"] = true
	}
	data, err := s.callJSON("conversations.open", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) UsersList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addInt(v, "limit", getInt(f, "limit"))
	addStr(v, "cursor", getStr(f, "cursor"))
	addBool(v, "include_locale", getBool(f, "include_locale"))
	data, err := s.callForm("users.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) UsersInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "user", getStr(f, "user"))
	addBool(v, "include_locale", getBool(f, "include_locale"))
	data, err := s.callForm("users.info", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) UsersLookupByEmail(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "email", getStr(f, "email"))
	data, err := s.callForm("users.lookupByEmail", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) UsersProfileGet(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "user", getStr(f, "user"))
	addBool(v, "include_labels", getBool(f, "include_labels"))
	data, err := s.callForm("users.profile.get", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) UsersGetPresence(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "user", getStr(f, "user"))
	data, err := s.callForm("users.getPresence", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ReactionsAdd(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "name", getStr(f, "name"))
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "timestamp", getStr(f, "timestamp"))
	data, err := s.callForm("reactions.add", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ReactionsRemove(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "name", getStr(f, "name"))
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "timestamp", getStr(f, "timestamp"))
	data, err := s.callForm("reactions.remove", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ReactionsGet(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "timestamp", getStr(f, "timestamp"))
	addBool(v, "full", getBool(f, "full"))
	data, err := s.callForm("reactions.get", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) PinsAdd(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "timestamp", getStr(f, "timestamp"))
	data, err := s.callForm("pins.add", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) PinsRemove(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "timestamp", getStr(f, "timestamp"))
	data, err := s.callForm("pins.remove", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) PinsList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel", getStr(f, "channel"))
	data, err := s.callForm("pins.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) SearchMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "query", getStr(f, "query"))
	addStr(v, "sort", getStr(f, "sort"))
	addStr(v, "sort_dir", getStr(f, "sort_dir"))
	addInt(v, "count", getInt(f, "count"))
	addInt(v, "page", getInt(f, "page"))
	addBool(v, "highlight", getBool(f, "highlight"))
	data, err := s.callForm("search.messages", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) SearchFiles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "query", getStr(f, "query"))
	addStr(v, "sort", getStr(f, "sort"))
	addStr(v, "sort_dir", getStr(f, "sort_dir"))
	addInt(v, "count", getInt(f, "count"))
	addInt(v, "page", getInt(f, "page"))
	data, err := s.callForm("search.files", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) FilesList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "user", getStr(f, "user"))
	addStr(v, "channel", getStr(f, "channel"))
	addStr(v, "types", getStr(f, "types"))
	addInt64(v, "ts_from", int64(getInt(f, "ts_from")))
	addInt64(v, "ts_to", int64(getInt(f, "ts_to")))
	addInt(v, "count", getInt(f, "count"))
	addInt(v, "page", getInt(f, "page"))
	data, err := s.callForm("files.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) FilesInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "file", getStr(f, "file"))
	addInt(v, "count", getInt(f, "count"))
	addInt(v, "page", getInt(f, "page"))
	data, err := s.callForm("files.info", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) FilesDelete(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "file", getStr(f, "file"))
	data, err := s.callForm("files.delete", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) BookmarksList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "channel_id", getStr(f, "channel_id"))
	data, err := s.callForm("bookmarks.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) BookmarksAdd(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel_id": getStr(f, "channel_id"),
		"title":      getStr(f, "title"),
		"type":       getStr(f, "type"),
	}
	if l := getStr(f, "link"); l != "" {
		body["link"] = l
	}
	if e := getStr(f, "emoji"); e != "" {
		body["emoji"] = e
	}
	if id := getStr(f, "entity_id"); id != "" {
		body["entity_id"] = id
	}
	data, err := s.callJSON("bookmarks.add", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) BookmarksRemove(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"channel_id":  getStr(f, "channel_id"),
		"bookmark_id": getStr(f, "bookmark_id"),
	}
	data, err := s.callJSON("bookmarks.remove", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) TeamInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addStr(v, "team", getStr(f, "team"))
	data, err := s.callForm("team.info", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) EmojiList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v := url.Values{}
	addBool(v, "include_categories", getBool(f, "include_categories"))
	data, err := s.callForm("emoji.list", v)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ViewsOpen(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"trigger_id": getStr(f, "trigger_id"),
	}
	if view := getStruct(f, "view"); view != nil && len(view.Fields) > 0 {
		body["view"] = view.AsMap()
	}
	data, err := s.callJSON("views.open", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

func (s *SlackService) ViewsPublish(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{
		"user_id": getStr(f, "user_id"),
	}
	if view := getStruct(f, "view"); view != nil && len(view.Fields) > 0 {
		body["view"] = view.AsMap()
	}
	if h := getStr(f, "hash"); h != "" {
		body["hash"] = h
	}
	data, err := s.callJSON("views.publish", body)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

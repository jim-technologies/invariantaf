package main

import (
	"bytes"
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

// DiscordService proxies the Discord HTTP REST API. Authentication is via a
// bot token (DISCORD_BOT_TOKEN) sent as Authorization: Bot <token>.
//
// Most write endpoints accept a free-form body — we pass it through as
// google.protobuf.Struct so callers stay in sync with whatever Discord adds.
// Responses are returned as Struct for the same reason.
type DiscordService struct {
	baseURL string
	token   string
	client  *http.Client
}

func NewDiscordService() *DiscordService {
	base := os.Getenv("DISCORD_BASE_URL")
	if base == "" {
		base = "https://discord.com/api/v10"
	}
	return &DiscordService{
		baseURL: strings.TrimRight(base, "/"),
		token:   os.Getenv("DISCORD_BOT_TOKEN"),
		client:  &http.Client{},
	}
}

// -- core HTTP --

// request builds and executes a Discord REST request. The path is appended to
// the configured base URL. body, when non-nil, is JSON-encoded.
// Reason, when non-empty, is sent as X-Audit-Log-Reason.
// requireAuth toggles whether DISCORD_BOT_TOKEN is required.
func (s *DiscordService) request(
	method, path string,
	query url.Values,
	body any,
	reason string,
	requireAuth bool,
) (any, error) {
	if requireAuth && s.token == "" {
		return nil, fmt.Errorf("DISCORD_BOT_TOKEN is not set")
	}
	u := s.baseURL + path
	if len(query) > 0 {
		u += "?" + query.Encode()
	}
	var reqBody io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("encode body: %w", err)
		}
		reqBody = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, u, reqBody)
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	if requireAuth {
		req.Header.Set("Authorization", "Bot "+s.token)
	}
	req.Header.Set("User-Agent", "invariantaf-discord/0.1")
	req.Header.Set("Accept", "application/json")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if reason != "" {
		req.Header.Set("X-Audit-Log-Reason", reason)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http %s %s: %w", method, path, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("discord %s %s returned %d: %s", method, path, resp.StatusCode, string(raw))
	}
	if len(raw) == 0 || resp.StatusCode == http.StatusNoContent {
		return map[string]any{"status": resp.StatusCode}, nil
	}
	var out any
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, fmt.Errorf("decode body: %w (raw: %s)", err, string(raw))
	}
	return out, nil
}

// wrap normalizes a Discord response into a structpb.Struct.
// Discord sometimes returns an array — we wrap it as {"items": [...]} so callers
// always get a Struct.
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

func getList(fields map[string]*structpb.Value, key string) *structpb.ListValue {
	if v, ok := fields[key]; ok {
		return v.GetListValue()
	}
	return nil
}

func structToMap(s *structpb.Struct) map[string]any {
	if s == nil {
		return nil
	}
	return s.AsMap()
}

func setQuery(q url.Values, key, val string) {
	if val != "" {
		q.Set(key, val)
	}
}

func setQueryInt(q url.Values, key string, val int) {
	if val > 0 {
		q.Set(key, strconv.Itoa(val))
	}
}

func setQueryBool(q url.Values, key string, val bool) {
	if val {
		q.Set(key, "true")
	}
}

// urlEmoji URL-encodes a Discord emoji for path use.
func urlEmoji(emoji string) string {
	return url.PathEscape(emoji)
}

// -- RPC handlers (users) --

func (s *DiscordService) GetCurrentUser(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	v, err := s.request("GET", "/users/@me", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetUser(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/users/"+getStr(f, "user_id"), nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetCurrentUserGuilds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQuery(q, "before", getStr(f, "before"))
	setQuery(q, "after", getStr(f, "after"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	setQueryBool(q, "with_counts", getBool(f, "with_counts"))
	v, err := s.request("GET", "/users/@me/guilds", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) LeaveGuild(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("DELETE", "/users/@me/guilds/"+getStr(f, "guild_id"), nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateDM(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{"recipient_id": getStr(f, "recipient_id")}
	v, err := s.request("POST", "/users/@me/channels", nil, body, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- guilds --

func (s *DiscordService) GetGuild(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQueryBool(q, "with_counts", getBool(f, "with_counts"))
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id"), q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildPreview(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/preview", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ModifyGuild(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PATCH",
		"/guilds/"+getStr(f, "guild_id"),
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildChannels(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/channels", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateGuildChannel(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/guilds/"+getStr(f, "guild_id")+"/channels",
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ListGuildMembers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQueryInt(q, "limit", getInt(f, "limit"))
	setQuery(q, "after", getStr(f, "after"))
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/members", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) SearchGuildMembers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQuery(q, "query", getStr(f, "query"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/members/search", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"GET",
		"/guilds/"+getStr(f, "guild_id")+"/members/"+getStr(f, "user_id"),
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ModifyGuildMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PATCH",
		"/guilds/"+getStr(f, "guild_id")+"/members/"+getStr(f, "user_id"),
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) RemoveGuildMember(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/guilds/"+getStr(f, "guild_id")+"/members/"+getStr(f, "user_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateGuildBan(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	body := map[string]any{}
	if d := getInt(f, "delete_message_seconds"); d > 0 {
		body["delete_message_seconds"] = d
	}
	v, err := s.request(
		"PUT",
		"/guilds/"+getStr(f, "guild_id")+"/bans/"+getStr(f, "user_id"),
		nil, body, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) RemoveGuildBan(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/guilds/"+getStr(f, "guild_id")+"/bans/"+getStr(f, "user_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildBans(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQueryInt(q, "limit", getInt(f, "limit"))
	setQuery(q, "before", getStr(f, "before"))
	setQuery(q, "after", getStr(f, "after"))
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/bans", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildRoles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/roles", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateGuildRole(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/guilds/"+getStr(f, "guild_id")+"/roles",
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ModifyGuildRole(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PATCH",
		"/guilds/"+getStr(f, "guild_id")+"/roles/"+getStr(f, "role_id"),
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteGuildRole(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/guilds/"+getStr(f, "guild_id")+"/roles/"+getStr(f, "role_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) AddGuildMemberRole(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PUT",
		"/guilds/"+getStr(f, "guild_id")+"/members/"+getStr(f, "user_id")+"/roles/"+getStr(f, "role_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) RemoveGuildMemberRole(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/guilds/"+getStr(f, "guild_id")+"/members/"+getStr(f, "user_id")+"/roles/"+getStr(f, "role_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildInvites(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/invites", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ListGuildEmojis(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/emojis", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGuildAuditLog(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQuery(q, "user_id", getStr(f, "user_id"))
	if at := getInt(f, "action_type"); at > 0 {
		q.Set("action_type", strconv.Itoa(at))
	}
	setQuery(q, "before", getStr(f, "before"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	v, err := s.request("GET", "/guilds/"+getStr(f, "guild_id")+"/audit-logs", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- channels & messages --

func (s *DiscordService) GetChannel(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/channels/"+getStr(f, "channel_id"), nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ModifyChannel(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PATCH",
		"/channels/"+getStr(f, "channel_id"),
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteChannel(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/channels/"+getStr(f, "channel_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetChannelMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQuery(q, "around", getStr(f, "around"))
	setQuery(q, "before", getStr(f, "before"))
	setQuery(q, "after", getStr(f, "after"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	v, err := s.request("GET", "/channels/"+getStr(f, "channel_id")+"/messages", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetChannelMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"GET",
		"/channels/"+getStr(f, "channel_id")+"/messages/"+getStr(f, "message_id"),
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/messages",
		nil,
		structToMap(getStruct(f, "body")),
		"",
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) EditMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PATCH",
		"/channels/"+getStr(f, "channel_id")+"/messages/"+getStr(f, "message_id"),
		nil,
		structToMap(getStruct(f, "body")),
		"",
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/channels/"+getStr(f, "channel_id")+"/messages/"+getStr(f, "message_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CrosspostMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/messages/"+getStr(f, "message_id")+"/crosspost",
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) BulkDeleteMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	idsList := getList(f, "message_ids")
	ids := make([]string, 0)
	if idsList != nil {
		for _, val := range idsList.Values {
			ids = append(ids, val.GetStringValue())
		}
	}
	body := map[string]any{"messages": ids}
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/messages/bulk-delete",
		nil, body, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- reactions --

func (s *DiscordService) CreateReaction(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	path := fmt.Sprintf(
		"/channels/%s/messages/%s/reactions/%s/@me",
		getStr(f, "channel_id"), getStr(f, "message_id"), urlEmoji(getStr(f, "emoji")),
	)
	v, err := s.request("PUT", path, nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteOwnReaction(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	path := fmt.Sprintf(
		"/channels/%s/messages/%s/reactions/%s/@me",
		getStr(f, "channel_id"), getStr(f, "message_id"), urlEmoji(getStr(f, "emoji")),
	)
	v, err := s.request("DELETE", path, nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteUserReaction(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	path := fmt.Sprintf(
		"/channels/%s/messages/%s/reactions/%s/%s",
		getStr(f, "channel_id"), getStr(f, "message_id"), urlEmoji(getStr(f, "emoji")), getStr(f, "user_id"),
	)
	v, err := s.request("DELETE", path, nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetReactions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQuery(q, "after", getStr(f, "after"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	path := fmt.Sprintf(
		"/channels/%s/messages/%s/reactions/%s",
		getStr(f, "channel_id"), getStr(f, "message_id"), urlEmoji(getStr(f, "emoji")),
	)
	v, err := s.request("GET", path, q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteAllReactions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	path := fmt.Sprintf(
		"/channels/%s/messages/%s/reactions",
		getStr(f, "channel_id"), getStr(f, "message_id"),
	)
	if emoji := getStr(f, "emoji"); emoji != "" {
		path += "/" + urlEmoji(emoji)
	}
	v, err := s.request("DELETE", path, nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- channel ops --

func (s *DiscordService) TriggerTypingIndicator(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/typing",
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetPinnedMessages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/channels/"+getStr(f, "channel_id")+"/pins", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) PinMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PUT",
		"/channels/"+getStr(f, "channel_id")+"/pins/"+getStr(f, "message_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) UnpinMessage(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/channels/"+getStr(f, "channel_id")+"/pins/"+getStr(f, "message_id"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) CreateChannelInvite(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/invites",
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetChannelInvites(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request("GET", "/channels/"+getStr(f, "channel_id")+"/invites", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- threads --

func (s *DiscordService) StartThread(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"POST",
		"/channels/"+getStr(f, "channel_id")+"/threads",
		nil,
		structToMap(getStruct(f, "body")),
		getStr(f, "reason"),
		true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) JoinThread(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"PUT",
		"/channels/"+getStr(f, "channel_id")+"/thread-members/@me",
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) LeaveThread(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/channels/"+getStr(f, "channel_id")+"/thread-members/@me",
		nil, nil, "", true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) ListThreadMembers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQueryBool(q, "with_member", getBool(f, "with_member"))
	setQuery(q, "after", getStr(f, "after"))
	setQueryInt(q, "limit", getInt(f, "limit"))
	v, err := s.request("GET", "/channels/"+getStr(f, "channel_id")+"/thread-members", q, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

// -- webhooks & misc --

func (s *DiscordService) ExecuteWebhook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	q := url.Values{}
	setQueryBool(q, "wait", getBool(f, "wait"))
	setQuery(q, "thread_id", getStr(f, "thread_id"))
	v, err := s.request(
		"POST",
		"/webhooks/"+getStr(f, "webhook_id")+"/"+getStr(f, "webhook_token"),
		q,
		structToMap(getStruct(f, "body")),
		"",
		false, // webhook executes without bot auth
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) DeleteInvite(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	f := req.GetFields()
	v, err := s.request(
		"DELETE",
		"/invites/"+getStr(f, "invite_code"),
		nil, nil, getStr(f, "reason"), true,
	)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGateway(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	v, err := s.request("GET", "/gateway", nil, nil, "", false)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

func (s *DiscordService) GetGatewayBot(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	v, err := s.request("GET", "/gateway/bot", nil, nil, "", true)
	if err != nil {
		return nil, err
	}
	return wrap(v)
}

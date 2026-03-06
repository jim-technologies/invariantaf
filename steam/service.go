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

const defaultSteamBaseURL = "https://api.steampowered.com"
const defaultStoreBaseURL = "https://store.steampowered.com"

// SteamService implements all 10 RPCs of steam.v1.SteamService.
type SteamService struct {
	apiKey       string
	client       *http.Client
	steamBaseURL string
	storeBaseURL string
}

// NewSteamService creates a SteamService using STEAM_API_KEY from the environment.
func NewSteamService() *SteamService {
	return &SteamService{
		apiKey:       os.Getenv("STEAM_API_KEY"),
		client:       &http.Client{},
		steamBaseURL: defaultSteamBaseURL,
		storeBaseURL: defaultStoreBaseURL,
	}
}

// get performs an HTTP GET and decodes the JSON response body.
func (s *SteamService) get(url string) (map[string]any, error) {
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("http get: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("steam api returned status %d: %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

// GetPlayerSummaries retrieves profile info for one or more Steam players.
func (s *SteamService) GetPlayerSummaries(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	steamIDs := req.GetFields()["steam_ids"].GetStringValue()
	if steamIDs == "" {
		return nil, fmt.Errorf("steam_ids is required")
	}

	u := fmt.Sprintf("%s/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s",
		s.steamBaseURL, s.apiKey, url.QueryEscape(steamIDs))

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	response, _ := traverse(raw, "response")
	playersRaw, _ := traverseList(response, "players")

	var players []any
	for _, p := range playersRaw {
		pm, ok := p.(map[string]any)
		if !ok {
			continue
		}
		player := map[string]any{
			"steam_id":                   getString(pm, "steamid"),
			"persona_name":               getString(pm, "personaname"),
			"profile_url":                getString(pm, "profileurl"),
			"avatar":                     getString(pm, "avatar"),
			"avatar_medium":              getString(pm, "avatarmedium"),
			"avatar_full":                getString(pm, "avatarfull"),
			"persona_state":              getNumber(pm, "personastate"),
			"community_visibility_state": getNumber(pm, "communityvisibilitystate"),
			"last_logoff":                getNumber(pm, "lastlogoff"),
			"country_code":               getString(pm, "loccountrycode"),
			"time_created":               getNumber(pm, "timecreated"),
			"game_id":                    getString(pm, "gameid"),
			"game_extra_info":            getString(pm, "gameextrainfo"),
		}
		players = append(players, player)
	}

	return structpb.NewStruct(map[string]any{
		"players": players,
	})
}

// GetOwnedGames retrieves the games owned by a player.
func (s *SteamService) GetOwnedGames(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	steamID := fields["steam_id"].GetStringValue()
	if steamID == "" {
		return nil, fmt.Errorf("steam_id is required")
	}

	params := url.Values{}
	params.Set("key", s.apiKey)
	params.Set("steamid", steamID)
	params.Set("format", "json")

	if fields["include_appinfo"].GetBoolValue() {
		params.Set("include_appinfo", "1")
	}
	if fields["include_played_free_games"].GetBoolValue() {
		params.Set("include_played_free_games", "1")
	}

	u := fmt.Sprintf("%s/IPlayerService/GetOwnedGames/v0001/?%s", s.steamBaseURL, params.Encode())

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	response, _ := traverse(raw, "response")
	gameCount := getNumber(response, "game_count")
	gamesRaw, _ := traverseList(response, "games")

	var games []any
	for _, g := range gamesRaw {
		gm, ok := g.(map[string]any)
		if !ok {
			continue
		}
		game := map[string]any{
			"app_id":           getNumber(gm, "appid"),
			"name":             getString(gm, "name"),
			"playtime_forever": getNumber(gm, "playtime_forever"),
			"playtime_2weeks":  getNumber(gm, "playtime_2weeks"),
			"img_icon_url":     getString(gm, "img_icon_url"),
		}
		games = append(games, game)
	}

	return structpb.NewStruct(map[string]any{
		"game_count": gameCount,
		"games":      games,
	})
}

// GetRecentlyPlayedGames retrieves recently played games for a player.
func (s *SteamService) GetRecentlyPlayedGames(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	steamID := fields["steam_id"].GetStringValue()
	if steamID == "" {
		return nil, fmt.Errorf("steam_id is required")
	}

	params := url.Values{}
	params.Set("key", s.apiKey)
	params.Set("steamid", steamID)
	params.Set("format", "json")

	if count := fields["count"].GetNumberValue(); count > 0 {
		params.Set("count", strconv.Itoa(int(count)))
	}

	u := fmt.Sprintf("%s/IPlayerService/GetRecentlyPlayedGames/v0001/?%s", s.steamBaseURL, params.Encode())

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	response, _ := traverse(raw, "response")
	totalCount := getNumber(response, "total_count")
	gamesRaw, _ := traverseList(response, "games")

	var games []any
	for _, g := range gamesRaw {
		gm, ok := g.(map[string]any)
		if !ok {
			continue
		}
		game := map[string]any{
			"app_id":           getNumber(gm, "appid"),
			"name":             getString(gm, "name"),
			"playtime_2weeks":  getNumber(gm, "playtime_2weeks"),
			"playtime_forever": getNumber(gm, "playtime_forever"),
			"img_icon_url":     getString(gm, "img_icon_url"),
		}
		games = append(games, game)
	}

	return structpb.NewStruct(map[string]any{
		"total_count": totalCount,
		"games":       games,
	})
}

// GetPlayerAchievements retrieves a player's achievements for a specific game.
func (s *SteamService) GetPlayerAchievements(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	steamID := fields["steam_id"].GetStringValue()
	appID := int(fields["app_id"].GetNumberValue())
	if steamID == "" {
		return nil, fmt.Errorf("steam_id is required")
	}
	if appID == 0 {
		return nil, fmt.Errorf("app_id is required")
	}

	params := url.Values{}
	params.Set("key", s.apiKey)
	params.Set("steamid", steamID)
	params.Set("appid", strconv.Itoa(appID))

	lang := fields["language"].GetStringValue()
	if lang == "" {
		lang = "en"
	}
	params.Set("l", lang)

	u := fmt.Sprintf("%s/ISteamUserStats/GetPlayerAchievements/v0001/?%s", s.steamBaseURL, params.Encode())

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	stats, _ := traverse(raw, "playerstats")
	gameName := getString(stats, "gameName")
	respSteamID := getString(stats, "steamID")
	success := getBool(stats, "success")
	achievementsRaw, _ := traverseList(stats, "achievements")

	var achievements []any
	for _, a := range achievementsRaw {
		am, ok := a.(map[string]any)
		if !ok {
			continue
		}
		achieved := getNumber(am, "achieved") == 1.0
		achievement := map[string]any{
			"api_name":    getString(am, "apiname"),
			"achieved":    achieved,
			"unlock_time": getNumber(am, "unlocktime"),
			"name":        getString(am, "name"),
			"description": getString(am, "description"),
		}
		achievements = append(achievements, achievement)
	}

	return structpb.NewStruct(map[string]any{
		"game_name":    gameName,
		"steam_id":     respSteamID,
		"success":      success,
		"achievements": achievements,
	})
}

// GetAppDetails retrieves detailed metadata about a Steam app from the Store API.
func (s *SteamService) GetAppDetails(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	appID := int(req.GetFields()["app_id"].GetNumberValue())
	if appID == 0 {
		return nil, fmt.Errorf("app_id is required")
	}

	appIDStr := strconv.Itoa(appID)
	u := fmt.Sprintf("%s/api/appdetails?appids=%s", s.storeBaseURL, appIDStr)

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	appData, ok := raw[appIDStr].(map[string]any)
	if !ok {
		return structpb.NewStruct(map[string]any{"success": false})
	}

	success := getBool(appData, "success")
	if !success {
		return structpb.NewStruct(map[string]any{"success": false})
	}

	data, _ := traverse(appData, "data")

	// Extract genres
	var genres []any
	if genresRaw, ok := data["genres"].([]any); ok {
		for _, g := range genresRaw {
			gm, ok := g.(map[string]any)
			if !ok {
				continue
			}
			genres = append(genres, map[string]any{
				"id":          getString(gm, "id"),
				"description": getString(gm, "description"),
			})
		}
	}

	// Extract platforms
	var platforms map[string]any
	if pm, ok := data["platforms"].(map[string]any); ok {
		platforms = map[string]any{
			"windows": getBool(pm, "windows"),
			"mac":     getBool(pm, "mac"),
			"linux":   getBool(pm, "linux"),
		}
	}

	// Extract price
	var priceOverview map[string]any
	if po, ok := data["price_overview"].(map[string]any); ok {
		priceOverview = map[string]any{
			"currency":          getString(po, "currency"),
			"initial":           getNumber(po, "initial"),
			"final":             getNumber(po, "final"),
			"discount_percent":  getNumber(po, "discount_percent"),
			"initial_formatted": getString(po, "initial_formatted"),
			"final_formatted":   getString(po, "final_formatted"),
		}
	}

	// Extract metacritic
	var metacritic map[string]any
	if mc, ok := data["metacritic"].(map[string]any); ok {
		metacritic = map[string]any{
			"score": getNumber(mc, "score"),
			"url":   getString(mc, "url"),
		}
	}

	// Extract developers and publishers
	developers := getStringSlice(data, "developers")
	publishers := getStringSlice(data, "publishers")

	// Recommendations
	var recommendations float64
	if rec, ok := data["recommendations"].(map[string]any); ok {
		recommendations = getNumber(rec, "total")
	}

	// Release date
	var releaseDate string
	if rd, ok := data["release_date"].(map[string]any); ok {
		releaseDate = getString(rd, "date")
	}

	result := map[string]any{
		"success": true,
		"data": map[string]any{
			"app_id":               float64(appID),
			"type":                 getString(data, "type"),
			"name":                 getString(data, "name"),
			"short_description":    getString(data, "short_description"),
			"detailed_description": getString(data, "detailed_description"),
			"developers":           developers,
			"publishers":           publishers,
			"is_free":              getBool(data, "is_free"),
			"header_image":         getString(data, "header_image"),
			"website":              getString(data, "website"),
			"release_date":         releaseDate,
			"recommendations":      recommendations,
		},
	}

	if platforms != nil {
		result["data"].(map[string]any)["platforms"] = platforms
	}
	if priceOverview != nil {
		result["data"].(map[string]any)["price_overview"] = priceOverview
	}
	if metacritic != nil {
		result["data"].(map[string]any)["metacritic"] = metacritic
	}
	if genres != nil {
		result["data"].(map[string]any)["genres"] = genres
	}

	return structpb.NewStruct(result)
}

// GetAppList retrieves the complete list of all Steam apps.
func (s *SteamService) GetAppList(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	u := fmt.Sprintf("%s/ISteamApps/GetAppList/v0002/", s.steamBaseURL)

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	appList, _ := traverse(raw, "applist")
	appsRaw, _ := traverseList(appList, "apps")

	var apps []any
	for _, a := range appsRaw {
		am, ok := a.(map[string]any)
		if !ok {
			continue
		}
		apps = append(apps, map[string]any{
			"app_id": getNumber(am, "appid"),
			"name":   getString(am, "name"),
		})
	}

	return structpb.NewStruct(map[string]any{
		"apps": apps,
	})
}

// GetNumberOfCurrentPlayers retrieves the current player count for an app.
func (s *SteamService) GetNumberOfCurrentPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	appID := int(req.GetFields()["app_id"].GetNumberValue())
	if appID == 0 {
		return nil, fmt.Errorf("app_id is required")
	}

	u := fmt.Sprintf("%s/ISteamUserStats/GetNumberOfCurrentPlayers/v0001/?appid=%d",
		s.steamBaseURL, appID)

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	response, _ := traverse(raw, "response")
	playerCount := getNumber(response, "player_count")

	return structpb.NewStruct(map[string]any{
		"player_count": playerCount,
	})
}

// GetFriendList retrieves a player's friend list.
func (s *SteamService) GetFriendList(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	steamID := req.GetFields()["steam_id"].GetStringValue()
	if steamID == "" {
		return nil, fmt.Errorf("steam_id is required")
	}

	u := fmt.Sprintf("%s/ISteamUser/GetFriendList/v0001/?key=%s&steamid=%s&relationship=friend",
		s.steamBaseURL, s.apiKey, steamID)

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	friendslist, _ := traverse(raw, "friendslist")
	friendsRaw, _ := traverseList(friendslist, "friends")

	var friends []any
	for _, f := range friendsRaw {
		fm, ok := f.(map[string]any)
		if !ok {
			continue
		}
		friends = append(friends, map[string]any{
			"steam_id":     getString(fm, "steamid"),
			"relationship": getString(fm, "relationship"),
			"friend_since": getNumber(fm, "friend_since"),
		})
	}

	return structpb.NewStruct(map[string]any{
		"friends": friends,
	})
}

// GetNewsForApp retrieves news articles for a Steam app.
func (s *SteamService) GetNewsForApp(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	appID := int(fields["app_id"].GetNumberValue())
	if appID == 0 {
		return nil, fmt.Errorf("app_id is required")
	}

	params := url.Values{}
	params.Set("appid", strconv.Itoa(appID))
	params.Set("format", "json")

	count := int(fields["count"].GetNumberValue())
	if count <= 0 {
		count = 10
	}
	params.Set("count", strconv.Itoa(count))

	maxLength := int(fields["max_length"].GetNumberValue())
	if maxLength > 0 {
		params.Set("maxlength", strconv.Itoa(maxLength))
	}

	u := fmt.Sprintf("%s/ISteamNews/GetNewsForApp/v0002/?%s", s.steamBaseURL, params.Encode())

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	appnews, _ := traverse(raw, "appnews")
	newsRaw, _ := traverseList(appnews, "newsitems")
	respAppID := getNumber(appnews, "appid")

	var newsItems []any
	for _, n := range newsRaw {
		nm, ok := n.(map[string]any)
		if !ok {
			continue
		}
		newsItems = append(newsItems, map[string]any{
			"gid":        getString(nm, "gid"),
			"title":      getString(nm, "title"),
			"url":        getString(nm, "url"),
			"author":     getString(nm, "author"),
			"contents":   getString(nm, "contents"),
			"feed_label": getString(nm, "feedlabel"),
			"date":       getNumber(nm, "date"),
			"feed_name":  getString(nm, "feedname"),
		})
	}

	return structpb.NewStruct(map[string]any{
		"app_id":     respAppID,
		"news_items": newsItems,
	})
}

// GetGlobalAchievementPercentages retrieves global achievement completion rates for a game.
func (s *SteamService) GetGlobalAchievementPercentages(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	appID := int(req.GetFields()["app_id"].GetNumberValue())
	if appID == 0 {
		return nil, fmt.Errorf("app_id is required")
	}

	u := fmt.Sprintf("%s/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid=%d",
		s.steamBaseURL, appID)

	raw, err := s.get(u)
	if err != nil {
		return nil, err
	}

	percentages, _ := traverse(raw, "achievementpercentages")
	achievementsRaw, _ := traverseList(percentages, "achievements")

	var achievements []any
	for _, a := range achievementsRaw {
		am, ok := a.(map[string]any)
		if !ok {
			continue
		}
		achievements = append(achievements, map[string]any{
			"name":    getString(am, "name"),
			"percent": getNumber(am, "percent"),
		})
	}

	return structpb.NewStruct(map[string]any{
		"achievements": achievements,
	})
}

// --- Helpers ---

// traverse safely navigates into a nested map by key.
func traverse(m map[string]any, key string) (map[string]any, bool) {
	if m == nil {
		return nil, false
	}
	v, ok := m[key]
	if !ok {
		return nil, false
	}
	result, ok := v.(map[string]any)
	return result, ok
}

// traverseList safely extracts a list from a map by key.
func traverseList(m map[string]any, key string) ([]any, bool) {
	if m == nil {
		return nil, false
	}
	v, ok := m[key]
	if !ok {
		return nil, false
	}
	result, ok := v.([]any)
	return result, ok
}

// getString safely extracts a string value from a map.
func getString(m map[string]any, key string) string {
	if m == nil {
		return ""
	}
	v, ok := m[key]
	if !ok {
		return ""
	}
	switch val := v.(type) {
	case string:
		return val
	case float64:
		// Some IDs come as numbers but we want them as strings.
		if val == float64(int64(val)) {
			return strconv.FormatInt(int64(val), 10)
		}
		return strconv.FormatFloat(val, 'f', -1, 64)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// getNumber safely extracts a numeric value from a map.
func getNumber(m map[string]any, key string) float64 {
	if m == nil {
		return 0
	}
	v, ok := m[key]
	if !ok {
		return 0
	}
	switch val := v.(type) {
	case float64:
		return val
	case int:
		return float64(val)
	case int64:
		return float64(val)
	case bool:
		if val {
			return 1
		}
		return 0
	case string:
		f, _ := strconv.ParseFloat(val, 64)
		return f
	default:
		return 0
	}
}

// getBool safely extracts a boolean value from a map.
func getBool(m map[string]any, key string) bool {
	if m == nil {
		return false
	}
	v, ok := m[key]
	if !ok {
		return false
	}
	switch val := v.(type) {
	case bool:
		return val
	case float64:
		return val != 0
	case string:
		return strings.EqualFold(val, "true") || val == "1"
	default:
		return false
	}
}

// getStringSlice extracts a []string from a map value that may be []any.
func getStringSlice(m map[string]any, key string) []any {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok {
		return nil
	}
	raw, ok := v.([]any)
	if !ok {
		return nil
	}
	result := make([]any, len(raw))
	for i, item := range raw {
		result[i] = fmt.Sprintf("%v", item)
	}
	return result
}

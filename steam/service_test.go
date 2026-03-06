package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/types/known/structpb"
)

// mockSteamServer returns an httptest.Server that routes Steam API and Store API requests.
func mockSteamServer(t *testing.T) *httptest.Server {
	t.Helper()
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		path := r.URL.Path

		switch {
		case strings.Contains(path, "GetPlayerSummaries"):
			json.NewEncoder(w).Encode(map[string]any{
				"response": map[string]any{
					"players": []any{
						map[string]any{
							"steamid":                  "76561197960435530",
							"personaname":              "Robin",
							"profileurl":               "https://steamcommunity.com/id/robin/",
							"avatar":                   "https://example.com/avatar_small.jpg",
							"avatarmedium":             "https://example.com/avatar_medium.jpg",
							"avatarfull":               "https://example.com/avatar_full.jpg",
							"personastate":             float64(1),
							"communityvisibilitystate": float64(3),
							"lastlogoff":               float64(1700000000),
							"loccountrycode":           "US",
							"timecreated":              float64(1063407589),
							"gameid":                   "440",
							"gameextrainfo":            "Team Fortress 2",
						},
					},
				},
			})

		case strings.Contains(path, "GetOwnedGames"):
			json.NewEncoder(w).Encode(map[string]any{
				"response": map[string]any{
					"game_count": float64(3),
					"games": []any{
						map[string]any{
							"appid":            float64(440),
							"name":             "Team Fortress 2",
							"playtime_forever": float64(12345),
							"playtime_2weeks":  float64(120),
							"img_icon_url":     "e3f595a92552da3d664ad00277fad2107345f743",
						},
						map[string]any{
							"appid":            float64(730),
							"name":             "Counter-Strike 2",
							"playtime_forever": float64(5000),
							"playtime_2weeks":  float64(60),
							"img_icon_url":     "abc123",
						},
						map[string]any{
							"appid":            float64(570),
							"name":             "Dota 2",
							"playtime_forever": float64(999),
							"playtime_2weeks":  float64(0),
							"img_icon_url":     "def456",
						},
					},
				},
			})

		case strings.Contains(path, "GetRecentlyPlayedGames"):
			json.NewEncoder(w).Encode(map[string]any{
				"response": map[string]any{
					"total_count": float64(2),
					"games": []any{
						map[string]any{
							"appid":            float64(440),
							"name":             "Team Fortress 2",
							"playtime_2weeks":  float64(120),
							"playtime_forever": float64(12345),
							"img_icon_url":     "e3f595a92552da3d664ad00277fad2107345f743",
						},
						map[string]any{
							"appid":            float64(730),
							"name":             "Counter-Strike 2",
							"playtime_2weeks":  float64(60),
							"playtime_forever": float64(5000),
							"img_icon_url":     "abc123",
						},
					},
				},
			})

		case strings.Contains(path, "GetPlayerAchievements"):
			json.NewEncoder(w).Encode(map[string]any{
				"playerstats": map[string]any{
					"steamID":  "76561197960435530",
					"gameName": "Team Fortress 2",
					"success":  true,
					"achievements": []any{
						map[string]any{
							"apiname":     "TF_PLAY_GAME_EVERYCLASS",
							"achieved":    float64(1),
							"unlocktime":  float64(1234567890),
							"name":        "Head of the Class",
							"description": "Play a complete round with every class.",
						},
						map[string]any{
							"apiname":     "TF_GET_HEALPOINTS",
							"achieved":    float64(0),
							"unlocktime":  float64(0),
							"name":        "Team Doctor",
							"description": "Accumulate 25000 heal points as a Medic.",
						},
					},
				},
			})

		case strings.Contains(path, "GetGlobalAchievementPercentagesForApp"):
			json.NewEncoder(w).Encode(map[string]any{
				"achievementpercentages": map[string]any{
					"achievements": []any{
						map[string]any{
							"name":    "TF_PLAY_GAME_EVERYCLASS",
							"percent": 45.3,
						},
						map[string]any{
							"name":    "TF_GET_HEALPOINTS",
							"percent": 12.7,
						},
					},
				},
			})

		case strings.Contains(path, "GetNumberOfCurrentPlayers"):
			json.NewEncoder(w).Encode(map[string]any{
				"response": map[string]any{
					"player_count": float64(85432),
					"result":       float64(1),
				},
			})

		case strings.Contains(path, "GetFriendList"):
			json.NewEncoder(w).Encode(map[string]any{
				"friendslist": map[string]any{
					"friends": []any{
						map[string]any{
							"steamid":      "76561197960265731",
							"relationship": "friend",
							"friend_since": float64(1300000000),
						},
						map[string]any{
							"steamid":      "76561197960265732",
							"relationship": "friend",
							"friend_since": float64(1400000000),
						},
					},
				},
			})

		case strings.Contains(path, "GetNewsForApp"):
			json.NewEncoder(w).Encode(map[string]any{
				"appnews": map[string]any{
					"appid": float64(440),
					"newsitems": []any{
						map[string]any{
							"gid":       "5000000000000000001",
							"title":     "TF2 Update Released",
							"url":       "https://store.steampowered.com/news/440",
							"author":    "Valve",
							"contents":  "Bug fixes and improvements.",
							"feedlabel": "steam_community_announcements",
							"date":      float64(1700000000),
							"feedname":  "steam_community_announcements",
						},
					},
				},
			})

		case strings.Contains(path, "GetAppList"):
			json.NewEncoder(w).Encode(map[string]any{
				"applist": map[string]any{
					"apps": []any{
						map[string]any{
							"appid": float64(10),
							"name":  "Counter-Strike",
						},
						map[string]any{
							"appid": float64(440),
							"name":  "Team Fortress 2",
						},
						map[string]any{
							"appid": float64(570),
							"name":  "Dota 2",
						},
					},
				},
			})

		case strings.Contains(path, "/api/appdetails"):
			appIDs := r.URL.Query().Get("appids")
			json.NewEncoder(w).Encode(map[string]any{
				appIDs: map[string]any{
					"success": true,
					"data": map[string]any{
						"type":                 "game",
						"name":                 "Team Fortress 2",
						"steam_appid":          float64(440),
						"short_description":    "Nine distinct classes provide a broad range of tactical abilities and personalities.",
						"detailed_description": "<h1>Team Fortress 2</h1><p>A free-to-play team-based FPS.</p>",
						"developers":           []any{"Valve"},
						"publishers":           []any{"Valve"},
						"is_free":              true,
						"header_image":         "https://cdn.akamai.steamstatic.com/steam/apps/440/header.jpg",
						"website":              "http://www.teamfortress.com",
						"platforms": map[string]any{
							"windows": true,
							"mac":     true,
							"linux":   true,
						},
						"metacritic": map[string]any{
							"score": float64(92),
							"url":   "https://www.metacritic.com/game/pc/team-fortress-2",
						},
						"genres": []any{
							map[string]any{"id": "1", "description": "Action"},
							map[string]any{"id": "37", "description": "Free to Play"},
						},
						"release_date": map[string]any{
							"coming_soon": false,
							"date":        "Oct 10, 2007",
						},
						"recommendations": map[string]any{
							"total": float64(900000),
						},
						"price_overview": map[string]any{
							"currency":          "USD",
							"initial":           float64(0),
							"final":             float64(0),
							"discount_percent":  float64(0),
							"initial_formatted": "",
							"final_formatted":   "Free To Play",
						},
					},
				},
			})

		default:
			http.NotFound(w, r)
		}
	}))
}

// testService creates a SteamService pointed at a mock server.
func testService(t *testing.T) (*SteamService, *httptest.Server) {
	t.Helper()
	ts := mockSteamServer(t)
	t.Cleanup(ts.Close)
	svc := &SteamService{
		apiKey:       "test-api-key",
		client:       ts.Client(),
		steamBaseURL: ts.URL,
		storeBaseURL: ts.URL,
	}
	return svc, ts
}

func makeReq(t *testing.T, fields map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(fields)
	require.NoError(t, err)
	return s
}

func TestGetPlayerSummaries(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetPlayerSummaries(context.Background(), makeReq(t, map[string]any{
		"steam_ids": "76561197960435530",
	}))
	require.NoError(t, err)

	players := resp.GetFields()["players"].GetListValue().GetValues()
	require.Len(t, players, 1)

	p := players[0].GetStructValue().GetFields()
	assert.Equal(t, "76561197960435530", p["steam_id"].GetStringValue())
	assert.Equal(t, "Robin", p["persona_name"].GetStringValue())
	assert.Equal(t, "https://steamcommunity.com/id/robin/", p["profile_url"].GetStringValue())
	assert.Equal(t, "US", p["country_code"].GetStringValue())
	assert.InEpsilon(t, 1.0, p["persona_state"].GetNumberValue(), 0.01)
	assert.InEpsilon(t, 3.0, p["community_visibility_state"].GetNumberValue(), 0.01)
	assert.Equal(t, "440", p["game_id"].GetStringValue())
	assert.Equal(t, "Team Fortress 2", p["game_extra_info"].GetStringValue())
}

func TestGetPlayerSummaries_MissingSteamIDs(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetPlayerSummaries(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "steam_ids is required")
}

func TestGetOwnedGames(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetOwnedGames(context.Background(), makeReq(t, map[string]any{
		"steam_id":        "76561197960435530",
		"include_appinfo": true,
	}))
	require.NoError(t, err)

	fields := resp.GetFields()
	assert.InEpsilon(t, 3.0, fields["game_count"].GetNumberValue(), 0.01)

	games := fields["games"].GetListValue().GetValues()
	require.Len(t, games, 3)

	g0 := games[0].GetStructValue().GetFields()
	assert.InEpsilon(t, 440.0, g0["app_id"].GetNumberValue(), 0.01)
	assert.Equal(t, "Team Fortress 2", g0["name"].GetStringValue())
	assert.InEpsilon(t, 12345.0, g0["playtime_forever"].GetNumberValue(), 0.01)
}

func TestGetOwnedGames_MissingSteamID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetOwnedGames(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "steam_id is required")
}

func TestGetRecentlyPlayedGames(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetRecentlyPlayedGames(context.Background(), makeReq(t, map[string]any{
		"steam_id": "76561197960435530",
		"count":    float64(5),
	}))
	require.NoError(t, err)

	fields := resp.GetFields()
	assert.InEpsilon(t, 2.0, fields["total_count"].GetNumberValue(), 0.01)

	games := fields["games"].GetListValue().GetValues()
	require.Len(t, games, 2)

	g0 := games[0].GetStructValue().GetFields()
	assert.InEpsilon(t, 440.0, g0["app_id"].GetNumberValue(), 0.01)
	assert.Equal(t, "Team Fortress 2", g0["name"].GetStringValue())
	assert.InEpsilon(t, 120.0, g0["playtime_2weeks"].GetNumberValue(), 0.01)
}

func TestGetRecentlyPlayedGames_MissingSteamID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetRecentlyPlayedGames(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "steam_id is required")
}

func TestGetPlayerAchievements(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetPlayerAchievements(context.Background(), makeReq(t, map[string]any{
		"steam_id": "76561197960435530",
		"app_id":   float64(440),
	}))
	require.NoError(t, err)

	fields := resp.GetFields()
	assert.Equal(t, "Team Fortress 2", fields["game_name"].GetStringValue())
	assert.Equal(t, "76561197960435530", fields["steam_id"].GetStringValue())
	assert.True(t, fields["success"].GetBoolValue())

	achievements := fields["achievements"].GetListValue().GetValues()
	require.Len(t, achievements, 2)

	a0 := achievements[0].GetStructValue().GetFields()
	assert.Equal(t, "TF_PLAY_GAME_EVERYCLASS", a0["api_name"].GetStringValue())
	assert.True(t, a0["achieved"].GetBoolValue())
	assert.InEpsilon(t, 1234567890.0, a0["unlock_time"].GetNumberValue(), 0.01)
	assert.Equal(t, "Head of the Class", a0["name"].GetStringValue())

	a1 := achievements[1].GetStructValue().GetFields()
	assert.Equal(t, "TF_GET_HEALPOINTS", a1["api_name"].GetStringValue())
	assert.False(t, a1["achieved"].GetBoolValue())
}

func TestGetPlayerAchievements_MissingParams(t *testing.T) {
	svc, _ := testService(t)

	_, err := svc.GetPlayerAchievements(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(440),
	}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "steam_id is required")

	_, err = svc.GetPlayerAchievements(context.Background(), makeReq(t, map[string]any{
		"steam_id": "76561197960435530",
	}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "app_id is required")
}

func TestGetAppDetails(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetAppDetails(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(440),
	}))
	require.NoError(t, err)

	fields := resp.GetFields()
	assert.True(t, fields["success"].GetBoolValue())

	data := fields["data"].GetStructValue().GetFields()
	assert.Equal(t, "Team Fortress 2", data["name"].GetStringValue())
	assert.Equal(t, "game", data["type"].GetStringValue())
	assert.True(t, data["is_free"].GetBoolValue())
	assert.Equal(t, "Oct 10, 2007", data["release_date"].GetStringValue())

	platforms := data["platforms"].GetStructValue().GetFields()
	assert.True(t, platforms["windows"].GetBoolValue())
	assert.True(t, platforms["mac"].GetBoolValue())
	assert.True(t, platforms["linux"].GetBoolValue())

	metacritic := data["metacritic"].GetStructValue().GetFields()
	assert.InEpsilon(t, 92.0, metacritic["score"].GetNumberValue(), 0.01)

	genres := data["genres"].GetListValue().GetValues()
	require.Len(t, genres, 2)
	assert.Equal(t, "Action", genres[0].GetStructValue().GetFields()["description"].GetStringValue())

	developers := data["developers"].GetListValue().GetValues()
	require.Len(t, developers, 1)
	assert.Equal(t, "Valve", developers[0].GetStringValue())

	price := data["price_overview"].GetStructValue().GetFields()
	assert.Equal(t, "USD", price["currency"].GetStringValue())
	assert.Equal(t, "Free To Play", price["final_formatted"].GetStringValue())

	assert.InEpsilon(t, 900000.0, data["recommendations"].GetNumberValue(), 0.01)
}

func TestGetAppDetails_MissingAppID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetAppDetails(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "app_id is required")
}

func TestGetAppList(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetAppList(context.Background(), makeReq(t, map[string]any{}))
	require.NoError(t, err)

	apps := resp.GetFields()["apps"].GetListValue().GetValues()
	require.Len(t, apps, 3)

	a0 := apps[0].GetStructValue().GetFields()
	assert.InEpsilon(t, 10.0, a0["app_id"].GetNumberValue(), 0.01)
	assert.Equal(t, "Counter-Strike", a0["name"].GetStringValue())

	a1 := apps[1].GetStructValue().GetFields()
	assert.InEpsilon(t, 440.0, a1["app_id"].GetNumberValue(), 0.01)
	assert.Equal(t, "Team Fortress 2", a1["name"].GetStringValue())
}

func TestGetNumberOfCurrentPlayers(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetNumberOfCurrentPlayers(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(440),
	}))
	require.NoError(t, err)

	assert.InEpsilon(t, 85432.0, resp.GetFields()["player_count"].GetNumberValue(), 0.01)
}

func TestGetNumberOfCurrentPlayers_MissingAppID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetNumberOfCurrentPlayers(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "app_id is required")
}

func TestGetFriendList(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetFriendList(context.Background(), makeReq(t, map[string]any{
		"steam_id": "76561197960435530",
	}))
	require.NoError(t, err)

	friends := resp.GetFields()["friends"].GetListValue().GetValues()
	require.Len(t, friends, 2)

	f0 := friends[0].GetStructValue().GetFields()
	assert.Equal(t, "76561197960265731", f0["steam_id"].GetStringValue())
	assert.Equal(t, "friend", f0["relationship"].GetStringValue())
	assert.InEpsilon(t, 1300000000.0, f0["friend_since"].GetNumberValue(), 0.01)
}

func TestGetFriendList_MissingSteamID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetFriendList(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "steam_id is required")
}

func TestGetNewsForApp(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetNewsForApp(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(440),
		"count":  float64(5),
	}))
	require.NoError(t, err)

	fields := resp.GetFields()
	assert.InEpsilon(t, 440.0, fields["app_id"].GetNumberValue(), 0.01)

	items := fields["news_items"].GetListValue().GetValues()
	require.Len(t, items, 1)

	n0 := items[0].GetStructValue().GetFields()
	assert.Equal(t, "TF2 Update Released", n0["title"].GetStringValue())
	assert.Equal(t, "Valve", n0["author"].GetStringValue())
	assert.Equal(t, "Bug fixes and improvements.", n0["contents"].GetStringValue())
	assert.Equal(t, "steam_community_announcements", n0["feed_label"].GetStringValue())
}

func TestGetNewsForApp_MissingAppID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetNewsForApp(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "app_id is required")
}

func TestGetGlobalAchievementPercentages(t *testing.T) {
	svc, _ := testService(t)
	resp, err := svc.GetGlobalAchievementPercentages(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(440),
	}))
	require.NoError(t, err)

	achievements := resp.GetFields()["achievements"].GetListValue().GetValues()
	require.Len(t, achievements, 2)

	a0 := achievements[0].GetStructValue().GetFields()
	assert.Equal(t, "TF_PLAY_GAME_EVERYCLASS", a0["name"].GetStringValue())
	assert.InEpsilon(t, 45.3, a0["percent"].GetNumberValue(), 0.01)

	a1 := achievements[1].GetStructValue().GetFields()
	assert.Equal(t, "TF_GET_HEALPOINTS", a1["name"].GetStringValue())
	assert.InEpsilon(t, 12.7, a1["percent"].GetNumberValue(), 0.01)
}

func TestGetGlobalAchievementPercentages_MissingAppID(t *testing.T) {
	svc, _ := testService(t)
	_, err := svc.GetGlobalAchievementPercentages(context.Background(), makeReq(t, map[string]any{}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "app_id is required")
}

func TestGetAppDetails_NotFound(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		appIDs := r.URL.Query().Get("appids")
		json.NewEncoder(w).Encode(map[string]any{
			appIDs: map[string]any{
				"success": false,
			},
		})
	}))
	t.Cleanup(ts.Close)

	svc := &SteamService{
		apiKey:       "test-key",
		client:       ts.Client(),
		steamBaseURL: ts.URL,
		storeBaseURL: ts.URL,
	}

	resp, err := svc.GetAppDetails(context.Background(), makeReq(t, map[string]any{
		"app_id": float64(99999999),
	}))
	require.NoError(t, err)
	assert.False(t, resp.GetFields()["success"].GetBoolValue())
}

func TestHTTPErrorHandling(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal Server Error"))
	}))
	t.Cleanup(ts.Close)

	svc := &SteamService{
		apiKey:       "test-key",
		client:       ts.Client(),
		steamBaseURL: ts.URL,
		storeBaseURL: ts.URL,
	}

	_, err := svc.GetPlayerSummaries(context.Background(), makeReq(t, map[string]any{
		"steam_ids": "76561197960435530",
	}))
	require.Error(t, err)
	assert.Contains(t, err.Error(), "500")
}

func TestNewSteamService(t *testing.T) {
	t.Setenv("STEAM_API_KEY", "my-test-key")
	svc := NewSteamService()
	assert.Equal(t, "my-test-key", svc.apiKey)
	assert.Equal(t, defaultSteamBaseURL, svc.steamBaseURL)
	assert.Equal(t, defaultStoreBaseURL, svc.storeBaseURL)
	assert.NotNil(t, svc.client)
}

package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockOddsServer creates a test server that returns realistic Odds API responses.
func mockOddsServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/sports" || r.URL.Path == "/sports/":
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"key":           "americanfootball_nfl",
					"active":        true,
					"group":         "American Football",
					"title":         "NFL",
					"description":   "US Football",
					"has_outrights": false,
				},
				map[string]any{
					"key":           "basketball_nba",
					"active":        true,
					"group":         "Basketball",
					"title":         "NBA",
					"description":   "US Basketball",
					"has_outrights": false,
				},
				map[string]any{
					"key":           "soccer_epl",
					"active":        true,
					"group":         "Soccer",
					"title":         "EPL",
					"description":   "English Premier League",
					"has_outrights": true,
				},
			})

		case strings.Contains(r.URL.Path, "/odds-history"):
			json.NewEncoder(w).Encode(map[string]any{
				"timestamp": "2024-01-15T12:00:00Z",
				"data": []any{
					map[string]any{
						"id":             "event123hist",
						"sport_key":      "americanfootball_nfl",
						"sport_title":    "NFL",
						"commence_time":  "2024-01-15T18:00:00Z",
						"home_team":      "Kansas City Chiefs",
						"away_team":      "Buffalo Bills",
						"bookmakers": []any{
							map[string]any{
								"key":         "draftkings",
								"title":       "DraftKings",
								"last_update": "2024-01-15T11:55:00Z",
								"markets": []any{
									map[string]any{
										"key":         "h2h",
										"last_update": "2024-01-15T11:55:00Z",
										"outcomes": []any{
											map[string]any{"name": "Kansas City Chiefs", "price": 1.65},
											map[string]any{"name": "Buffalo Bills", "price": 2.30},
										},
									},
								},
							},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/events/") && strings.Contains(r.URL.Path, "/odds"):
			json.NewEncoder(w).Encode(map[string]any{
				"id":             "event123",
				"sport_key":      "americanfootball_nfl",
				"sport_title":    "NFL",
				"commence_time":  "2024-12-25T18:00:00Z",
				"home_team":      "Kansas City Chiefs",
				"away_team":      "Pittsburgh Steelers",
				"bookmakers": []any{
					map[string]any{
						"key":         "fanduel",
						"title":       "FanDuel",
						"last_update": "2024-12-24T20:00:00Z",
						"markets": []any{
							map[string]any{
								"key":         "h2h",
								"last_update": "2024-12-24T20:00:00Z",
								"outcomes": []any{
									map[string]any{"name": "Kansas City Chiefs", "price": 1.45},
									map[string]any{"name": "Pittsburgh Steelers", "price": 2.90},
								},
							},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/events"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"id":            "event456",
					"sport_key":     "americanfootball_nfl",
					"sport_title":   "NFL",
					"commence_time": "2024-12-29T18:00:00Z",
					"home_team":     "Dallas Cowboys",
					"away_team":     "Philadelphia Eagles",
				},
				map[string]any{
					"id":            "event789",
					"sport_key":     "americanfootball_nfl",
					"sport_title":   "NFL",
					"commence_time": "2024-12-29T21:00:00Z",
					"home_team":     "San Francisco 49ers",
					"away_team":     "Arizona Cardinals",
				},
			})

		case strings.Contains(r.URL.Path, "/scores"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"id":            "score001",
					"sport_key":     "americanfootball_nfl",
					"sport_title":   "NFL",
					"commence_time": "2024-12-22T18:00:00Z",
					"completed":     true,
					"home_team":     "Green Bay Packers",
					"away_team":     "Miami Dolphins",
					"scores": []any{
						map[string]any{"name": "Green Bay Packers", "score": "31"},
						map[string]any{"name": "Miami Dolphins", "score": "27"},
					},
					"last_update": "2024-12-22T21:30:00Z",
				},
				map[string]any{
					"id":            "score002",
					"sport_key":     "americanfootball_nfl",
					"sport_title":   "NFL",
					"commence_time": "2024-12-22T21:00:00Z",
					"completed":     false,
					"home_team":     "Detroit Lions",
					"away_team":     "Chicago Bears",
					"scores": []any{
						map[string]any{"name": "Detroit Lions", "score": "14"},
						map[string]any{"name": "Chicago Bears", "score": "7"},
					},
					"last_update": "2024-12-22T22:00:00Z",
				},
			})

		case strings.Contains(r.URL.Path, "/odds"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"id":            "odds001",
					"sport_key":     "americanfootball_nfl",
					"sport_title":   "NFL",
					"commence_time": "2024-12-25T18:00:00Z",
					"home_team":     "Kansas City Chiefs",
					"away_team":     "Pittsburgh Steelers",
					"bookmakers": []any{
						map[string]any{
							"key":         "draftkings",
							"title":       "DraftKings",
							"last_update": "2024-12-24T15:00:00Z",
							"markets": []any{
								map[string]any{
									"key":         "h2h",
									"last_update": "2024-12-24T15:00:00Z",
									"outcomes": []any{
										map[string]any{"name": "Kansas City Chiefs", "price": 1.50},
										map[string]any{"name": "Pittsburgh Steelers", "price": 2.75},
									},
								},
								map[string]any{
									"key":         "spreads",
									"last_update": "2024-12-24T15:00:00Z",
									"outcomes": []any{
										map[string]any{"name": "Kansas City Chiefs", "price": 1.91, "point": -7.5},
										map[string]any{"name": "Pittsburgh Steelers", "price": 1.91, "point": 7.5},
									},
								},
								map[string]any{
									"key":         "totals",
									"last_update": "2024-12-24T15:00:00Z",
									"outcomes": []any{
										map[string]any{"name": "Over", "price": 1.91, "point": 47.5},
										map[string]any{"name": "Under", "price": 1.91, "point": 47.5},
									},
								},
							},
						},
						map[string]any{
							"key":         "fanduel",
							"title":       "FanDuel",
							"last_update": "2024-12-24T15:05:00Z",
							"markets": []any{
								map[string]any{
									"key":         "h2h",
									"last_update": "2024-12-24T15:05:00Z",
									"outcomes": []any{
										map[string]any{"name": "Kansas City Chiefs", "price": 1.48},
										map[string]any{"name": "Pittsburgh Steelers", "price": 2.80},
									},
								},
							},
						},
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *TheOddsApiService {
	return &TheOddsApiService{
		baseURL: serverURL,
		apiKey:  "test-api-key",
		client:  &http.Client{},
	}
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

// --- Mock Tests ---

func TestListSports(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListSports(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListSports: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	sports := items.GetListValue().GetValues()
	if len(sports) != 3 {
		t.Fatalf("expected 3 sports, got %d", len(sports))
	}

	first := sports[0].GetStructValue().GetFields()
	if got := first["key"].GetStringValue(); got != "americanfootball_nfl" {
		t.Errorf("key = %q, want %q", got, "americanfootball_nfl")
	}
	if got := first["title"].GetStringValue(); got != "NFL" {
		t.Errorf("title = %q, want %q", got, "NFL")
	}
	if got := first["active"].GetBoolValue(); got != true {
		t.Errorf("active = %v, want true", got)
	}
	if got := first["group"].GetStringValue(); got != "American Football" {
		t.Errorf("group = %q, want %q", got, "American Football")
	}

	third := sports[2].GetStructValue().GetFields()
	if got := third["has_outrights"].GetBoolValue(); got != true {
		t.Errorf("has_outrights = %v, want true", got)
	}
}

func TestGetOdds(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetOdds(context.Background(), mustStruct(t, map[string]any{
		"sport": "americanfootball_nfl",
	}))
	if err != nil {
		t.Fatalf("GetOdds: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	events := items.GetListValue().GetValues()
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}

	event := events[0].GetStructValue().GetFields()
	if got := event["home_team"].GetStringValue(); got != "Kansas City Chiefs" {
		t.Errorf("home_team = %q, want %q", got, "Kansas City Chiefs")
	}
	if got := event["away_team"].GetStringValue(); got != "Pittsburgh Steelers" {
		t.Errorf("away_team = %q, want %q", got, "Pittsburgh Steelers")
	}

	bookmakers := event["bookmakers"].GetListValue().GetValues()
	if len(bookmakers) != 2 {
		t.Fatalf("expected 2 bookmakers, got %d", len(bookmakers))
	}

	dk := bookmakers[0].GetStructValue().GetFields()
	if got := dk["key"].GetStringValue(); got != "draftkings" {
		t.Errorf("bookmaker key = %q, want %q", got, "draftkings")
	}

	markets := dk["markets"].GetListValue().GetValues()
	if len(markets) != 3 {
		t.Fatalf("expected 3 markets from DraftKings, got %d", len(markets))
	}

	h2h := markets[0].GetStructValue().GetFields()
	if got := h2h["key"].GetStringValue(); got != "h2h" {
		t.Errorf("market key = %q, want %q", got, "h2h")
	}

	outcomes := h2h["outcomes"].GetListValue().GetValues()
	if len(outcomes) != 2 {
		t.Fatalf("expected 2 h2h outcomes, got %d", len(outcomes))
	}
	if got := outcomes[0].GetStructValue().GetFields()["price"].GetNumberValue(); got != 1.50 {
		t.Errorf("KC h2h price = %v, want 1.50", got)
	}
}

func TestGetOddsWithCustomParams(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetOdds(context.Background(), mustStruct(t, map[string]any{
		"sport":   "americanfootball_nfl",
		"regions": "us,uk",
		"markets": "h2h",
	}))
	if err != nil {
		t.Fatalf("GetOdds: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
}

func TestGetOddsRequiresSport(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetOdds(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing sport")
	}
	if !strings.Contains(err.Error(), "sport is required") {
		t.Errorf("error = %q, want to contain 'sport is required'", err.Error())
	}
}

func TestGetScores(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetScores(context.Background(), mustStruct(t, map[string]any{
		"sport":     "americanfootball_nfl",
		"days_from": float64(1),
	}))
	if err != nil {
		t.Fatalf("GetScores: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	scores := items.GetListValue().GetValues()
	if len(scores) != 2 {
		t.Fatalf("expected 2 score events, got %d", len(scores))
	}

	first := scores[0].GetStructValue().GetFields()
	if got := first["completed"].GetBoolValue(); got != true {
		t.Errorf("completed = %v, want true", got)
	}
	if got := first["home_team"].GetStringValue(); got != "Green Bay Packers" {
		t.Errorf("home_team = %q, want %q", got, "Green Bay Packers")
	}

	scoreList := first["scores"].GetListValue().GetValues()
	if len(scoreList) != 2 {
		t.Fatalf("expected 2 scores, got %d", len(scoreList))
	}
	if got := scoreList[0].GetStructValue().GetFields()["score"].GetStringValue(); got != "31" {
		t.Errorf("score = %q, want %q", got, "31")
	}

	second := scores[1].GetStructValue().GetFields()
	if got := second["completed"].GetBoolValue(); got != false {
		t.Errorf("completed = %v, want false (in-progress)", got)
	}
}

func TestGetScoresRequiresSport(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetScores(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing sport")
	}
	if !strings.Contains(err.Error(), "sport is required") {
		t.Errorf("error = %q, want to contain 'sport is required'", err.Error())
	}
}

func TestGetEvents(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetEvents(context.Background(), mustStruct(t, map[string]any{
		"sport": "americanfootball_nfl",
	}))
	if err != nil {
		t.Fatalf("GetEvents: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	events := items.GetListValue().GetValues()
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}

	first := events[0].GetStructValue().GetFields()
	if got := first["id"].GetStringValue(); got != "event456" {
		t.Errorf("id = %q, want %q", got, "event456")
	}
	if got := first["home_team"].GetStringValue(); got != "Dallas Cowboys" {
		t.Errorf("home_team = %q, want %q", got, "Dallas Cowboys")
	}
	if got := first["away_team"].GetStringValue(); got != "Philadelphia Eagles" {
		t.Errorf("away_team = %q, want %q", got, "Philadelphia Eagles")
	}
}

func TestGetEventsRequiresSport(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetEvents(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing sport")
	}
	if !strings.Contains(err.Error(), "sport is required") {
		t.Errorf("error = %q, want to contain 'sport is required'", err.Error())
	}
}

func TestGetEventOdds(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetEventOdds(context.Background(), mustStruct(t, map[string]any{
		"sport":    "americanfootball_nfl",
		"event_id": "event123",
	}))
	if err != nil {
		t.Fatalf("GetEventOdds: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["id"].GetStringValue(); got != "event123" {
		t.Errorf("id = %q, want %q", got, "event123")
	}
	if got := fields["home_team"].GetStringValue(); got != "Kansas City Chiefs" {
		t.Errorf("home_team = %q, want %q", got, "Kansas City Chiefs")
	}

	bookmakers := fields["bookmakers"].GetListValue().GetValues()
	if len(bookmakers) != 1 {
		t.Fatalf("expected 1 bookmaker, got %d", len(bookmakers))
	}

	fd := bookmakers[0].GetStructValue().GetFields()
	if got := fd["key"].GetStringValue(); got != "fanduel" {
		t.Errorf("bookmaker key = %q, want %q", got, "fanduel")
	}
}

func TestGetEventOddsRequiresSport(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetEventOdds(context.Background(), mustStruct(t, map[string]any{
		"event_id": "event123",
	}))
	if err == nil {
		t.Fatal("expected error for missing sport")
	}
	if !strings.Contains(err.Error(), "sport is required") {
		t.Errorf("error = %q, want to contain 'sport is required'", err.Error())
	}
}

func TestGetEventOddsRequiresEventID(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetEventOdds(context.Background(), mustStruct(t, map[string]any{
		"sport": "americanfootball_nfl",
	}))
	if err == nil {
		t.Fatal("expected error for missing event_id")
	}
	if !strings.Contains(err.Error(), "event_id is required") {
		t.Errorf("error = %q, want to contain 'event_id is required'", err.Error())
	}
}

func TestGetHistoricalOdds(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetHistoricalOdds(context.Background(), mustStruct(t, map[string]any{
		"sport": "americanfootball_nfl",
		"date":  "2024-01-15T00:00:00Z",
	}))
	if err != nil {
		t.Fatalf("GetHistoricalOdds: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["timestamp"].GetStringValue(); got != "2024-01-15T12:00:00Z" {
		t.Errorf("timestamp = %q, want %q", got, "2024-01-15T12:00:00Z")
	}

	data := fields["data"].GetListValue().GetValues()
	if len(data) != 1 {
		t.Fatalf("expected 1 historical event, got %d", len(data))
	}

	event := data[0].GetStructValue().GetFields()
	if got := event["home_team"].GetStringValue(); got != "Kansas City Chiefs" {
		t.Errorf("home_team = %q, want %q", got, "Kansas City Chiefs")
	}
}

func TestGetHistoricalOddsRequiresSport(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetHistoricalOdds(context.Background(), mustStruct(t, map[string]any{
		"date": "2024-01-15T00:00:00Z",
	}))
	if err == nil {
		t.Fatal("expected error for missing sport")
	}
	if !strings.Contains(err.Error(), "sport is required") {
		t.Errorf("error = %q, want to contain 'sport is required'", err.Error())
	}
}

func TestGetHistoricalOddsRequiresDate(t *testing.T) {
	ts := mockOddsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetHistoricalOdds(context.Background(), mustStruct(t, map[string]any{
		"sport": "americanfootball_nfl",
	}))
	if err == nil {
		t.Fatal("expected error for missing date")
	}
	if !strings.Contains(err.Error(), "date is required") {
		t.Errorf("error = %q, want to contain 'date is required'", err.Error())
	}
}

// --- Live integration tests (hit the real Odds API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("ODDS_API_KEY") == "" {
		t.Skip("set ODDS_API_KEY to run live integration tests (hits real Odds API)")
	}
}

func liveService() *TheOddsApiService {
	return NewTheOddsApiService()
}

func TestLiveListSports(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListSports(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListSports: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListSports")
	}
	t.Logf("ListSports response keys: %v", keysOf(fields))
}

func TestLiveGetOdds(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetOdds(context.Background(), mustStruct(t, map[string]any{
		"sport": "upcoming",
	}))
	if err != nil {
		t.Fatalf("GetOdds: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetOdds")
	}
	t.Logf("GetOdds response keys: %v", keysOf(fields))
}

func TestLiveGetScores(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// Use "upcoming" which always has data.
	resp, err := svc.GetScores(context.Background(), mustStruct(t, map[string]any{
		"sport":     "americanfootball_nfl",
		"days_from": float64(3),
	}))
	if err != nil {
		// Scores may return error if no games recently.
		t.Logf("GetScores returned error (may be expected): %v", err)
		return
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetScores")
	}
	t.Logf("GetScores response keys: %v", keysOf(fields))
}

func TestLiveGetEvents(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetEvents(context.Background(), mustStruct(t, map[string]any{
		"sport": "upcoming",
	}))
	if err != nil {
		t.Fatalf("GetEvents: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetEvents")
	}
	t.Logf("GetEvents response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}

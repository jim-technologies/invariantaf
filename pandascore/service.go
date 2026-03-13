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

	"google.golang.org/protobuf/types/known/structpb"
)

// PandaScoreService implements the PandaScoreService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type PandaScoreService struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

// NewPandaScoreService creates a new service with default settings.
// Reads PANDASCORE_API_KEY from the environment for authentication and
// PANDASCORE_BASE_URL to override the default API base URL.
func NewPandaScoreService() *PandaScoreService {
	baseURL := os.Getenv("PANDASCORE_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.pandascore.co"
	}
	return &PandaScoreService{
		baseURL: baseURL,
		apiKey:  os.Getenv("PANDASCORE_API_KEY"),
		client:  &http.Client{},
	}
}

// get performs an authenticated GET request to the PandaScore API.
// The PandaScore API returns JSON arrays for list endpoints, so this method
// handles both array and object responses. Array responses are returned
// wrapped inside a map with a single "items" key.
func (s *PandaScoreService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if s.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.apiKey)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		var arr []any
		if err2 := json.Unmarshal(body, &arr); err2 == nil {
			result = map[string]any{"items": arr}
		} else {
			return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
		}
	}

	return result, nil
}

// helper: get a string field from structpb, with a default.
func getString(fields map[string]*structpb.Value, key, def string) string {
	if v, ok := fields[key]; ok && v.GetStringValue() != "" {
		return v.GetStringValue()
	}
	return def
}

// helper: get an int field from structpb (numbers come as float64).
func getInt(fields map[string]*structpb.Value, key string) int64 {
	if v, ok := fields[key]; ok {
		return int64(v.GetNumberValue())
	}
	return 0
}

// helper: get a float field from structpb.
func getFloat(fields map[string]*structpb.Value, key string) float64 {
	if v, ok := fields[key]; ok {
		return v.GetNumberValue()
	}
	return 0
}

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// paginationParams extracts page and per_page from the request, applying a
// default per_page value.
func paginationParams(fields map[string]*structpb.Value, perPageDefault int) url.Values {
	params := url.Values{}
	if v, ok := fields["page"]; ok && v.GetNumberValue() != 0 {
		params.Set("page", strconv.FormatInt(int64(v.GetNumberValue()), 10))
	}
	if v, ok := fields["per_page"]; ok && v.GetNumberValue() != 0 {
		params.Set("per_page", strconv.FormatInt(int64(v.GetNumberValue()), 10))
	} else {
		params.Set("per_page", strconv.Itoa(perPageDefault))
	}
	return params
}

// ListMatches lists all Dota 2 matches (past, upcoming, running).
func (s *PandaScoreService) ListMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)
	params.Set("sort", "-scheduled_at")

	data, err := s.get("/dota2/matches", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"matches": items})
}

// ListUpcomingMatches lists upcoming scheduled Dota 2 matches.
func (s *PandaScoreService) ListUpcomingMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/matches/upcoming", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"matches": items})
}

// ListRunningMatches lists currently live Dota 2 matches.
func (s *PandaScoreService) ListRunningMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/matches/running", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"matches": items})
}

// ListPastMatches lists completed Dota 2 matches with results.
func (s *PandaScoreService) ListPastMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)
	params.Set("sort", "-scheduled_at")

	data, err := s.get("/dota2/matches/past", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"matches": items})
}

// ListTournaments lists all Dota 2 tournaments.
func (s *PandaScoreService) ListTournaments(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/tournaments", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"tournaments": items})
}

// ListTeams lists all Dota 2 teams.
func (s *PandaScoreService) ListTeams(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/teams", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"teams": items})
}

// ListPlayers lists all Dota 2 players.
func (s *PandaScoreService) ListPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/players", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"players": items})
}

// ListLeagues lists all Dota 2 leagues.
func (s *PandaScoreService) ListLeagues(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/leagues", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"leagues": items})
}

// ListSeries lists upcoming Dota 2 series.
func (s *PandaScoreService) ListSeries(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 50)

	data, err := s.get("/dota2/series/upcoming", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"series": items})
}

// ListHeroes lists all Dota 2 heroes.
func (s *PandaScoreService) ListHeroes(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := paginationParams(fields, 100)

	data, err := s.get("/dota2/heroes", params)
	if err != nil {
		return nil, err
	}

	items := extractItems(data)
	return toStruct(map[string]any{"heroes": items})
}

// extractItems pulls the array payload out of the wrapped API response.
// PandaScore returns JSON arrays directly; our get() method wraps them in
// {"items": [...]}, so we extract them back here.
func extractItems(data map[string]any) []any {
	if items, ok := data["items"]; ok {
		if arr, ok := items.([]any); ok {
			return arr
		}
	}
	return []any{}
}

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

	"google.golang.org/protobuf/types/known/structpb"
)

// OpenDotaService implements the OpenDotaService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type OpenDotaService struct {
	baseURL string
	client  *http.Client
}

// NewOpenDotaService creates a new service with default settings.
// The OpenDota API is free and requires no authentication.
func NewOpenDotaService() *OpenDotaService {
	base := os.Getenv("OPENDOTA_BASE_URL")
	if base == "" {
		base = "https://api.opendota.com/api"
	}
	return &OpenDotaService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// get performs a GET request to the OpenDota API and returns the decoded JSON.
func (s *OpenDotaService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
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

// post performs a POST request to the OpenDota API and returns the decoded JSON.
func (s *OpenDotaService) post(path string, params url.Values, payload map[string]any) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}

	var bodyReader io.Reader
	if payload != nil {
		b, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequest("POST", u, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
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

	if resp.StatusCode != http.StatusOK {
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

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// queryParams extracts the optional "query" struct field as url.Values.
func queryParams(fields map[string]*structpb.Value) url.Values {
	params := url.Values{}
	if q, ok := fields["query"]; ok && q.GetStructValue() != nil {
		for k, v := range q.GetStructValue().GetFields() {
			params.Set(k, fmt.Sprintf("%v", v.AsInterface()))
		}
	}
	return params
}

// bodyPayload extracts the optional "body" struct field as a map.
func bodyPayload(fields map[string]*structpb.Value) map[string]any {
	if b, ok := fields["body"]; ok && b.GetStructValue() != nil {
		return b.GetStructValue().AsMap()
	}
	return nil
}

// GetBenchmarks returns benchmarks of average stat values for a hero.
func (s *OpenDotaService) GetBenchmarks(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/benchmarks", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetConstantsResource returns static game data mirrored from the dotaconstants repository.
func (s *OpenDotaService) GetConstantsResource(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	resource := getString(fields, "resource", "")
	if resource == "" {
		return nil, fmt.Errorf("resource is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/constants/%s", resource), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetDistributions returns distributions of MMR data by bracket and country.
func (s *OpenDotaService) GetDistributions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/distributions", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetExplorer submits arbitrary SQL queries to the database.
func (s *OpenDotaService) GetExplorer(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/explorer", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetFindMatches finds recent matches by heroes played.
func (s *OpenDotaService) GetFindMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/findMatches", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHealth returns service health data.
func (s *OpenDotaService) GetHealth(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/health", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroStats returns stats about hero performance in recent matches.
func (s *OpenDotaService) GetHeroStats(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/heroStats", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroes returns hero data.
func (s *OpenDotaService) GetHeroes(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/heroes", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroDurations returns hero performance over a range of match durations.
func (s *OpenDotaService) GetHeroDurations(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	heroID := getInt(fields, "hero_id")
	if heroID == 0 {
		return nil, fmt.Errorf("hero_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/heroes/%d/durations", heroID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroItemPopularity returns item popularity of a hero.
func (s *OpenDotaService) GetHeroItemPopularity(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	heroID := getInt(fields, "hero_id")
	if heroID == 0 {
		return nil, fmt.Errorf("hero_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/heroes/%d/itemPopularity", heroID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroMatches returns recent matches with a hero.
func (s *OpenDotaService) GetHeroMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	heroID := getInt(fields, "hero_id")
	if heroID == 0 {
		return nil, fmt.Errorf("hero_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/heroes/%d/matches", heroID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroMatchups returns results against other heroes for a hero.
func (s *OpenDotaService) GetHeroMatchups(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	heroID := getInt(fields, "hero_id")
	if heroID == 0 {
		return nil, fmt.Errorf("hero_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/heroes/%d/matchups", heroID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetHeroPlayers returns players who have played this hero.
func (s *OpenDotaService) GetHeroPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	heroID := getInt(fields, "hero_id")
	if heroID == 0 {
		return nil, fmt.Errorf("hero_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/heroes/%d/players", heroID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLeagues returns league data.
func (s *OpenDotaService) GetLeagues(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/leagues", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLeague returns data for a league.
func (s *OpenDotaService) GetLeague(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	leagueID := getInt(fields, "league_id")
	if leagueID == 0 {
		return nil, fmt.Errorf("league_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/leagues/%d", leagueID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLeagueMatchIds returns match IDs for a league.
func (s *OpenDotaService) GetLeagueMatchIds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	leagueID := getInt(fields, "league_id")
	if leagueID == 0 {
		return nil, fmt.Errorf("league_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/leagues/%d/matchIds", leagueID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLeagueMatches returns matches for a league.
func (s *OpenDotaService) GetLeagueMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	leagueID := getInt(fields, "league_id")
	if leagueID == 0 {
		return nil, fmt.Errorf("league_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/leagues/%d/matches", leagueID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLeagueTeams returns teams for a league.
func (s *OpenDotaService) GetLeagueTeams(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	leagueID := getInt(fields, "league_id")
	if leagueID == 0 {
		return nil, fmt.Errorf("league_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/leagues/%d/teams", leagueID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetLive returns top currently ongoing live games.
func (s *OpenDotaService) GetLive(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/live", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetMatch returns match data.
func (s *OpenDotaService) GetMatch(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	matchID := getInt(fields, "match_id")
	if matchID == 0 {
		return nil, fmt.Errorf("match_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/matches/%d", matchID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetMetadata returns site metadata.
func (s *OpenDotaService) GetMetadata(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/metadata", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetParsedMatches returns list of parsed match IDs.
func (s *OpenDotaService) GetParsedMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/parsedMatches", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayer returns player data.
func (s *OpenDotaService) GetPlayer(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerCounts returns counts in categories.
func (s *OpenDotaService) GetPlayerCounts(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/counts", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerHeroes returns heroes played.
func (s *OpenDotaService) GetPlayerHeroes(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/heroes", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerHistogramsField returns distribution of matches in a single stat.
func (s *OpenDotaService) GetPlayerHistogramsField(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	field := getString(fields, "field", "")
	if field == "" {
		return nil, fmt.Errorf("field is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/histograms/%s", accountID, field), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerMatches returns matches played.
func (s *OpenDotaService) GetPlayerMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/matches", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerPeers returns players played with.
func (s *OpenDotaService) GetPlayerPeers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/peers", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerPros returns pro players played with.
func (s *OpenDotaService) GetPlayerPros(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/pros", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerRankings returns player hero rankings.
func (s *OpenDotaService) GetPlayerRankings(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/rankings", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerRatings returns history of the player rank tier/medal changes.
func (s *OpenDotaService) GetPlayerRatings(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/ratings", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerRecentMatches returns recent matches played.
func (s *OpenDotaService) GetPlayerRecentMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/recentMatches", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// PostPlayerRefresh refreshes player match history.
func (s *OpenDotaService) PostPlayerRefresh(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	payload := bodyPayload(fields)
	data, err := s.post(fmt.Sprintf("/players/%d/refresh", accountID), params, payload)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerTotals returns totals in stats.
func (s *OpenDotaService) GetPlayerTotals(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/totals", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerWardmap returns wards placed in matches played.
func (s *OpenDotaService) GetPlayerWardmap(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/wardmap", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerWinLoss returns win/loss count.
func (s *OpenDotaService) GetPlayerWinLoss(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/wl", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPlayerWordcloud returns words said/read in matches played.
func (s *OpenDotaService) GetPlayerWordcloud(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	accountID := getInt(fields, "account_id")
	if accountID == 0 {
		return nil, fmt.Errorf("account_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/players/%d/wordcloud", accountID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetProMatches returns list of pro matches.
func (s *OpenDotaService) GetProMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/proMatches", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetProPlayers returns list of pro players.
func (s *OpenDotaService) GetProPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/proPlayers", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetPublicMatches returns list of randomly sampled public matches.
func (s *OpenDotaService) GetPublicMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/publicMatches", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetRankings returns top players by hero.
func (s *OpenDotaService) GetRankings(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/rankings", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetRecordsField returns top performances in a stat.
func (s *OpenDotaService) GetRecordsField(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	field := getString(fields, "field", "")
	if field == "" {
		return nil, fmt.Errorf("field is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/records/%s", field), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetRequestJobId returns parse request state.
func (s *OpenDotaService) GetRequestJobId(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	jobID := getString(fields, "job_id", "")
	if jobID == "" {
		return nil, fmt.Errorf("job_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/request/%s", jobID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// PostRequestMatchId submits a new parse request.
func (s *OpenDotaService) PostRequestMatchId(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	matchID := getInt(fields, "match_id")
	if matchID == 0 {
		return nil, fmt.Errorf("match_id is required")
	}
	params := queryParams(fields)
	payload := bodyPayload(fields)
	data, err := s.post(fmt.Sprintf("/request/%d", matchID), params, payload)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetScenariosItemTimings returns win rates for certain item timings on a hero.
func (s *OpenDotaService) GetScenariosItemTimings(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/scenarios/itemTimings", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetScenariosLaneRoles returns win rates for heroes in certain lane roles.
func (s *OpenDotaService) GetScenariosLaneRoles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/scenarios/laneRoles", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetScenariosMisc returns miscellaneous team scenarios.
func (s *OpenDotaService) GetScenariosMisc(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/scenarios/misc", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetSchema returns database schema.
func (s *OpenDotaService) GetSchema(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/schema", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// SearchPlayers searches players by personaname.
func (s *OpenDotaService) SearchPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/search", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTeams returns team data.
func (s *OpenDotaService) GetTeams(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/teams", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTeam returns data for a team.
func (s *OpenDotaService) GetTeam(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	teamID := getInt(fields, "team_id")
	if teamID == 0 {
		return nil, fmt.Errorf("team_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/teams/%d", teamID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTeamHeroes returns heroes for a team.
func (s *OpenDotaService) GetTeamHeroes(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	teamID := getInt(fields, "team_id")
	if teamID == 0 {
		return nil, fmt.Errorf("team_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/teams/%d/heroes", teamID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTeamMatches returns matches for a team.
func (s *OpenDotaService) GetTeamMatches(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	teamID := getInt(fields, "team_id")
	if teamID == 0 {
		return nil, fmt.Errorf("team_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/teams/%d/matches", teamID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTeamPlayers returns players who have played for a team.
func (s *OpenDotaService) GetTeamPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	teamID := getInt(fields, "team_id")
	if teamID == 0 {
		return nil, fmt.Errorf("team_id is required")
	}
	params := queryParams(fields)
	data, err := s.get(fmt.Sprintf("/teams/%d/players", teamID), params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTopPlayers returns list of highly ranked players.
func (s *OpenDotaService) GetTopPlayers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := queryParams(fields)
	data, err := s.get("/topPlayers", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

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

// BraveSearchService implements the BraveSearchService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response.
type BraveSearchService struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

// NewBraveSearchService creates a new service reading config from environment.
// Requires BRAVE_API_KEY. Optionally accepts BRAVE_BASE_URL (defaults to
// https://api.search.brave.com/res/v1).
func NewBraveSearchService() *BraveSearchService {
	baseURL := os.Getenv("BRAVE_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.search.brave.com/res/v1"
	}
	return &BraveSearchService{
		baseURL: baseURL,
		apiKey:  os.Getenv("BRAVE_API_KEY"),
		client:  &http.Client{},
	}
}

// get performs a GET request to the Brave Search API with the subscription token header.
func (s *BraveSearchService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("X-Subscription-Token", s.apiKey)

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
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	return result, nil
}

// WebSearch searches the web using Brave Search.
func (s *BraveSearchService) WebSearch(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := getString(fields, "query", "")
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{}
	params.Set("q", query)

	if count := getInt(fields, "count"); count > 0 {
		params.Set("count", strconv.FormatInt(count, 10))
	}
	if offset := getInt(fields, "offset"); offset > 0 {
		params.Set("offset", strconv.FormatInt(offset, 10))
	}
	if country := getString(fields, "country", ""); country != "" {
		params.Set("country", country)
	}
	if searchLang := getString(fields, "search_lang", ""); searchLang != "" {
		params.Set("search_lang", searchLang)
	}
	if freshness := getString(fields, "freshness", ""); freshness != "" {
		params.Set("freshness", freshness)
	}

	data, err := s.get("/web/search", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// NewsSearch searches news articles using Brave Search.
func (s *BraveSearchService) NewsSearch(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := getString(fields, "query", "")
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{}
	params.Set("q", query)

	if count := getInt(fields, "count"); count > 0 {
		params.Set("count", strconv.FormatInt(count, 10))
	}
	if country := getString(fields, "country", ""); country != "" {
		params.Set("country", country)
	}
	if freshness := getString(fields, "freshness", ""); freshness != "" {
		params.Set("freshness", freshness)
	}

	data, err := s.get("/news/search", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ImageSearch searches images using Brave Search.
func (s *BraveSearchService) ImageSearch(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := getString(fields, "query", "")
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{}
	params.Set("q", query)

	if count := getInt(fields, "count"); count > 0 {
		params.Set("count", strconv.FormatInt(count, 10))
	}
	if country := getString(fields, "country", ""); country != "" {
		params.Set("country", country)
	}

	data, err := s.get("/images/search", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
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

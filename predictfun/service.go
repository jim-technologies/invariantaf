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

// PredictFunService implements the PredictFunService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type PredictFunService struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

// NewPredictFunService creates a new service with default settings.
// Set PREDICTFUN_API_KEY for mainnet access.
// Set PREDICTFUN_BASE_URL to override the default base URL.
func NewPredictFunService() *PredictFunService {
	baseURL := os.Getenv("PREDICTFUN_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.predict.fun"
	}
	return &PredictFunService{
		baseURL: baseURL,
		apiKey:  os.Getenv("PREDICTFUN_API_KEY"),
		client:  &http.Client{},
	}
}

// get performs a GET request to the Predict.fun API.
func (s *PredictFunService) get(ctx context.Context, path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequestWithContext(ctx, "GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	if s.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.apiKey)
	}
	req.Header.Set("Accept", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("read error response: %w", err)
		}
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
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

// getByID fetches a resource at pathFmt (containing one %d verb) using the "id" field from the request.
func (s *PredictFunService) getByID(ctx context.Context, req *structpb.Struct, pathFmt string) (*structpb.Struct, error) {
	id := getInt(req.GetFields(), "id")
	if id == 0 {
		return nil, fmt.Errorf("id is required")
	}
	data, err := s.get(ctx, fmt.Sprintf(pathFmt, id), nil)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// ListMarkets lists prediction markets with optional filters.
func (s *PredictFunService) ListMarkets(ctx context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if status := getString(fields, "status", ""); status != "" {
		params.Set("status", status)
	}
	if slug := getString(fields, "category_slug", ""); slug != "" {
		params.Set("categorySlug", slug)
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if cursor := getString(fields, "cursor", ""); cursor != "" {
		params.Set("cursor", cursor)
	}

	data, err := s.get(ctx, "/v1/markets", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetMarket gets a single market by its numeric ID.
func (s *PredictFunService) GetMarket(ctx context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	return s.getByID(ctx, req, "/v1/markets/%d")
}

// GetOrderbook gets the orderbook for a specific market.
func (s *PredictFunService) GetOrderbook(ctx context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	return s.getByID(ctx, req, "/v1/markets/%d/orderbook")
}

// ListCategories lists available market categories.
func (s *PredictFunService) ListCategories(ctx context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if cursor := getString(fields, "cursor", ""); cursor != "" {
		params.Set("cursor", cursor)
	}

	data, err := s.get(ctx, "/v1/categories", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

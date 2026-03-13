package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"

	"google.golang.org/protobuf/types/known/structpb"
)

// AcrossService implements the AcrossService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type AcrossService struct {
	baseURL string
	client  *http.Client
}

// NewAcrossService creates a new service with default settings.
// No authentication is required for the Across public API.
func NewAcrossService() *AcrossService {
	return &AcrossService{
		baseURL: "https://app.across.to/api",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Across API and returns the decoded JSON.
func (s *AcrossService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. available-routes endpoint).
		// Try wrapping in a map.
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

// GetSuggestedFees gets suggested fees for a cross-chain bridge transfer.
func (s *AcrossService) GetSuggestedFees(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	token := getString(fields, "token", "")
	if token == "" {
		return nil, fmt.Errorf("token is required")
	}
	params.Set("token", token)

	destinationChainID := getInt(fields, "destination_chain_id")
	if destinationChainID == 0 {
		return nil, fmt.Errorf("destination_chain_id is required")
	}
	params.Set("destinationChainId", strconv.FormatInt(destinationChainID, 10))

	amount := getString(fields, "amount", "")
	if amount == "" {
		return nil, fmt.Errorf("amount is required")
	}
	params.Set("amount", amount)

	originChainID := getInt(fields, "origin_chain_id")
	if originChainID == 0 {
		return nil, fmt.Errorf("origin_chain_id is required")
	}
	params.Set("originChainId", strconv.FormatInt(originChainID, 10))

	data, err := s.get("/suggested-fees", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetAvailableRoutes gets available bridge routes between chains.
func (s *AcrossService) GetAvailableRoutes(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if originChainID := getInt(fields, "origin_chain_id"); originChainID > 0 {
		params.Set("originChainId", strconv.FormatInt(originChainID, 10))
	}
	if destinationChainID := getInt(fields, "destination_chain_id"); destinationChainID > 0 {
		params.Set("destinationChainId", strconv.FormatInt(destinationChainID, 10))
	}

	data, err := s.get("/available-routes", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetLimits gets transfer limits for a token between two chains.
func (s *AcrossService) GetLimits(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	token := getString(fields, "token", "")
	if token == "" {
		return nil, fmt.Errorf("token is required")
	}
	params.Set("token", token)

	destinationChainID := getInt(fields, "destination_chain_id")
	if destinationChainID == 0 {
		return nil, fmt.Errorf("destination_chain_id is required")
	}
	params.Set("destinationChainId", strconv.FormatInt(destinationChainID, 10))

	originChainID := getInt(fields, "origin_chain_id")
	if originChainID == 0 {
		return nil, fmt.Errorf("origin_chain_id is required")
	}
	params.Set("originChainId", strconv.FormatInt(originChainID, 10))

	data, err := s.get("/limits", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPoolState gets LP pool state for a token.
func (s *AcrossService) GetPoolState(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()

	token := getString(fields, "token", "")
	if token == "" {
		return nil, fmt.Errorf("token is required")
	}

	params := url.Values{}
	params.Set("token", token)

	data, err := s.get("/pools", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

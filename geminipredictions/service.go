package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"

	"google.golang.org/protobuf/types/known/structpb"
)

// GeminiPredictionsService implements the GeminiPredictionsService RPCs defined
// in the proto descriptor. Each method takes a structpb.Struct request and
// returns a structpb.Struct response, allowing the invariant protocol SDK to
// handle serialization/deserialization transparently.
type GeminiPredictionsService struct {
	baseURL string
	client  *http.Client
}

// NewGeminiPredictionsService creates a new service.
// The Gemini Prediction Markets public REST API requires no authentication
// for market-data endpoints.
func NewGeminiPredictionsService() *GeminiPredictionsService {
	base := os.Getenv("GEMINI_BASE_URL")
	if base == "" {
		base = "https://api.gemini.com"
	}
	return &GeminiPredictionsService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// get performs a GET request and returns the decoded JSON as a map.
func (s *GeminiPredictionsService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")

	// Add API key if provided (not required for public endpoints but
	// may be needed for higher rate limits).
	if apiKey := os.Getenv("GEMINI_API_KEY"); apiKey != "" {
		req.Header.Set("X-GEMINI-APIKEY", apiKey)
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

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// transformContract normalizes a contract object from the API.
func transformContract(c map[string]any) map[string]any {
	prices := map[string]any{}
	if raw, ok := c["prices"].(map[string]any); ok {
		prices = map[string]any{
			"best_bid":         stringVal(raw, "bestBid"),
			"best_ask":         stringVal(raw, "bestAsk"),
			"last_trade_price": stringVal(raw, "lastTradePrice"),
		}
	}

	return map[string]any{
		"id":                stringVal(c, "id"),
		"label":             stringVal(c, "label"),
		"abbreviated_name":  stringVal(c, "abbreviatedName"),
		"ticker":            stringVal(c, "ticker"),
		"instrument_symbol": stringVal(c, "instrumentSymbol"),
		"status":            stringVal(c, "status"),
		"market_state":      stringVal(c, "marketState"),
		"prices":            prices,
		"color":             stringVal(c, "color"),
		"image_url":         stringVal(c, "imageUrl"),
		"expiry_date":       stringVal(c, "expiryDate"),
		"effective_date":    stringVal(c, "effectiveDate"),
		"created_at":        stringVal(c, "createdAt"),
		"resolved_at":       stringVal(c, "resolvedAt"),
		"resolution_side":   stringVal(c, "resolutionSide"),
		"sort_order":        intVal(c, "sortOrder"),
	}
}

// transformEvent normalizes a prediction event from the API.
func transformEvent(e map[string]any) map[string]any {
	contracts := make([]any, 0)
	if rawContracts, ok := e["contracts"].([]any); ok {
		for _, rc := range rawContracts {
			if cm, ok := rc.(map[string]any); ok {
				contracts = append(contracts, transformContract(cm))
			}
		}
	}

	tags := make([]any, 0)
	if rawTags, ok := e["tags"].([]any); ok {
		for _, t := range rawTags {
			if s, ok := t.(string); ok {
				tags = append(tags, s)
			}
		}
	}

	var subcategory map[string]any
	if raw, ok := e["subcategory"].(map[string]any); ok {
		subcategory = map[string]any{
			"id":   intVal(raw, "id"),
			"slug": stringVal(raw, "slug"),
			"name": stringVal(raw, "name"),
		}
	}

	result := map[string]any{
		"id":             stringVal(e, "id"),
		"title":          stringVal(e, "title"),
		"slug":           stringVal(e, "slug"),
		"description":    stringVal(e, "description"),
		"image_url":      stringVal(e, "imageUrl"),
		"type":           stringVal(e, "type"),
		"category":       stringVal(e, "category"),
		"series":         stringVal(e, "series"),
		"ticker":         stringVal(e, "ticker"),
		"status":         stringVal(e, "status"),
		"resolved_at":    stringVal(e, "resolvedAt"),
		"created_at":     stringVal(e, "createdAt"),
		"contracts":      contracts,
		"volume":         stringVal(e, "volume"),
		"volume_24h":     stringVal(e, "volume24h"),
		"tags":           tags,
		"expiry_date":    stringVal(e, "expiryDate"),
		"effective_date": stringVal(e, "effectiveDate"),
		"is_live":        boolVal(e, "isLive"),
		"template":       stringVal(e, "template"),
	}

	if subcategory != nil {
		result["subcategory"] = subcategory
	}

	return result
}

// extractEvents extracts the "data" array from an API response envelope.
func extractEvents(payload map[string]any) []map[string]any {
	data, ok := payload["data"]
	if !ok {
		return nil
	}
	switch d := data.(type) {
	case []any:
		result := make([]map[string]any, 0, len(d))
		for _, v := range d {
			if m, ok := v.(map[string]any); ok {
				result = append(result, m)
			}
		}
		return result
	case map[string]any:
		return []map[string]any{d}
	}
	return nil
}

// ListEvents returns prediction market events with optional filters.
func (s *GeminiPredictionsService) ListEvents(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if status := getString(fields, "status", ""); status != "" {
		params.Set("status", status)
	}
	if category := getString(fields, "category", ""); category != "" {
		params.Set("category", category)
	}

	payload, err := s.get("/v1/prediction-markets/events", params)
	if err != nil {
		return nil, err
	}

	rawEvents := extractEvents(payload)
	events := make([]any, 0, len(rawEvents))
	for _, e := range rawEvents {
		events = append(events, transformEvent(e))
	}

	return toStruct(map[string]any{"events": events})
}

// GetEvent returns a single prediction market event by ticker.
func (s *GeminiPredictionsService) GetEvent(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	ticker := getString(fields, "event_ticker", "")
	if ticker == "" {
		return nil, fmt.Errorf("event_ticker is required")
	}

	path := fmt.Sprintf("/v1/prediction-markets/events/%s", url.PathEscape(ticker))
	payload, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}

	// The single-event endpoint may return the event directly or wrapped in "data".
	eventData := payload
	if data, ok := payload["data"].(map[string]any); ok {
		eventData = data
	}
	// If "data" is an array with one element, unwrap it.
	if dataArr, ok := payload["data"].([]any); ok && len(dataArr) == 1 {
		if m, ok := dataArr[0].(map[string]any); ok {
			eventData = m
		}
	}

	event := transformEvent(eventData)
	return toStruct(map[string]any{"event": event})
}

// ListNewlyListedEvents returns newly listed prediction market events.
func (s *GeminiPredictionsService) ListNewlyListedEvents(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	payload, err := s.get("/v1/prediction-markets/events/newly-listed", nil)
	if err != nil {
		return nil, err
	}

	rawEvents := extractEvents(payload)
	events := make([]any, 0, len(rawEvents))
	for _, e := range rawEvents {
		events = append(events, transformEvent(e))
	}

	return toStruct(map[string]any{"events": events})
}

// ListRecentlySettledEvents returns recently settled prediction market events.
func (s *GeminiPredictionsService) ListRecentlySettledEvents(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	payload, err := s.get("/v1/prediction-markets/events/recently-settled", nil)
	if err != nil {
		return nil, err
	}

	rawEvents := extractEvents(payload)
	events := make([]any, 0, len(rawEvents))
	for _, e := range rawEvents {
		events = append(events, transformEvent(e))
	}

	return toStruct(map[string]any{"events": events})
}

// ListUpcomingEvents returns upcoming prediction market events.
func (s *GeminiPredictionsService) ListUpcomingEvents(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	payload, err := s.get("/v1/prediction-markets/events/upcoming", nil)
	if err != nil {
		return nil, err
	}

	rawEvents := extractEvents(payload)
	events := make([]any, 0, len(rawEvents))
	for _, e := range rawEvents {
		events = append(events, transformEvent(e))
	}

	return toStruct(map[string]any{"events": events})
}

// ListCategories returns available prediction market categories.
func (s *GeminiPredictionsService) ListCategories(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	payload, err := s.get("/v1/prediction-markets/categories", nil)
	if err != nil {
		return nil, err
	}

	categories := make([]any, 0)
	if raw, ok := payload["categories"].([]any); ok {
		for _, c := range raw {
			if s, ok := c.(string); ok {
				categories = append(categories, s)
			}
		}
	}

	return toStruct(map[string]any{"categories": categories})
}

// stringVal returns a string value from a map, defaulting to "".
func stringVal(m map[string]any, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
		if v != nil {
			return fmt.Sprintf("%v", v)
		}
	}
	return ""
}

// intVal returns an int64 value from a map, handling both float64 and string.
func intVal(m map[string]any, key string) int64 {
	if v, ok := m[key]; ok {
		switch n := v.(type) {
		case float64:
			return int64(n)
		case int:
			return int64(n)
		case int64:
			return n
		}
	}
	return 0
}

// boolVal returns a bool value from a map, defaulting to false.
func boolVal(m map[string]any, key string) bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return false
}

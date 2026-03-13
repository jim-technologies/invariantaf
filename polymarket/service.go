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

// PolymarketService implements the PolymarketGammaService,
// PolymarketClobService, and PolymarketDataService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response.
type PolymarketService struct {
	gammaBaseURL string
	clobBaseURL  string
	dataBaseURL  string
	client       *http.Client
}

// NewPolymarketService creates a new service with default settings.
// No authentication is needed for public endpoints.
func NewPolymarketService() *PolymarketService {
	gammaBase := os.Getenv("POLYMARKET_GAMMA_BASE_URL")
	if gammaBase == "" {
		gammaBase = "https://gamma-api.polymarket.com"
	}
	clobBase := os.Getenv("POLYMARKET_CLOB_BASE_URL")
	if clobBase == "" {
		clobBase = "https://clob.polymarket.com"
	}
	dataBase := os.Getenv("POLYMARKET_DATA_BASE_URL")
	if dataBase == "" {
		dataBase = "https://data-api.polymarket.com"
	}
	return &PolymarketService{
		gammaBaseURL: gammaBase,
		clobBaseURL:  clobBase,
		dataBaseURL:  dataBase,
		client:       &http.Client{},
	}
}

// get performs a GET request to the given base URL + path and returns the
// decoded JSON. Handles both JSON object and array responses.
func (s *PolymarketService) get(baseURL, path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", baseURL, path)
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
			result = map[string]any{"data": arr}
		} else {
			return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
		}
	}

	return result, nil
}

// getString gets a string field from structpb, with a default.
func getString(fields map[string]*structpb.Value, key, def string) string {
	if v, ok := fields[key]; ok && v.GetStringValue() != "" {
		return v.GetStringValue()
	}
	return def
}

// getInt gets an int field from structpb (numbers come as float64).
func getInt(fields map[string]*structpb.Value, key string) int64 {
	if v, ok := fields[key]; ok {
		return int64(v.GetNumberValue())
	}
	return 0
}

// getFloat gets a float field from structpb.
func getFloat(fields map[string]*structpb.Value, key string) float64 {
	if v, ok := fields[key]; ok {
		return v.GetNumberValue()
	}
	return 0
}

// getBool gets a bool field from structpb.
func getBool(fields map[string]*structpb.Value, key string) (bool, bool) {
	if v, ok := fields[key]; ok {
		return v.GetBoolValue(), true
	}
	return false, false
}

// toStruct converts an API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// --- PolymarketGammaService RPCs ---

// Search searches markets, events, and profiles via the Gamma API.
func (s *PolymarketService) Search(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	q := getString(fields, "q", "")
	if q == "" {
		return nil, fmt.Errorf("q is required")
	}

	params := url.Values{}
	params.Set("q", q)
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if offset := getInt(fields, "offset"); offset > 0 {
		params.Set("offset", strconv.FormatInt(offset, 10))
	}

	data, err := s.get(s.gammaBaseURL, "/public-search", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ListEvents lists events with optional pagination and filters via the Gamma API.
func (s *PolymarketService) ListEvents(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()

	params := url.Values{}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if offset := getInt(fields, "offset"); offset > 0 {
		params.Set("offset", strconv.FormatInt(offset, 10))
	}
	if active, ok := getBool(fields, "active"); ok {
		params.Set("active", strconv.FormatBool(active))
	}
	if closed, ok := getBool(fields, "closed"); ok {
		params.Set("closed", strconv.FormatBool(closed))
	}
	if tag := getString(fields, "tag", ""); tag != "" {
		params.Set("tag", tag)
	}
	if order := getString(fields, "order", ""); order != "" {
		params.Set("order", order)
	}

	data, err := s.get(s.gammaBaseURL, "/events", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetEvent gets a single event by slug via the Gamma API.
func (s *PolymarketService) GetEvent(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	slug := getString(fields, "slug", "")
	if slug == "" {
		return nil, fmt.Errorf("slug is required")
	}

	path := fmt.Sprintf("/events/slug/%s", url.PathEscape(slug))
	data, err := s.get(s.gammaBaseURL, path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetEventById gets a single event by ID via the Gamma API.
func (s *PolymarketService) GetEventById(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getString(fields, "id", "")
	if id == "" {
		return nil, fmt.Errorf("id is required")
	}

	path := fmt.Sprintf("/events/%s", url.PathEscape(id))
	data, err := s.get(s.gammaBaseURL, path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetMarket lists markets with optional filters via the Gamma API.
func (s *PolymarketService) GetMarket(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()

	params := url.Values{}
	if slug := getString(fields, "slug", ""); slug != "" {
		params.Set("slug", slug)
	}
	if conditionID := getString(fields, "condition_id", ""); conditionID != "" {
		params.Set("condition_id", conditionID)
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if offset := getInt(fields, "offset"); offset > 0 {
		params.Set("offset", strconv.FormatInt(offset, 10))
	}
	if active, ok := getBool(fields, "active"); ok {
		params.Set("active", strconv.FormatBool(active))
	}
	if closed, ok := getBool(fields, "closed"); ok {
		params.Set("closed", strconv.FormatBool(closed))
	}

	data, err := s.get(s.gammaBaseURL, "/markets", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetMarketById gets a single market by ID via the Gamma API.
func (s *PolymarketService) GetMarketById(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getString(fields, "id", "")
	if id == "" {
		return nil, fmt.Errorf("id is required")
	}

	path := fmt.Sprintf("/markets/%s", url.PathEscape(id))
	data, err := s.get(s.gammaBaseURL, path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// --- PolymarketClobService RPCs (public endpoints) ---

// GetOrderbook gets orderbook levels for a token ID via the CLOB API.
func (s *PolymarketService) GetOrderbook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tokenID := getString(fields, "token_id", "")
	if tokenID == "" {
		return nil, fmt.Errorf("token_id is required")
	}

	params := url.Values{}
	params.Set("token_id", tokenID)

	data, err := s.get(s.clobBaseURL, "/book", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPrice gets the best price for a token ID and side via the CLOB API.
func (s *PolymarketService) GetPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tokenID := getString(fields, "token_id", "")
	if tokenID == "" {
		return nil, fmt.Errorf("token_id is required")
	}
	side := getString(fields, "side", "")
	if side == "" {
		return nil, fmt.Errorf("side is required")
	}

	params := url.Values{}
	params.Set("token_id", tokenID)
	params.Set("side", side)

	data, err := s.get(s.clobBaseURL, "/price", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetMidpoint gets the midpoint for a token ID via the CLOB API.
func (s *PolymarketService) GetMidpoint(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tokenID := getString(fields, "token_id", "")
	if tokenID == "" {
		return nil, fmt.Errorf("token_id is required")
	}

	params := url.Values{}
	params.Set("token_id", tokenID)

	data, err := s.get(s.clobBaseURL, "/midpoint", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetSpread gets the spread for a token ID via the CLOB API.
func (s *PolymarketService) GetSpread(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tokenID := getString(fields, "token_id", "")
	if tokenID == "" {
		return nil, fmt.Errorf("token_id is required")
	}

	params := url.Values{}
	params.Set("token_id", tokenID)

	data, err := s.get(s.clobBaseURL, "/spread", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPriceHistory gets historical prices for a token ID via the CLOB API.
func (s *PolymarketService) GetPriceHistory(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()

	params := url.Values{}
	if market := getString(fields, "market", ""); market != "" {
		params.Set("market", market)
	}
	if interval := getString(fields, "interval", ""); interval != "" {
		params.Set("interval", interval)
	}
	if fidelity := getInt(fields, "fidelity"); fidelity > 0 {
		params.Set("fidelity", strconv.FormatInt(fidelity, 10))
	}
	if startTs := getInt(fields, "startTs"); startTs > 0 {
		params.Set("startTs", strconv.FormatInt(startTs, 10))
	}
	if endTs := getInt(fields, "endTs"); endTs > 0 {
		params.Set("endTs", strconv.FormatInt(endTs, 10))
	}

	data, err := s.get(s.clobBaseURL, "/prices-history", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// PlaceOrder places an order. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) PlaceOrder(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("PlaceOrder requires CLOB L2 authentication; use the Python implementation")
}

// CreateAndPostOrder creates and posts an order. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) CreateAndPostOrder(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("CreateAndPostOrder requires CLOB L2 authentication; use the Python implementation")
}

// CancelOrder cancels an order. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) CancelOrder(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("CancelOrder requires CLOB L2 authentication; use the Python implementation")
}

// CancelAllOrders cancels all orders. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) CancelAllOrders(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("CancelAllOrders requires CLOB L2 authentication; use the Python implementation")
}

// GetOpenOrders gets open orders. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) GetOpenOrders(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("GetOpenOrders requires CLOB L2 authentication; use the Python implementation")
}

// GetTrades gets trades. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) GetTrades(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("GetTrades requires CLOB L2 authentication; use the Python implementation")
}

// GetBalance gets balance and allowance. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) GetBalance(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("GetBalance requires CLOB L2 authentication; use the Python implementation")
}

// GetBalanceAllowance gets balance and allowance. Requires CLOB L2 auth (not supported in Go implementation).
func (s *PolymarketService) GetBalanceAllowance(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	return nil, fmt.Errorf("GetBalanceAllowance requires CLOB L2 authentication; use the Python implementation")
}

// --- PolymarketDataService RPCs ---

// GetPositions gets positions for a user wallet via the Data API.
func (s *PolymarketService) GetPositions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	user := getString(fields, "user", "")
	if user == "" {
		return nil, fmt.Errorf("user is required")
	}

	params := url.Values{}
	params.Set("user", user)
	if sizeThreshold := getFloat(fields, "sizeThreshold"); sizeThreshold > 0 {
		params.Set("sizeThreshold", strconv.FormatFloat(sizeThreshold, 'f', -1, 64))
	}
	if market := getString(fields, "market", ""); market != "" {
		params.Set("market", market)
	}
	if eventID := getString(fields, "eventId", ""); eventID != "" {
		params.Set("eventId", eventID)
	}

	data, err := s.get(s.dataBaseURL, "/positions", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetLeaderboard gets leaderboard entries via the Data API.
func (s *PolymarketService) GetLeaderboard(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()

	params := url.Values{}
	if interval := getString(fields, "interval", ""); interval != "" {
		params.Set("interval", interval)
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}
	if offset := getInt(fields, "offset"); offset > 0 {
		params.Set("offset", strconv.FormatInt(offset, 10))
	}

	data, err := s.get(s.dataBaseURL, "/v1/leaderboard", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

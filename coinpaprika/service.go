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

// CoinpaprikaService implements the CoinPaprikaService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type CoinpaprikaService struct {
	baseURL string
	client  *http.Client
}

// NewCoinpaprikaService creates a new service with default settings.
// The CoinPaprika API requires no authentication for public endpoints.
func NewCoinpaprikaService() *CoinpaprikaService {
	base := os.Getenv("COINPAPRIKA_BASE_URL")
	if base == "" {
		base = "https://api.coinpaprika.com/v1"
	}
	return &CoinpaprikaService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// get performs a GET request to the CoinPaprika API and returns the decoded
// JSON as a map. If the API returns a JSON array, it is wrapped in
// {"items": arr} so callers always get a map.
func (s *CoinpaprikaService) get(path string, params url.Values) (map[string]any, error) {
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

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// transformTicker flattens quotes.USD into quotes_usd for protobuf mapping.
func transformTicker(data map[string]any) map[string]any {
	result := make(map[string]any, len(data))
	for k, v := range data {
		result[k] = v
	}
	quotes, ok := result["quotes"]
	if !ok {
		return result
	}
	delete(result, "quotes")
	quotesMap, ok := quotes.(map[string]any)
	if !ok {
		return result
	}
	if usd, ok := quotesMap["USD"]; ok {
		result["quotes_usd"] = usd
	}
	return result
}

// transformMarket flattens quotes.USD into quotes_usd for protobuf mapping.
func transformMarket(data map[string]any) map[string]any {
	result := make(map[string]any, len(data))
	for k, v := range data {
		result[k] = v
	}
	quotes, ok := result["quotes"]
	if !ok {
		return result
	}
	delete(result, "quotes")
	quotesMap, ok := quotes.(map[string]any)
	if !ok {
		return result
	}
	if usd, ok := quotesMap["USD"]; ok {
		result["quotes_usd"] = usd
	}
	return result
}

// GetGlobal gets global crypto market statistics.
func (s *CoinpaprikaService) GetGlobal(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/global", nil)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// ListCoins lists all coins.
func (s *CoinpaprikaService) ListCoins(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/coins", nil)
	if err != nil {
		return nil, err
	}

	// The API returns a JSON array; our get() wraps it in {"items": arr}.
	coins, ok := data["items"]
	if !ok {
		coins = []any{}
	}
	return toStruct(map[string]any{"coins": coins})
}

// GetCoinById gets detailed info for a specific coin.
func (s *CoinpaprikaService) GetCoinById(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	coinID := getString(fields, "coin_id", "")
	if coinID == "" {
		return nil, fmt.Errorf("coin_id is required")
	}

	data, err := s.get(fmt.Sprintf("/coins/%s", coinID), nil)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTickerById gets ticker (price data) for a specific coin.
func (s *CoinpaprikaService) GetTickerById(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	coinID := getString(fields, "coin_id", "")
	if coinID == "" {
		return nil, fmt.Errorf("coin_id is required")
	}

	data, err := s.get(fmt.Sprintf("/tickers/%s", coinID), nil)
	if err != nil {
		return nil, err
	}
	return toStruct(transformTicker(data))
}

// ListTickers lists all tickers.
func (s *CoinpaprikaService) ListTickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/tickers", nil)
	if err != nil {
		return nil, err
	}

	// The API returns a JSON array; our get() wraps it in {"items": arr}.
	tickersRaw, ok := data["items"]
	if !ok {
		tickersRaw = []any{}
	}
	tickersList, ok := tickersRaw.([]any)
	if !ok {
		tickersList = []any{}
	}

	tickers := make([]any, len(tickersList))
	for i, t := range tickersList {
		if m, ok := t.(map[string]any); ok {
			tickers[i] = transformTicker(m)
		} else {
			tickers[i] = t
		}
	}
	return toStruct(map[string]any{"tickers": tickers})
}

// GetCoinMarkets gets markets/exchanges where a coin is traded.
func (s *CoinpaprikaService) GetCoinMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	coinID := getString(fields, "coin_id", "")
	if coinID == "" {
		return nil, fmt.Errorf("coin_id is required")
	}

	data, err := s.get(fmt.Sprintf("/coins/%s/markets", coinID), nil)
	if err != nil {
		return nil, err
	}

	// The API returns a JSON array; our get() wraps it in {"items": arr}.
	marketsRaw, ok := data["items"]
	if !ok {
		marketsRaw = []any{}
	}
	marketsList, ok := marketsRaw.([]any)
	if !ok {
		marketsList = []any{}
	}

	markets := make([]any, len(marketsList))
	for i, m := range marketsList {
		if mm, ok := m.(map[string]any); ok {
			markets[i] = transformMarket(mm)
		} else {
			markets[i] = m
		}
	}
	return toStruct(map[string]any{"markets": markets})
}

// GetCoinOHLCV gets latest OHLCV data for a coin.
func (s *CoinpaprikaService) GetCoinOHLCV(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	coinID := getString(fields, "coin_id", "")
	if coinID == "" {
		return nil, fmt.Errorf("coin_id is required")
	}

	data, err := s.get(fmt.Sprintf("/coins/%s/ohlcv/latest/", coinID), nil)
	if err != nil {
		return nil, err
	}

	// The API returns a JSON array; our get() wraps it in {"items": arr}.
	entries, ok := data["items"]
	if !ok {
		entries = []any{}
	}
	return toStruct(map[string]any{"entries": entries})
}

// SearchCoins searches coins by query string.
func (s *CoinpaprikaService) SearchCoins(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := getString(fields, "query", "")
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{}
	params.Set("q", query)
	params.Set("c", "currencies")

	data, err := s.get("/search/", params)
	if err != nil {
		return nil, err
	}

	currencies, ok := data["currencies"]
	if !ok {
		currencies = []any{}
	}
	return toStruct(map[string]any{"currencies": currencies})
}

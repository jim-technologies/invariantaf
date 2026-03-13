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

// USGovDataService implements the USGovDataService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type USGovDataService struct {
	baseURL string
	client  *http.Client
}

// NewUSGovDataService creates a new service with default settings.
// No authentication is required for the Treasury Fiscal Data API.
func NewUSGovDataService() *USGovDataService {
	return &USGovDataService{
		baseURL: "https://api.fiscaldata.treasury.gov/services/api/fiscal_service",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Treasury Fiscal Data API and returns the decoded JSON.
func (s *USGovDataService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array.
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

// GetDebtToThePenny returns the most recent US national debt records.
func (s *USGovDataService) GetDebtToThePenny(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("sort", "-record_date")

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("page[size]", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("page[size]", "10")
	}

	data, err := s.get("/v2/accounting/od/debt_to_penny", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTreasuryYields returns average interest rates on Treasury securities.
func (s *USGovDataService) GetTreasuryYields(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("sort", "-record_date")

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("page[size]", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("page[size]", "10")
	}

	data, err := s.get("/v2/accounting/od/avg_interest_rates", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTreasuryAuctions returns recent Treasury securities auction data.
func (s *USGovDataService) GetTreasuryAuctions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("sort", "-record_date")

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("page[size]", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("page[size]", "10")
	}

	data, err := s.get("/v1/accounting/od/securities_sales", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetExchangeRates returns Treasury exchange rates for foreign currencies.
func (s *USGovDataService) GetExchangeRates(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("sort", "-record_date")

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("page[size]", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("page[size]", "10")
	}

	data, err := s.get("/v1/accounting/od/rates_of_exchange", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFederalSpending returns monthly federal spending data from the MTS.
func (s *USGovDataService) GetFederalSpending(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("sort", "-record_date")

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("page[size]", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("page[size]", "10")
	}

	data, err := s.get("/v1/accounting/mts/mts_table_5", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

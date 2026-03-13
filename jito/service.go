package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync/atomic"

	"google.golang.org/protobuf/types/known/structpb"
)

// JitoService implements the JitoService RPCs defined in the proto descriptor.
// Each method takes a structpb.Struct request and returns a structpb.Struct
// response, allowing the invariant protocol SDK to handle serialization and
// deserialization transparently.
type JitoService struct {
	bundleURL  string // POST endpoint for JSON-RPC (sendBundle, getBundleStatuses)
	tipFloorURL string // GET endpoint for tip floor
	client     *http.Client
	rpcID      atomic.Int64
}

// NewJitoService creates a new service with default production URLs.
// No authentication is required for Jito APIs.
func NewJitoService() *JitoService {
	return &JitoService{
		bundleURL:   "https://mainnet.block-engine.jito.wtf/api/v1/bundles",
		tipFloorURL: "https://bundles.jito.wtf/api/v1/bundles/tip_floor",
		client:      &http.Client{},
	}
}

// jsonRPCRequest is the standard JSON-RPC 2.0 request envelope.
type jsonRPCRequest struct {
	JSONRPC string `json:"jsonrpc"`
	ID      int64  `json:"id"`
	Method  string `json:"method"`
	Params  []any  `json:"params"`
}

// jsonRPCResponse is the standard JSON-RPC 2.0 response envelope.
type jsonRPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *jsonRPCError   `json:"error,omitempty"`
}

// jsonRPCError represents a JSON-RPC error object.
type jsonRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// rpcCall performs a JSON-RPC 2.0 call to the bundle engine.
func (s *JitoService) rpcCall(method string, params []any) (json.RawMessage, error) {
	id := s.rpcID.Add(1)
	reqBody := jsonRPCRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}

	data, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal rpc request: %w", err)
	}

	req, err := http.NewRequest("POST", s.bundleURL, bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

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

	var rpcResp jsonRPCResponse
	if err := json.Unmarshal(body, &rpcResp); err != nil {
		return nil, fmt.Errorf("decode rpc response: %w (body: %s)", err, string(body))
	}

	if rpcResp.Error != nil {
		return nil, fmt.Errorf("rpc error (code %d): %s", rpcResp.Error.Code, rpcResp.Error.Message)
	}

	return rpcResp.Result, nil
}

// getTipFloorRaw performs a GET request to the tip floor REST endpoint.
func (s *JitoService) getTipFloorRaw() ([]byte, error) {
	req, err := http.NewRequest("GET", s.tipFloorURL, nil)
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

	return body, nil
}

// helper: get a string field from structpb, with a default.
func getString(fields map[string]*structpb.Value, key, def string) string {
	if v, ok := fields[key]; ok && v.GetStringValue() != "" {
		return v.GetStringValue()
	}
	return def
}

// helper: get a string list from structpb.
func getStringList(fields map[string]*structpb.Value, key string) []string {
	v, ok := fields[key]
	if !ok {
		return nil
	}
	lv := v.GetListValue()
	if lv == nil {
		return nil
	}
	var result []string
	for _, item := range lv.GetValues() {
		if s := item.GetStringValue(); s != "" {
			result = append(result, s)
		}
	}
	return result
}

// helper: convert map to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// SendBundle submits a bundle of base58-encoded signed transactions.
func (s *JitoService) SendBundle(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	transactions := getStringList(fields, "transactions")
	if len(transactions) == 0 {
		return nil, fmt.Errorf("transactions is required (list of base58-encoded signed transactions)")
	}

	// sendBundle params: [ [tx1, tx2, ...] ]
	result, err := s.rpcCall("sendBundle", []any{transactions})
	if err != nil {
		return nil, err
	}

	// Result is a string (the bundle ID).
	var bundleID string
	if err := json.Unmarshal(result, &bundleID); err != nil {
		return nil, fmt.Errorf("decode bundle id: %w (raw: %s)", err, string(result))
	}

	return toStruct(map[string]any{
		"bundle_id": bundleID,
	})
}

// GetBundleStatuses retrieves the processing status of submitted bundles.
func (s *JitoService) GetBundleStatuses(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	bundleIDs := getStringList(fields, "bundle_ids")
	if len(bundleIDs) == 0 {
		return nil, fmt.Errorf("bundle_ids is required (list of bundle ID strings)")
	}

	// getBundleStatuses params: [ [id1, id2, ...] ]
	result, err := s.rpcCall("getBundleStatuses", []any{bundleIDs})
	if err != nil {
		return nil, err
	}

	// Result is an object with a "value" key containing an array of statuses.
	var parsed map[string]any
	if err := json.Unmarshal(result, &parsed); err != nil {
		return nil, fmt.Errorf("decode statuses: %w (raw: %s)", err, string(result))
	}

	// Normalize: extract the "value" array into "statuses".
	var statuses []any
	if value, ok := parsed["value"]; ok {
		if arr, ok := value.([]any); ok {
			statuses = arr
		}
	}

	return toStruct(map[string]any{
		"statuses": statuses,
	})
}

// GetTipFloor retrieves the current minimum tip amounts for bundle inclusion.
func (s *JitoService) GetTipFloor(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	body, err := s.getTipFloorRaw()
	if err != nil {
		return nil, err
	}

	// The tip floor endpoint returns an array of entries.
	var entries []any
	if err := json.Unmarshal(body, &entries); err != nil {
		return nil, fmt.Errorf("decode tip floor: %w (body: %s)", err, string(body))
	}

	return toStruct(map[string]any{
		"entries": entries,
	})
}

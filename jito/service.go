package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"sync/atomic"

	"google.golang.org/protobuf/types/known/structpb"
)

// JitoService implements the JitoService RPCs defined in the proto descriptor.
// Generated typed RPC adapters pass canonical requests to the provider boundary.
// Raw response JSON preserves integer precision until typed protobuf decoding.
type JitoService struct {
	bundleURL   string // POST endpoint for JSON-RPC (sendBundle, getBundleStatuses)
	tipFloorURL string // GET endpoint for tip floor
	client      *http.Client
	rpcID       atomic.Int64
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
	if err := decodeProviderJSON(body, &rpcResp); err != nil {
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
func responseJSON(data map[string]any) (json.RawMessage, error) {
	return json.Marshal(data)
}

// SendBundle submits a bundle of base58-encoded signed transactions.
func (s *JitoService) SendBundle(_ context.Context, req *structpb.Struct) (json.RawMessage, error) {
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
	if err := decodeProviderJSON(result, &bundleID); err != nil {
		return nil, fmt.Errorf("decode bundle id: %w (raw: %s)", err, string(result))
	}

	return responseJSON(map[string]any{
		"bundle_id": bundleID,
	})
}

// GetBundleStatuses retrieves the processing status of submitted bundles.
func (s *JitoService) GetBundleStatuses(_ context.Context, req *structpb.Struct) (json.RawMessage, error) {
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
	if err := decodeProviderJSON(result, &parsed); err != nil {
		return nil, fmt.Errorf("decode statuses: %w (raw: %s)", err, string(result))
	}

	// Normalize: extract the "value" array into "statuses".
	for key := range parsed {
		if key != "value" && key != "context" {
			return nil, fmt.Errorf("unknown bundle status envelope field: %s", key)
		}
	}
	if rawContext, exists := parsed["context"]; exists {
		context, ok := rawContext.(map[string]any)
		if !ok || len(context) != 1 {
			return nil, fmt.Errorf("bundle status context must contain only slot")
		}
		slot, ok := context["slot"].(json.Number)
		if !ok {
			return nil, fmt.Errorf("bundle status context slot must be an unsigned integer")
		}
		if _, err := strconv.ParseUint(slot.String(), 10, 64); err != nil {
			return nil, fmt.Errorf("bundle status context slot must be an unsigned integer")
		}
	}
	arr, ok := parsed["value"].([]any)
	if !ok {
		return nil, fmt.Errorf("bundle status value must be an array")
	}
	statuses := make([]any, 0, len(arr))
	for _, entry := range arr {
		row, ok := entry.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("bundle status must be an object")
		}
		for key, value := range row {
			switch key {
			case "bundle_id", "status", "confirmation_status", "confirmationStatus", "landed_slot", "slot", "error", "err":
			case "transactions":
				transactions, ok := value.([]any)
				if !ok {
					return nil, fmt.Errorf("bundle status transactions must be an array")
				}
				for _, transaction := range transactions {
					if _, ok := transaction.(string); !ok {
						return nil, fmt.Errorf("bundle status transaction must be a string")
					}
				}
			default:
				return nil, fmt.Errorf("unknown bundle status field: %s", key)
			}
		}
		status := row["status"]
		if status == nil {
			status = row["confirmation_status"]
		}
		if status == nil {
			status = row["confirmationStatus"]
		}
		slot := row["landed_slot"]
		if slot == nil {
			slot = row["slot"]
		}
		errorInfo := row["error"]
		if errorInfo == nil {
			errorInfo = row["err"]
		}
		if errorInfo != nil {
			if _, ok := errorInfo.(string); !ok {
				body, err := json.Marshal(errorInfo)
				if err != nil {
					return nil, err
				}
				errorInfo = string(body)
			}
		}
		statuses = append(statuses, map[string]any{
			"bundle_id": row["bundle_id"], "status": status,
			"landed_slot": slot, "error": errorInfo,
		})
	}

	return responseJSON(map[string]any{
		"statuses": statuses,
	})
}

// GetTipFloor retrieves the current minimum tip amounts for bundle inclusion.
func (s *JitoService) GetTipFloor(_ context.Context, _ *structpb.Struct) (json.RawMessage, error) {
	body, err := s.getTipFloorRaw()
	if err != nil {
		return nil, err
	}

	// The tip floor endpoint returns an array of entries.
	var entries []any
	if err := decodeProviderJSON(body, &entries); err != nil {
		return nil, fmt.Errorf("decode tip floor: %w (body: %s)", err, string(body))
	}

	return responseJSON(map[string]any{
		"entries": entries,
	})
}

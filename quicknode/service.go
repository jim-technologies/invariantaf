package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync/atomic"

	pb "github.com/jim-technologies/invariantaf/quicknode/quicknode/v1"
)

// quickNodeClient holds shared HTTP plumbing for all QuickNode services.
type quickNodeClient struct {
	apiBaseURL  string // https://api.quicknode.com (REST platform APIs)
	endpointURL string // user's RPC endpoint URL (enhanced RPC methods)
	apiKey      string
	client      *http.Client
	rpcID       atomic.Int64
}

func newQuickNodeClient() *quickNodeClient {
	apiBase := os.Getenv("QUICKNODE_API_BASE_URL")
	if apiBase == "" {
		apiBase = "https://api.quicknode.com"
	}
	return &quickNodeClient{
		apiBaseURL:  strings.TrimRight(apiBase, "/"),
		endpointURL: os.Getenv("QUICKNODE_ENDPOINT_URL"),
		apiKey:      os.Getenv("QUICKNODE_API_KEY"),
		client:      &http.Client{},
	}
}

// ─── HTTP helpers ────────────────────────────────────────────────────────────

func (c *quickNodeClient) doREST(method, path string, body any) (map[string]any, error) {
	u := c.apiBaseURL + path
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(data)
	}
	req, err := http.NewRequest(method, u, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		req.Header.Set("x-api-key", c.apiKey)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http %s %s: %w", method, path, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("quicknode api returned %d: %s", resp.StatusCode, string(raw))
	}
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	var result map[string]any
	if err := json.Unmarshal(raw, &result); err != nil {
		// try parsing as array
		var arr []any
		if err2 := json.Unmarshal(raw, &arr); err2 == nil {
			return map[string]any{"data": arr}, nil
		}
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

func (c *quickNodeClient) restGET(path string, params url.Values) (map[string]any, error) {
	if len(params) > 0 {
		path += "?" + params.Encode()
	}
	return c.doREST(http.MethodGet, path, nil)
}

func (c *quickNodeClient) restPOST(path string, body any) (map[string]any, error) {
	return c.doREST(http.MethodPost, path, body)
}

func (c *quickNodeClient) restPATCH(path string, body any) (map[string]any, error) {
	return c.doREST(http.MethodPatch, path, body)
}

func (c *quickNodeClient) restPUT(path string, body any) (map[string]any, error) {
	return c.doREST(http.MethodPut, path, body)
}

func (c *quickNodeClient) restDELETE(path string) (map[string]any, error) {
	return c.doREST(http.MethodDelete, path, nil)
}

// jsonRPC sends a JSON-RPC 2.0 request to the user's endpoint URL.
func (c *quickNodeClient) jsonRPC(method string, params any) (map[string]any, error) {
	if c.endpointURL == "" {
		return nil, fmt.Errorf("QUICKNODE_ENDPOINT_URL is required for %s; set it to your QuickNode endpoint URL", method)
	}
	id := c.rpcID.Add(1)
	payload := map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
		"params":  params,
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal rpc: %w", err)
	}
	resp, err := c.client.Post(c.endpointURL, "application/json", bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("rpc %s: %w", method, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read rpc body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("rpc %s returned %d: %s", method, resp.StatusCode, string(raw))
	}
	var result map[string]any
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, fmt.Errorf("decode rpc json: %w", err)
	}
	if errObj, ok := result["error"]; ok && errObj != nil {
		return nil, fmt.Errorf("rpc %s error: %v", method, errObj)
	}
	res := toMap(result["result"])
	if res == nil {
		// result might be an array or primitive
		return map[string]any{"result": result["result"]}, nil
	}
	return res, nil
}

// ─── Type helpers ────────────────────────────────────────────────────────────

func toStr(v any) string {
	if v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	case bool:
		if t {
			return "true"
		}
		return "false"
	default:
		return fmt.Sprintf("%v", v)
	}
}

func toInt32(v any) int32 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return int32(f)
	}
	return 0
}

func toInt64(v any) int64 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return int64(f)
	}
	return 0
}

func toFloat64(v any) float64 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
}

func toBool(v any) bool {
	if v == nil {
		return false
	}
	if b, ok := v.(bool); ok {
		return b
	}
	return false
}

func toMap(v any) map[string]any {
	if v == nil {
		return nil
	}
	if m, ok := v.(map[string]any); ok {
		return m
	}
	return nil
}

func toSlice(v any) []any {
	if v == nil {
		return nil
	}
	if s, ok := v.([]any); ok {
		return s
	}
	return nil
}

func toStringSlice(v any) []string {
	raw := toSlice(v)
	var out []string
	for _, item := range raw {
		out = append(out, toStr(item))
	}
	return out
}

// ─── Service types ───────────────────────────────────────────────────────────

type QuickNodeConsoleService struct{ *quickNodeClient }
type QuickNodeStreamsService struct{ *quickNodeClient }
type QuickNodeWebhooksService struct{ *quickNodeClient }
type QuickNodeKeyValueService struct{ *quickNodeClient }
type QuickNodeIPFSService struct{ *quickNodeClient }
type QuickNodeTokenNFTService struct{ *quickNodeClient }
type QuickNodeSolanaDASService struct{ *quickNodeClient }

// ═════════════════════════════════════════════════════════════════════════════
// Console Service
// ═════════════════════════════════════════════════════════════════════════════

func (s *QuickNodeConsoleService) ListChains(_ context.Context, _ *pb.ListChainsRequest) (*pb.ListChainsResponse, error) {
	data, err := s.restGET("/v0/chains", nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListChainsResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Chains = append(resp.Chains, &pb.Chain{
			Name:    toStr(m["name"]),
			Network: toStr(m["network"]),
			Status:  toStr(m["status"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) ListEndpoints(_ context.Context, _ *pb.ListEndpointsRequest) (*pb.ListEndpointsResponse, error) {
	data, err := s.restGET("/v0/endpoints", nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListEndpointsResponse{}
	for _, item := range toSlice(data["data"]) {
		resp.Endpoints = append(resp.Endpoints, parseEndpoint(toMap(item)))
	}
	return resp, nil
}

func parseEndpoint(m map[string]any) *pb.Endpoint {
	if m == nil {
		return &pb.Endpoint{}
	}
	return &pb.Endpoint{
		Id:        toStr(m["id"]),
		Name:      toStr(m["name"]),
		Chain:     toStr(m["chain"]),
		Network:   toStr(m["network"]),
		HttpUrl:   toStr(m["http_url"]),
		WssUrl:    toStr(m["wss_url"]),
		Status:    toStr(m["status"]),
		CreatedAt: toStr(m["created_at"]),
		Plan:      toStr(m["plan"]),
	}
}

func (s *QuickNodeConsoleService) CreateEndpoint(_ context.Context, req *pb.CreateEndpointRequest) (*pb.Endpoint, error) {
	body := map[string]any{
		"name":    req.GetName(),
		"chain":   req.GetChain(),
		"network": req.GetNetwork(),
	}
	data, err := s.restPOST("/v0/endpoints", body)
	if err != nil {
		return nil, err
	}
	return parseEndpoint(data), nil
}

func (s *QuickNodeConsoleService) GetEndpoint(_ context.Context, req *pb.GetEndpointRequest) (*pb.Endpoint, error) {
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s", req.GetEndpointId()), nil)
	if err != nil {
		return nil, err
	}
	return parseEndpoint(data), nil
}

func (s *QuickNodeConsoleService) UpdateEndpoint(_ context.Context, req *pb.UpdateEndpointRequest) (*pb.Endpoint, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	data, err := s.restPATCH(fmt.Sprintf("/v0/endpoints/%s", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return parseEndpoint(data), nil
}

func (s *QuickNodeConsoleService) DeleteEndpoint(_ context.Context, req *pb.DeleteEndpointRequest) (*pb.DeleteEndpointResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/v0/endpoints/%s", req.GetEndpointId()))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteEndpointResponse{}, nil
}

func (s *QuickNodeConsoleService) UpdateEndpointStatus(_ context.Context, req *pb.UpdateEndpointStatusRequest) (*pb.Endpoint, error) {
	body := map[string]any{"status": req.GetStatus()}
	data, err := s.restPATCH(fmt.Sprintf("/v0/endpoints/%s/status", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return parseEndpoint(data), nil
}

func (s *QuickNodeConsoleService) GetEndpointMetrics(_ context.Context, req *pb.GetEndpointMetricsRequest) (*pb.GetEndpointMetricsResponse, error) {
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/metrics", req.GetEndpointId()), nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetEndpointMetricsResponse{
		TotalCalls:        toInt64(data["total_calls"]),
		SuccessCount:      toInt64(data["success_count"]),
		ErrorCount:        toInt64(data["error_count"]),
		MaxResponseTimeMs: toFloat64(data["max_response_time_ms"]),
		AvgResponseTimeMs: toFloat64(data["avg_response_time_ms"]),
	}, nil
}

func (s *QuickNodeConsoleService) GetEndpointLogs(_ context.Context, req *pb.GetEndpointLogsRequest) (*pb.GetEndpointLogsResponse, error) {
	params := url.Values{}
	if req.GetFrom() != "" {
		params.Set("from", req.GetFrom())
	}
	if req.GetTo() != "" {
		params.Set("to", req.GetTo())
	}
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/logs", req.GetEndpointId()), params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetEndpointLogsResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Logs = append(resp.Logs, &pb.LogEntry{
			RequestId:      toStr(m["request_id"]),
			Method:         toStr(m["method"]),
			StatusCode:     toInt32(m["status_code"]),
			ResponseTimeMs: toFloat64(m["response_time_ms"]),
			Timestamp:      toStr(m["timestamp"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) GetEndpointLogDetails(_ context.Context, req *pb.GetEndpointLogDetailsRequest) (*pb.LogDetail, error) {
	params := url.Values{}
	params.Set("request_id", req.GetRequestId())
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/log_details", req.GetEndpointId()), params)
	if err != nil {
		return nil, err
	}
	return &pb.LogDetail{
		RequestId:      toStr(data["request_id"]),
		Method:         toStr(data["method"]),
		StatusCode:     toInt32(data["status_code"]),
		ResponseTimeMs: toFloat64(data["response_time_ms"]),
		Timestamp:      toStr(data["timestamp"]),
		RequestBody:    toStr(data["request_body"]),
		ResponseBody:   toStr(data["response_body"]),
	}, nil
}

func (s *QuickNodeConsoleService) GetRPCUsage(_ context.Context, req *pb.GetRPCUsageRequest) (*pb.GetRPCUsageResponse, error) {
	params := url.Values{}
	if req.GetFrom() != "" {
		params.Set("from", req.GetFrom())
	}
	if req.GetTo() != "" {
		params.Set("to", req.GetTo())
	}
	data, err := s.restGET("/v0/usage/rpc", params)
	if err != nil {
		return nil, err
	}
	return &pb.GetRPCUsageResponse{
		TotalCredits:  toInt64(data["total_credits"]),
		TotalRequests: toInt64(data["total_requests"]),
	}, nil
}

func (s *QuickNodeConsoleService) GetRPCUsageByEndpoint(_ context.Context, req *pb.GetRPCUsageRequest) (*pb.GetRPCUsageByEndpointResponse, error) {
	params := url.Values{}
	if req.GetFrom() != "" {
		params.Set("from", req.GetFrom())
	}
	if req.GetTo() != "" {
		params.Set("to", req.GetTo())
	}
	data, err := s.restGET("/v0/usage/rpc/by-endpoint", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetRPCUsageByEndpointResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Endpoints = append(resp.Endpoints, &pb.EndpointUsage{
			EndpointId: toStr(m["endpoint_id"]),
			Name:       toStr(m["name"]),
			Credits:    toInt64(m["credits"]),
			Requests:   toInt64(m["requests"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) GetRPCUsageByMethod(_ context.Context, req *pb.GetRPCUsageRequest) (*pb.GetRPCUsageByMethodResponse, error) {
	params := url.Values{}
	if req.GetFrom() != "" {
		params.Set("from", req.GetFrom())
	}
	if req.GetTo() != "" {
		params.Set("to", req.GetTo())
	}
	data, err := s.restGET("/v0/usage/rpc/by-method", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetRPCUsageByMethodResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Methods = append(resp.Methods, &pb.MethodUsage{
			Method:   toStr(m["method"]),
			Credits:  toInt64(m["credits"]),
			Requests: toInt64(m["requests"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) GetRPCUsageByChain(_ context.Context, req *pb.GetRPCUsageRequest) (*pb.GetRPCUsageByChainResponse, error) {
	params := url.Values{}
	if req.GetFrom() != "" {
		params.Set("from", req.GetFrom())
	}
	if req.GetTo() != "" {
		params.Set("to", req.GetTo())
	}
	data, err := s.restGET("/v0/usage/rpc/by-chain", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetRPCUsageByChainResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Chains = append(resp.Chains, &pb.ChainUsage{
			Chain:    toStr(m["chain"]),
			Network:  toStr(m["network"]),
			Credits:  toInt64(m["credits"]),
			Requests: toInt64(m["requests"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) ListInvoices(_ context.Context, _ *pb.ListInvoicesRequest) (*pb.ListInvoicesResponse, error) {
	data, err := s.restGET("/v0/billing/invoices", nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListInvoicesResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Invoices = append(resp.Invoices, &pb.Invoice{
			Id:       toStr(m["id"]),
			Amount:   toInt64(m["amount"]),
			Currency: toStr(m["currency"]),
			Status:   toStr(m["status"]),
			Date:     toStr(m["date"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) ListPayments(_ context.Context, _ *pb.ListPaymentsRequest) (*pb.ListPaymentsResponse, error) {
	data, err := s.restGET("/v0/billing/payments", nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListPaymentsResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Payments = append(resp.Payments, &pb.Payment{
			Id:       toStr(m["id"]),
			Amount:   toInt64(m["amount"]),
			Currency: toStr(m["currency"]),
			Status:   toStr(m["status"]),
			Date:     toStr(m["date"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) GetMethodRateLimits(_ context.Context, req *pb.GetMethodRateLimitsRequest) (*pb.GetMethodRateLimitsResponse, error) {
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/method-rate-limits", req.GetEndpointId()), nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetMethodRateLimitsResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Limits = append(resp.Limits, &pb.MethodRateLimit{
			Id:     toStr(m["id"]),
			Method: toStr(m["method"]),
			Rps:    toInt32(m["rps"]),
			Rpm:    toInt32(m["rpm"]),
			Rpd:    toInt32(m["rpd"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) UpdateRateLimits(_ context.Context, req *pb.UpdateRateLimitsRequest) (*pb.UpdateRateLimitsResponse, error) {
	body := map[string]any{}
	if req.GetRps() > 0 {
		body["rps"] = req.GetRps()
	}
	if req.GetRpm() > 0 {
		body["rpm"] = req.GetRpm()
	}
	if req.GetRpd() > 0 {
		body["rpd"] = req.GetRpd()
	}
	data, err := s.restPUT(fmt.Sprintf("/v0/endpoints/%s/rate-limits", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.UpdateRateLimitsResponse{
		Rps: toInt32(data["rps"]),
		Rpm: toInt32(data["rpm"]),
		Rpd: toInt32(data["rpd"]),
	}, nil
}

func (s *QuickNodeConsoleService) CreateMethodRateLimit(_ context.Context, req *pb.CreateMethodRateLimitRequest) (*pb.MethodRateLimit, error) {
	body := map[string]any{
		"method": req.GetMethod(),
	}
	if req.GetRps() > 0 {
		body["rps"] = req.GetRps()
	}
	if req.GetRpm() > 0 {
		body["rpm"] = req.GetRpm()
	}
	if req.GetRpd() > 0 {
		body["rpd"] = req.GetRpd()
	}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/method-rate-limits", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.MethodRateLimit{
		Id:     toStr(data["id"]),
		Method: toStr(data["method"]),
		Rps:    toInt32(data["rps"]),
		Rpm:    toInt32(data["rpm"]),
		Rpd:    toInt32(data["rpd"]),
	}, nil
}

func (s *QuickNodeConsoleService) UpdateMethodRateLimit(_ context.Context, req *pb.UpdateMethodRateLimitRequest) (*pb.MethodRateLimit, error) {
	body := map[string]any{}
	if req.GetMethod() != "" {
		body["method"] = req.GetMethod()
	}
	if req.GetRps() > 0 {
		body["rps"] = req.GetRps()
	}
	if req.GetRpm() > 0 {
		body["rpm"] = req.GetRpm()
	}
	if req.GetRpd() > 0 {
		body["rpd"] = req.GetRpd()
	}
	path := fmt.Sprintf("/v0/endpoints/%s/method-rate-limits/%s", req.GetEndpointId(), req.GetMethodRateLimitId())
	data, err := s.restPATCH(path, body)
	if err != nil {
		return nil, err
	}
	return &pb.MethodRateLimit{
		Id:     toStr(data["id"]),
		Method: toStr(data["method"]),
		Rps:    toInt32(data["rps"]),
		Rpm:    toInt32(data["rpm"]),
		Rpd:    toInt32(data["rpd"]),
	}, nil
}

func (s *QuickNodeConsoleService) DeleteMethodRateLimit(_ context.Context, req *pb.DeleteMethodRateLimitRequest) (*pb.DeleteMethodRateLimitResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/method-rate-limits/%s", req.GetEndpointId(), req.GetMethodRateLimitId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteMethodRateLimitResponse{}, nil
}

func (s *QuickNodeConsoleService) GetSecurityOptions(_ context.Context, req *pb.GetSecurityOptionsRequest) (*pb.SecurityOptions, error) {
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/security_options", req.GetEndpointId()), nil)
	if err != nil {
		return nil, err
	}
	return &pb.SecurityOptions{
		TokenAuthEnabled:        toBool(data["token_auth_enabled"]),
		JwtAuthEnabled:          toBool(data["jwt_auth_enabled"]),
		IpAllowlistEnabled:      toBool(data["ip_allowlist_enabled"]),
		ReferrerAllowlistEnabled: toBool(data["referrer_allowlist_enabled"]),
		DomainMaskEnabled:       toBool(data["domain_mask_enabled"]),
	}, nil
}

func (s *QuickNodeConsoleService) UpdateSecurityOptions(_ context.Context, req *pb.UpdateSecurityOptionsRequest) (*pb.SecurityOptions, error) {
	body := map[string]any{
		"token_auth_enabled":         req.GetTokenAuthEnabled(),
		"jwt_auth_enabled":           req.GetJwtAuthEnabled(),
		"ip_allowlist_enabled":       req.GetIpAllowlistEnabled(),
		"referrer_allowlist_enabled": req.GetReferrerAllowlistEnabled(),
		"domain_mask_enabled":        req.GetDomainMaskEnabled(),
	}
	data, err := s.restPATCH(fmt.Sprintf("/v0/endpoints/%s/security_options", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.SecurityOptions{
		TokenAuthEnabled:        toBool(data["token_auth_enabled"]),
		JwtAuthEnabled:          toBool(data["jwt_auth_enabled"]),
		IpAllowlistEnabled:      toBool(data["ip_allowlist_enabled"]),
		ReferrerAllowlistEnabled: toBool(data["referrer_allowlist_enabled"]),
		DomainMaskEnabled:       toBool(data["domain_mask_enabled"]),
	}, nil
}

func (s *QuickNodeConsoleService) CreateDomainMask(_ context.Context, req *pb.CreateDomainMaskRequest) (*pb.DomainMask, error) {
	body := map[string]any{"domain": req.GetDomain()}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/security/domain_masks", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.DomainMask{Id: toStr(data["id"]), Domain: toStr(data["domain"])}, nil
}

func (s *QuickNodeConsoleService) CreateIPAllowlist(_ context.Context, req *pb.CreateIPAllowlistRequest) (*pb.IPAllowlistEntry, error) {
	body := map[string]any{"ip": req.GetIp()}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/security/ips", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.IPAllowlistEntry{Id: toStr(data["id"]), Ip: toStr(data["ip"])}, nil
}

func (s *QuickNodeConsoleService) CreateJWT(_ context.Context, req *pb.CreateJWTRequest) (*pb.JWTEntry, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/security/jwts", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.JWTEntry{Id: toStr(data["id"]), Token: toStr(data["token"]), Name: toStr(data["name"])}, nil
}

func (s *QuickNodeConsoleService) CreateReferrer(_ context.Context, req *pb.CreateReferrerRequest) (*pb.ReferrerEntry, error) {
	body := map[string]any{"referrer": req.GetReferrer()}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/security/referrers", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.ReferrerEntry{Id: toStr(data["id"]), Referrer: toStr(data["referrer"])}, nil
}

func (s *QuickNodeConsoleService) CreateToken(_ context.Context, req *pb.CreateTokenRequest) (*pb.TokenEntry, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/security/tokens", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.TokenEntry{Id: toStr(data["id"]), Token: toStr(data["token"]), Name: toStr(data["name"])}, nil
}

func (s *QuickNodeConsoleService) DeleteDomainMask(_ context.Context, req *pb.DeleteDomainMaskRequest) (*pb.DeleteSecurityEntryResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/security/domain_masks/%s", req.GetEndpointId(), req.GetDomainMaskId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteSecurityEntryResponse{}, nil
}

func (s *QuickNodeConsoleService) DeleteIPAllowlist(_ context.Context, req *pb.DeleteIPAllowlistRequest) (*pb.DeleteSecurityEntryResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/security/ips/%s", req.GetEndpointId(), req.GetIpId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteSecurityEntryResponse{}, nil
}

func (s *QuickNodeConsoleService) DeleteJWT(_ context.Context, req *pb.DeleteJWTRequest) (*pb.DeleteSecurityEntryResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/security/jwts/%s", req.GetEndpointId(), req.GetJwtId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteSecurityEntryResponse{}, nil
}

func (s *QuickNodeConsoleService) DeleteReferrer(_ context.Context, req *pb.DeleteReferrerRequest) (*pb.DeleteSecurityEntryResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/security/referrers/%s", req.GetEndpointId(), req.GetReferrerId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteSecurityEntryResponse{}, nil
}

func (s *QuickNodeConsoleService) DeleteToken(_ context.Context, req *pb.DeleteTokenRequest) (*pb.DeleteSecurityEntryResponse, error) {
	path := fmt.Sprintf("/v0/endpoints/%s/security/tokens/%s", req.GetEndpointId(), req.GetTokenId())
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteSecurityEntryResponse{}, nil
}

func (s *QuickNodeConsoleService) GetEndpointTags(_ context.Context, req *pb.GetEndpointTagsRequest) (*pb.GetEndpointTagsResponse, error) {
	data, err := s.restGET(fmt.Sprintf("/v0/endpoints/%s/tags", req.GetEndpointId()), nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetEndpointTagsResponse{}
	for _, item := range toSlice(data["data"]) {
		m := toMap(item)
		resp.Tags = append(resp.Tags, &pb.EndpointTag{
			Id:    toStr(m["id"]),
			Key:   toStr(m["key"]),
			Value: toStr(m["value"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeConsoleService) CreateEndpointTag(_ context.Context, req *pb.CreateEndpointTagRequest) (*pb.EndpointTag, error) {
	body := map[string]any{"key": req.GetKey(), "value": req.GetValue()}
	data, err := s.restPOST(fmt.Sprintf("/v0/endpoints/%s/tags", req.GetEndpointId()), body)
	if err != nil {
		return nil, err
	}
	return &pb.EndpointTag{
		Id:    toStr(data["id"]),
		Key:   toStr(data["key"]),
		Value: toStr(data["value"]),
	}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// Streams Service
// ═════════════════════════════════════════════════════════════════════════════

func parseStream(m map[string]any) *pb.Stream {
	if m == nil {
		return &pb.Stream{}
	}
	return &pb.Stream{
		Id:                    toStr(m["id"]),
		Name:                  toStr(m["name"]),
		Network:               toStr(m["network"]),
		Dataset:               toStr(m["dataset"]),
		FilterFunction:        toStr(m["filter_function"]),
		Region:                toStr(m["region"]),
		Status:                toStr(m["status"]),
		Destination:           toStr(m["destination"]),
		DestinationType:       toStr(m["destination_type"]),
		DatasetBatchSize:      toInt32(m["dataset_batch_size"]),
		ElasticBatchEnabled:   toBool(m["elastic_batch_enabled"]),
		IncludeStreamMetadata: toBool(m["include_stream_metadata"]),
		CreatedAt:             toStr(m["created_at"]),
		UpdatedAt:             toStr(m["updated_at"]),
	}
}

func (s *QuickNodeStreamsService) CreateStream(_ context.Context, req *pb.CreateStreamRequest) (*pb.Stream, error) {
	body := map[string]any{
		"name":    req.GetName(),
		"network": req.GetNetwork(),
		"dataset": req.GetDataset(),
	}
	if req.GetFilterFunction() != "" {
		body["filter_function"] = req.GetFilterFunction()
	}
	if req.GetRegion() != "" {
		body["region"] = req.GetRegion()
	}
	if req.GetDestination() != "" {
		body["destination"] = req.GetDestination()
	}
	if req.GetDatasetBatchSize() > 0 {
		body["dataset_batch_size"] = req.GetDatasetBatchSize()
	}
	if req.GetElasticBatchEnabled() {
		body["elastic_batch_enabled"] = true
	}
	if req.GetIncludeStreamMetadata() {
		body["include_stream_metadata"] = true
	}
	if req.GetStatus() != "" {
		body["status"] = req.GetStatus()
	}
	data, err := s.restPOST("/streams/rest/v1/streams", body)
	if err != nil {
		return nil, err
	}
	return parseStream(data), nil
}

func (s *QuickNodeStreamsService) ListStreams(_ context.Context, req *pb.ListStreamsRequest) (*pb.ListStreamsResponse, error) {
	params := url.Values{}
	if req.GetLimit() > 0 {
		params.Set("limit", strconv.Itoa(int(req.GetLimit())))
	}
	if req.GetOffset() > 0 {
		params.Set("offset", strconv.Itoa(int(req.GetOffset())))
	}
	data, err := s.restGET("/streams/rest/v1/streams", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListStreamsResponse{
		Total: toInt32(data["total"]),
	}
	for _, item := range toSlice(data["data"]) {
		resp.Streams = append(resp.Streams, parseStream(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeStreamsService) GetStream(_ context.Context, req *pb.GetStreamRequest) (*pb.Stream, error) {
	data, err := s.restGET(fmt.Sprintf("/streams/rest/v1/streams/%s", req.GetStreamId()), nil)
	if err != nil {
		return nil, err
	}
	return parseStream(data), nil
}

func (s *QuickNodeStreamsService) UpdateStream(_ context.Context, req *pb.UpdateStreamRequest) (*pb.Stream, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	if req.GetFilterFunction() != "" {
		body["filter_function"] = req.GetFilterFunction()
	}
	if req.GetDestination() != "" {
		body["destination"] = req.GetDestination()
	}
	if req.GetStatus() != "" {
		body["status"] = req.GetStatus()
	}
	data, err := s.restPATCH(fmt.Sprintf("/streams/rest/v1/streams/%s", req.GetStreamId()), body)
	if err != nil {
		return nil, err
	}
	return parseStream(data), nil
}

func (s *QuickNodeStreamsService) DeleteStream(_ context.Context, req *pb.DeleteStreamRequest) (*pb.DeleteStreamResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/streams/rest/v1/streams/%s", req.GetStreamId()))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteStreamResponse{}, nil
}

func (s *QuickNodeStreamsService) DeleteAllStreams(_ context.Context, _ *pb.DeleteAllStreamsRequest) (*pb.DeleteAllStreamsResponse, error) {
	_, err := s.restDELETE("/streams/rest/v1/streams")
	if err != nil {
		return nil, err
	}
	return &pb.DeleteAllStreamsResponse{}, nil
}

func (s *QuickNodeStreamsService) PauseStream(_ context.Context, req *pb.PauseStreamRequest) (*pb.Stream, error) {
	data, err := s.restPOST(fmt.Sprintf("/streams/rest/v1/streams/%s/pause", req.GetStreamId()), nil)
	if err != nil {
		return nil, err
	}
	return parseStream(data), nil
}

func (s *QuickNodeStreamsService) ActivateStream(_ context.Context, req *pb.ActivateStreamRequest) (*pb.Stream, error) {
	data, err := s.restPOST(fmt.Sprintf("/streams/rest/v1/streams/%s/activate", req.GetStreamId()), nil)
	if err != nil {
		return nil, err
	}
	return parseStream(data), nil
}

func (s *QuickNodeStreamsService) GetEnabledStreamCount(_ context.Context, _ *pb.GetEnabledStreamCountRequest) (*pb.GetEnabledStreamCountResponse, error) {
	data, err := s.restGET("/streams/rest/v1/streams/enabled_count", nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetEnabledStreamCountResponse{
		Count: toInt32(data["count"]),
	}, nil
}

func (s *QuickNodeStreamsService) TestStreamFilter(_ context.Context, req *pb.TestStreamFilterRequest) (*pb.TestStreamFilterResponse, error) {
	body := map[string]any{
		"network":         req.GetNetwork(),
		"dataset":         req.GetDataset(),
		"filter_function": req.GetFilterFunction(),
	}
	data, err := s.restPOST("/streams/rest/v1/streams/test_filter", body)
	if err != nil {
		return nil, err
	}
	output := ""
	if v, ok := data["output"]; ok {
		b, _ := json.Marshal(v)
		output = string(b)
	}
	return &pb.TestStreamFilterResponse{
		Valid:  toBool(data["valid"]),
		Error:  toStr(data["error"]),
		Output: output,
	}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// Webhooks Service
// ═════════════════════════════════════════════════════════════════════════════

func parseWebhook(m map[string]any) *pb.Webhook {
	if m == nil {
		return &pb.Webhook{}
	}
	return &pb.Webhook{
		Id:         toStr(m["id"]),
		Name:       toStr(m["name"]),
		Url:        toStr(m["url"]),
		Network:    toStr(m["network"]),
		Expression: toStr(m["expression"]),
		Status:     toStr(m["status"]),
		TemplateId: toStr(m["template_id"]),
		CreatedAt:  toStr(m["created_at"]),
	}
}

func (s *QuickNodeWebhooksService) CreateWebhook(_ context.Context, req *pb.CreateWebhookRequest) (*pb.Webhook, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	if req.GetUrl() != "" {
		body["url"] = req.GetUrl()
	}
	if req.GetNetwork() != "" {
		body["network"] = req.GetNetwork()
	}
	if req.GetExpression() != "" {
		body["expression"] = req.GetExpression()
	}
	data, err := s.restPOST(fmt.Sprintf("/webhooks/template/%s", req.GetTemplateId()), body)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) ListWebhooks(_ context.Context, _ *pb.ListWebhooksRequest) (*pb.ListWebhooksResponse, error) {
	data, err := s.restGET("/webhooks", nil)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListWebhooksResponse{}
	for _, item := range toSlice(data["data"]) {
		resp.Webhooks = append(resp.Webhooks, parseWebhook(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeWebhooksService) GetWebhook(_ context.Context, req *pb.GetWebhookRequest) (*pb.Webhook, error) {
	data, err := s.restGET(fmt.Sprintf("/webhooks/%s", req.GetWebhookId()), nil)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) UpdateWebhook(_ context.Context, req *pb.UpdateWebhookRequest) (*pb.Webhook, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	if req.GetUrl() != "" {
		body["url"] = req.GetUrl()
	}
	if req.GetExpression() != "" {
		body["expression"] = req.GetExpression()
	}
	data, err := s.restPATCH(fmt.Sprintf("/webhooks/%s", req.GetWebhookId()), body)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) UpdateTemplateWebhook(_ context.Context, req *pb.UpdateTemplateWebhookRequest) (*pb.Webhook, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	if req.GetUrl() != "" {
		body["url"] = req.GetUrl()
	}
	if req.GetExpression() != "" {
		body["expression"] = req.GetExpression()
	}
	data, err := s.restPATCH(fmt.Sprintf("/webhooks/template/%s", req.GetWebhookId()), body)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) DeleteWebhook(_ context.Context, req *pb.DeleteWebhookRequest) (*pb.DeleteWebhookResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/webhooks/%s", req.GetWebhookId()))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteWebhookResponse{}, nil
}

func (s *QuickNodeWebhooksService) DeleteAllWebhooks(_ context.Context, _ *pb.DeleteAllWebhooksRequest) (*pb.DeleteAllWebhooksResponse, error) {
	_, err := s.restDELETE("/webhooks")
	if err != nil {
		return nil, err
	}
	return &pb.DeleteAllWebhooksResponse{}, nil
}

func (s *QuickNodeWebhooksService) ActivateWebhook(_ context.Context, req *pb.ActivateWebhookRequest) (*pb.Webhook, error) {
	data, err := s.restPOST(fmt.Sprintf("/webhooks/%s/activate", req.GetWebhookId()), nil)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) PauseWebhook(_ context.Context, req *pb.PauseWebhookRequest) (*pb.Webhook, error) {
	data, err := s.restPOST(fmt.Sprintf("/webhooks/%s/pause", req.GetWebhookId()), nil)
	if err != nil {
		return nil, err
	}
	return parseWebhook(data), nil
}

func (s *QuickNodeWebhooksService) GetEnabledWebhookCount(_ context.Context, _ *pb.GetEnabledWebhookCountRequest) (*pb.GetEnabledWebhookCountResponse, error) {
	data, err := s.restGET("/webhooks/enabled-count", nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetEnabledWebhookCountResponse{
		Count: toInt32(data["count"]),
	}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// Key-Value Store Service
// ═════════════════════════════════════════════════════════════════════════════

func (s *QuickNodeKeyValueService) CreateList(_ context.Context, req *pb.CreateKVListRequest) (*pb.KVList, error) {
	body := map[string]any{"key": req.GetKey()}
	if len(req.GetItems()) > 0 {
		body["items"] = req.GetItems()
	}
	data, err := s.restPOST("/kv/rest/v1/lists", body)
	if err != nil {
		return nil, err
	}
	return &pb.KVList{Key: toStr(data["key"]), Items: toStringSlice(data["items"])}, nil
}

func (s *QuickNodeKeyValueService) ListLists(_ context.Context, _ *pb.ListKVListsRequest) (*pb.ListKVListsResponse, error) {
	data, err := s.restGET("/kv/rest/v1/lists", nil)
	if err != nil {
		return nil, err
	}
	return &pb.ListKVListsResponse{Keys: toStringSlice(data["data"])}, nil
}

func (s *QuickNodeKeyValueService) GetList(_ context.Context, req *pb.GetKVListRequest) (*pb.KVList, error) {
	data, err := s.restGET(fmt.Sprintf("/kv/rest/v1/lists/%s", url.PathEscape(req.GetKey())), nil)
	if err != nil {
		return nil, err
	}
	return &pb.KVList{Key: toStr(data["key"]), Items: toStringSlice(data["items"])}, nil
}

func (s *QuickNodeKeyValueService) UpdateList(_ context.Context, req *pb.UpdateKVListRequest) (*pb.KVList, error) {
	body := map[string]any{}
	if len(req.GetAdd()) > 0 {
		body["add"] = req.GetAdd()
	}
	if len(req.GetRemove()) > 0 {
		body["remove"] = req.GetRemove()
	}
	data, err := s.restPATCH(fmt.Sprintf("/kv/rest/v1/lists/%s", url.PathEscape(req.GetKey())), body)
	if err != nil {
		return nil, err
	}
	return &pb.KVList{Key: toStr(data["key"]), Items: toStringSlice(data["items"])}, nil
}

func (s *QuickNodeKeyValueService) AddListItem(_ context.Context, req *pb.AddKVListItemRequest) (*pb.KVList, error) {
	body := map[string]any{"item": req.GetItem()}
	data, err := s.restPOST(fmt.Sprintf("/kv/rest/v1/lists/%s/items", url.PathEscape(req.GetKey())), body)
	if err != nil {
		return nil, err
	}
	return &pb.KVList{Key: toStr(data["key"]), Items: toStringSlice(data["items"])}, nil
}

func (s *QuickNodeKeyValueService) CheckListContains(_ context.Context, req *pb.CheckKVListContainsRequest) (*pb.CheckKVListContainsResponse, error) {
	path := fmt.Sprintf("/kv/rest/v1/lists/%s/contains/%s", url.PathEscape(req.GetKey()), url.PathEscape(req.GetItem()))
	data, err := s.restGET(path, nil)
	if err != nil {
		return nil, err
	}
	return &pb.CheckKVListContainsResponse{Contains: toBool(data["contains"])}, nil
}

func (s *QuickNodeKeyValueService) DeleteListItem(_ context.Context, req *pb.DeleteKVListItemRequest) (*pb.DeleteKVListItemResponse, error) {
	path := fmt.Sprintf("/kv/rest/v1/lists/%s/items/%s", url.PathEscape(req.GetKey()), url.PathEscape(req.GetItem()))
	_, err := s.restDELETE(path)
	if err != nil {
		return nil, err
	}
	return &pb.DeleteKVListItemResponse{}, nil
}

func (s *QuickNodeKeyValueService) DeleteList(_ context.Context, req *pb.DeleteKVListRequest) (*pb.DeleteKVListResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/kv/rest/v1/lists/%s", url.PathEscape(req.GetKey())))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteKVListResponse{}, nil
}

func (s *QuickNodeKeyValueService) CreateSet(_ context.Context, req *pb.CreateKVSetRequest) (*pb.KVSet, error) {
	body := map[string]any{"key": req.GetKey(), "value": req.GetValue()}
	data, err := s.restPOST("/kv/rest/v1/sets", body)
	if err != nil {
		return nil, err
	}
	return &pb.KVSet{Key: toStr(data["key"]), Value: toStr(data["value"])}, nil
}

func (s *QuickNodeKeyValueService) ListSets(_ context.Context, _ *pb.ListKVSetsRequest) (*pb.ListKVSetsResponse, error) {
	data, err := s.restGET("/kv/rest/v1/sets", nil)
	if err != nil {
		return nil, err
	}
	return &pb.ListKVSetsResponse{Keys: toStringSlice(data["data"])}, nil
}

func (s *QuickNodeKeyValueService) GetSet(_ context.Context, req *pb.GetKVSetRequest) (*pb.KVSet, error) {
	data, err := s.restGET(fmt.Sprintf("/kv/rest/v1/sets/%s", url.PathEscape(req.GetKey())), nil)
	if err != nil {
		return nil, err
	}
	return &pb.KVSet{Key: toStr(data["key"]), Value: toStr(data["value"])}, nil
}

func (s *QuickNodeKeyValueService) BulkCreateSets(_ context.Context, req *pb.BulkCreateKVSetsRequest) (*pb.BulkCreateKVSetsResponse, error) {
	var sets []map[string]any
	for _, s := range req.GetSets() {
		sets = append(sets, map[string]any{"key": s.GetKey(), "value": s.GetValue()})
	}
	body := map[string]any{}
	if len(sets) > 0 {
		body["create"] = sets
	}
	if len(req.GetDeleteKeys()) > 0 {
		body["delete"] = req.GetDeleteKeys()
	}
	data, err := s.restPOST("/kv/rest/v1/sets/bulk", body)
	if err != nil {
		return nil, err
	}
	return &pb.BulkCreateKVSetsResponse{
		Created: toInt32(data["created"]),
		Deleted: toInt32(data["deleted"]),
	}, nil
}

func (s *QuickNodeKeyValueService) DeleteSet(_ context.Context, req *pb.DeleteKVSetRequest) (*pb.DeleteKVSetResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/kv/rest/v1/sets/%s", url.PathEscape(req.GetKey())))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteKVSetResponse{}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// IPFS Service
// ═════════════════════════════════════════════════════════════════════════════

func (s *QuickNodeIPFSService) UploadObject(_ context.Context, req *pb.UploadIPFSObjectRequest) (*pb.IPFSObject, error) {
	decoded, err := base64.StdEncoding.DecodeString(req.GetBodyBase64())
	if err != nil {
		return nil, fmt.Errorf("decode base64 body: %w", err)
	}
	body := map[string]any{
		"Body":        base64.StdEncoding.EncodeToString(decoded),
		"Key":         req.GetKey(),
		"ContentType": req.GetContentType(),
	}
	data, err := s.restPOST("/ipfs/rest/v1/s3/put-object", body)
	if err != nil {
		return nil, err
	}
	return &pb.IPFSObject{
		RequestId:   toStr(data["requestid"]),
		Cid:         toStr(data["pin"]),
		FileName:    toStr(data["Key"]),
		ContentType: toStr(data["ContentType"]),
		Size:        toInt64(data["size"]),
	}, nil
}

func (s *QuickNodeIPFSService) PinObject(_ context.Context, req *pb.PinIPFSObjectRequest) (*pb.IPFSPinnedObject, error) {
	body := map[string]any{"cid": req.GetCid()}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	data, err := s.restPOST("/ipfs/rest/v1/pinning", body)
	if err != nil {
		return nil, err
	}
	return parsePinnedObject(data), nil
}

func parsePinnedObject(m map[string]any) *pb.IPFSPinnedObject {
	if m == nil {
		return &pb.IPFSPinnedObject{}
	}
	return &pb.IPFSPinnedObject{
		RequestId: toStr(m["requestid"]),
		Cid:       toStr(m["cid"]),
		Status:    toStr(m["status"]),
		Name:      toStr(m["name"]),
		CreatedAt: toStr(m["created"]),
	}
}

func (s *QuickNodeIPFSService) ListPinnedObjects(_ context.Context, req *pb.ListIPFSPinnedObjectsRequest) (*pb.ListIPFSPinnedObjectsResponse, error) {
	params := url.Values{}
	if req.GetPageNumber() > 0 {
		params.Set("pageNumber", strconv.Itoa(int(req.GetPageNumber())))
	}
	if req.GetPerPage() > 0 {
		params.Set("perPage", strconv.Itoa(int(req.GetPerPage())))
	}
	data, err := s.restGET("/ipfs/rest/v1/pinning", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.ListIPFSPinnedObjectsResponse{
		Total: toInt32(data["total"]),
	}
	for _, item := range toSlice(data["data"]) {
		resp.Objects = append(resp.Objects, parsePinnedObject(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeIPFSService) GetPinnedObject(_ context.Context, req *pb.GetIPFSPinnedObjectRequest) (*pb.IPFSPinnedObject, error) {
	data, err := s.restGET(fmt.Sprintf("/ipfs/rest/v1/pinning/%s", req.GetRequestId()), nil)
	if err != nil {
		return nil, err
	}
	return parsePinnedObject(data), nil
}

func (s *QuickNodeIPFSService) GetObject(_ context.Context, req *pb.GetIPFSObjectRequest) (*pb.IPFSObject, error) {
	params := url.Values{}
	params.Set("requestid", req.GetRequestId())
	data, err := s.restGET("/ipfs/rest/v1/s3/get-object", params)
	if err != nil {
		return nil, err
	}
	return &pb.IPFSObject{
		RequestId:   toStr(data["requestid"]),
		Cid:         toStr(data["cid"]),
		FileName:    toStr(data["Key"]),
		ContentType: toStr(data["ContentType"]),
		Size:        toInt64(data["size"]),
	}, nil
}

func (s *QuickNodeIPFSService) UpdatePinnedObject(_ context.Context, req *pb.UpdateIPFSPinnedObjectRequest) (*pb.IPFSPinnedObject, error) {
	body := map[string]any{}
	if req.GetName() != "" {
		body["name"] = req.GetName()
	}
	data, err := s.restPATCH(fmt.Sprintf("/ipfs/rest/v1/pinning/%s", req.GetRequestId()), body)
	if err != nil {
		return nil, err
	}
	return parsePinnedObject(data), nil
}

func (s *QuickNodeIPFSService) DeletePinnedObject(_ context.Context, req *pb.DeleteIPFSPinnedObjectRequest) (*pb.DeleteIPFSPinnedObjectResponse, error) {
	_, err := s.restDELETE(fmt.Sprintf("/ipfs/rest/v1/pinning/%s", req.GetRequestId()))
	if err != nil {
		return nil, err
	}
	return &pb.DeleteIPFSPinnedObjectResponse{}, nil
}

func (s *QuickNodeIPFSService) GetIPFSUsage(_ context.Context, _ *pb.GetIPFSUsageRequest) (*pb.GetIPFSUsageResponse, error) {
	data, err := s.restGET("/ipfs/rest/v1/account/usage", nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetIPFSUsageResponse{
		BandwidthBytes: toInt64(data["bandwidth_bytes"]),
		StorageBytes:   toInt64(data["storage_bytes"]),
		PinnedCount:    toInt32(data["pinned_count"]),
	}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// Token & NFT RPC Service (JSON-RPC against endpoint URL)
// ═════════════════════════════════════════════════════════════════════════════

func parseNFTAsset(m map[string]any) *pb.NFTAsset {
	if m == nil {
		return &pb.NFTAsset{}
	}
	return &pb.NFTAsset{
		CollectionAddress: toStr(m["collectionAddress"]),
		TokenId:           toStr(m["tokenId"]),
		Name:              toStr(m["name"]),
		CollectionName:    toStr(m["collectionName"]),
		ImageUrl:          toStr(m["imageUrl"]),
		TokenType:         toStr(m["tokenType"]),
		Chain:             toStr(m["chain"]),
		Network:           toStr(m["network"]),
		Description:       toStr(m["description"]),
	}
}

func (s *QuickNodeTokenNFTService) FetchNFTs(_ context.Context, req *pb.FetchNFTsRequest) (*pb.FetchNFTsResponse, error) {
	params := map[string]any{
		"wallet": req.GetWallet(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	if len(req.GetContracts()) > 0 {
		params["contracts"] = req.GetContracts()
	}
	data, err := s.jsonRPC("qn_fetchNFTs", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.FetchNFTsResponse{
		Owner:      toStr(data["owner"]),
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["assets"]) {
		resp.Assets = append(resp.Assets, parseNFTAsset(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) FetchNFTsByCollection(_ context.Context, req *pb.FetchNFTsByCollectionRequest) (*pb.FetchNFTsByCollectionResponse, error) {
	params := map[string]any{
		"collection": req.GetCollection(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	data, err := s.jsonRPC("qn_fetchNFTsByCollection", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.FetchNFTsByCollectionResponse{
		Collection: toStr(data["collection"]),
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["assets"]) {
		resp.Assets = append(resp.Assets, parseNFTAsset(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) FetchNFTCollectionDetails(_ context.Context, req *pb.FetchNFTCollectionDetailsRequest) (*pb.FetchNFTCollectionDetailsResponse, error) {
	params := map[string]any{
		"collection": req.GetCollection(),
	}
	data, err := s.jsonRPC("qn_fetchNFTCollectionDetails", params)
	if err != nil {
		return nil, err
	}
	return &pb.FetchNFTCollectionDetailsResponse{
		Name:        toStr(data["name"]),
		Description: toStr(data["description"]),
		ImageUrl:    toStr(data["imageUrl"]),
		BannerUrl:   toStr(data["bannerUrl"]),
		ExternalUrl: toStr(data["externalUrl"]),
		FloorPrice:  toStr(data["floorPrice"]),
		TotalSupply: toInt64(data["totalSupply"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) GetTransfersByNFT(_ context.Context, req *pb.GetTransfersByNFTRequest) (*pb.GetTransfersByNFTResponse, error) {
	params := map[string]any{
		"collection": req.GetCollection(),
		"tokenId":    req.GetTokenId(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	data, err := s.jsonRPC("qn_getTransfersByNFT", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetTransfersByNFTResponse{
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["transfers"]) {
		m := toMap(item)
		resp.Transfers = append(resp.Transfers, &pb.NFTTransfer{
			From:        toStr(m["from"]),
			To:          toStr(m["to"]),
			BlockNumber: toStr(m["blockNumber"]),
			TxHash:      toStr(m["txHash"]),
			Date:        toStr(m["date"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) VerifyNFTsOwner(_ context.Context, req *pb.VerifyNFTsOwnerRequest) (*pb.VerifyNFTsOwnerResponse, error) {
	params := map[string]any{
		"wallet":    req.GetWallet(),
		"contracts": req.GetContracts(),
	}
	data, err := s.jsonRPC("qn_verifyNFTsOwner", params)
	if err != nil {
		return nil, err
	}
	return &pb.VerifyNFTsOwnerResponse{
		OwnedContracts:   toStringSlice(data["owned"]),
		UnownedContracts: toStringSlice(data["unowned"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) GetWalletTokenBalance(_ context.Context, req *pb.GetWalletTokenBalanceRequest) (*pb.GetWalletTokenBalanceResponse, error) {
	params := map[string]any{
		"wallet": req.GetWallet(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	data, err := s.jsonRPC("qn_getWalletTokenBalance", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetWalletTokenBalanceResponse{
		Owner:      toStr(data["owner"]),
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["result"]) {
		m := toMap(item)
		resp.Tokens = append(resp.Tokens, &pb.TokenBalance{
			ContractAddress: toStr(m["contractAddress"]),
			Name:            toStr(m["name"]),
			Symbol:          toStr(m["symbol"]),
			Decimals:        toInt32(m["decimals"]),
			Balance:         toStr(m["totalBalance"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetWalletTokenTransactions(_ context.Context, req *pb.GetWalletTokenTransactionsRequest) (*pb.GetWalletTokenTransactionsResponse, error) {
	params := map[string]any{
		"wallet": req.GetWallet(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	data, err := s.jsonRPC("qn_getWalletTokenTransactions", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetWalletTokenTransactionsResponse{
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["transactions"]) {
		m := toMap(item)
		resp.Transactions = append(resp.Transactions, &pb.TokenTransaction{
			TxHash:          toStr(m["txHash"]),
			BlockNumber:     toStr(m["blockNumber"]),
			From:            toStr(m["from"]),
			To:              toStr(m["to"]),
			ContractAddress: toStr(m["contractAddress"]),
			Amount:          toStr(m["amount"]),
			Timestamp:       toStr(m["timestamp"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetTokenMetadataByContractAddress(_ context.Context, req *pb.GetTokenMetadataByContractAddressRequest) (*pb.TokenMetadata, error) {
	params := map[string]any{
		"contract": req.GetContractAddress(),
	}
	data, err := s.jsonRPC("qn_getTokenMetadataByContractAddress", params)
	if err != nil {
		return nil, err
	}
	return &pb.TokenMetadata{
		ContractAddress: toStr(data["contractAddress"]),
		Name:            toStr(data["name"]),
		Symbol:          toStr(data["symbol"]),
		Decimals:        toInt32(data["decimals"]),
		TotalSupply:     toStr(data["totalSupply"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) GetTokenMetadataBySymbol(_ context.Context, req *pb.GetTokenMetadataBySymbolRequest) (*pb.GetTokenMetadataBySymbolResponse, error) {
	params := map[string]any{
		"symbol": req.GetSymbol(),
	}
	data, err := s.jsonRPC("qn_getTokenMetadataBySymbol", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetTokenMetadataBySymbolResponse{}
	for _, item := range toSlice(data["result"]) {
		m := toMap(item)
		resp.Tokens = append(resp.Tokens, &pb.TokenMetadata{
			ContractAddress: toStr(m["contractAddress"]),
			Name:            toStr(m["name"]),
			Symbol:          toStr(m["symbol"]),
			Decimals:        toInt32(m["decimals"]),
			TotalSupply:     toStr(m["totalSupply"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetTransactionsByAddress(_ context.Context, req *pb.GetTransactionsByAddressRequest) (*pb.GetTransactionsByAddressResponse, error) {
	params := map[string]any{
		"address": req.GetAddress(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetPerPage() > 0 {
		params["perPage"] = req.GetPerPage()
	}
	data, err := s.jsonRPC("qn_getTransactionsByAddress", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetTransactionsByAddressResponse{
		TotalItems: toInt32(data["totalItems"]),
		TotalPages: toInt32(data["totalPages"]),
		PageNumber: toInt32(data["pageNumber"]),
	}
	for _, item := range toSlice(data["transactions"]) {
		m := toMap(item)
		resp.Transactions = append(resp.Transactions, &pb.Transaction{
			TxHash:      toStr(m["txHash"]),
			BlockNumber: toStr(m["blockNumber"]),
			From:        toStr(m["from"]),
			To:          toStr(m["to"]),
			Value:       toStr(m["value"]),
			GasUsed:     toStr(m["gasUsed"]),
			GasPrice:    toStr(m["gasPrice"]),
			Timestamp:   toStr(m["timestamp"]),
			Status:      toStr(m["status"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetContractABI(_ context.Context, req *pb.GetContractABIRequest) (*pb.GetContractABIResponse, error) {
	params := map[string]any{
		"contract": req.GetContractAddress(),
	}
	data, err := s.jsonRPC("qn_getContractABI", params)
	if err != nil {
		return nil, err
	}
	abi := toStr(data["abi"])
	if abi == "" {
		if raw := data["result"]; raw != nil {
			b, _ := json.Marshal(raw)
			abi = string(b)
		}
	}
	return &pb.GetContractABIResponse{Abi: abi}, nil
}

func (s *QuickNodeTokenNFTService) GetReceipts(_ context.Context, req *pb.GetReceiptsRequest) (*pb.GetReceiptsResponse, error) {
	data, err := s.jsonRPC("qn_getReceipts", []any{req.GetBlockNumber()})
	if err != nil {
		return nil, err
	}
	resp := &pb.GetReceiptsResponse{}
	for _, item := range toSlice(data["result"]) {
		m := toMap(item)
		resp.Receipts = append(resp.Receipts, &pb.TransactionReceipt{
			TransactionHash: toStr(m["transactionHash"]),
			BlockNumber:     toStr(m["blockNumber"]),
			From:            toStr(m["from"]),
			To:              toStr(m["to"]),
			GasUsed:         toStr(m["gasUsed"]),
			Status:          toStr(m["status"]),
			ContractAddress: toStr(m["contractAddress"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetBlockWithReceipts(_ context.Context, req *pb.GetBlockWithReceiptsRequest) (*pb.GetBlockWithReceiptsResponse, error) {
	data, err := s.jsonRPC("qn_getBlockWithReceipts", []any{req.GetBlockNumber()})
	if err != nil {
		return nil, err
	}
	block := toMap(data["block"])
	resp := &pb.GetBlockWithReceiptsResponse{
		BlockHash:   toStr(block["hash"]),
		BlockNumber: toStr(block["number"]),
		Timestamp:   toStr(block["timestamp"]),
	}
	for _, item := range toSlice(data["receipts"]) {
		m := toMap(item)
		resp.Receipts = append(resp.Receipts, &pb.TransactionReceipt{
			TransactionHash: toStr(m["transactionHash"]),
			BlockNumber:     toStr(m["blockNumber"]),
			From:            toStr(m["from"]),
			To:              toStr(m["to"]),
			GasUsed:         toStr(m["gasUsed"]),
			Status:          toStr(m["status"]),
			ContractAddress: toStr(m["contractAddress"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) GetBlockFromTimestamp(_ context.Context, req *pb.GetBlockFromTimestampRequest) (*pb.GetBlockFromTimestampResponse, error) {
	data, err := s.jsonRPC("qn_getBlockFromTimestamp", map[string]any{
		"timestamp": req.GetTimestamp(),
	})
	if err != nil {
		return nil, err
	}
	return &pb.GetBlockFromTimestampResponse{
		BlockNumber:    toStr(data["blockNumber"]),
		BlockTimestamp: toStr(data["blockTimestamp"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) GetBlocksInTimestampRange(_ context.Context, req *pb.GetBlocksInTimestampRangeRequest) (*pb.GetBlocksInTimestampRangeResponse, error) {
	data, err := s.jsonRPC("qn_getBlocksInTimestampRange", map[string]any{
		"startTimestamp": req.GetStartTimestamp(),
		"endTimestamp":   req.GetEndTimestamp(),
	})
	if err != nil {
		return nil, err
	}
	resp := &pb.GetBlocksInTimestampRangeResponse{}
	for _, item := range toSlice(data["result"]) {
		m := toMap(item)
		resp.Blocks = append(resp.Blocks, &pb.BlockInfo{
			BlockNumber:    toStr(m["blockNumber"]),
			BlockTimestamp: toStr(m["blockTimestamp"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeTokenNFTService) ResolveENS(_ context.Context, req *pb.ResolveENSRequest) (*pb.ResolveENSResponse, error) {
	data, err := s.jsonRPC("qn_resolveENS", map[string]any{
		"nameOrAddress": req.GetNameOrAddress(),
	})
	if err != nil {
		return nil, err
	}
	return &pb.ResolveENSResponse{
		Address: toStr(data["address"]),
		EnsName: toStr(data["ensName"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) BroadcastRawTransaction(_ context.Context, req *pb.BroadcastRawTransactionRequest) (*pb.BroadcastRawTransactionResponse, error) {
	data, err := s.jsonRPC("qn_broadcastRawTransaction", req.GetRawTransaction())
	if err != nil {
		return nil, err
	}
	return &pb.BroadcastRawTransactionResponse{
		TxHash: toStr(data["result"]),
	}, nil
}

func (s *QuickNodeTokenNFTService) EstimatePriorityFees(_ context.Context, req *pb.EstimatePriorityFeesRequest) (*pb.EstimatePriorityFeesResponse, error) {
	params := map[string]any{}
	if req.GetLastNSlots() > 0 {
		params["last_n_slots"] = req.GetLastNSlots()
	}
	if req.GetAccount() != "" {
		params["account"] = req.GetAccount()
	}
	data, err := s.jsonRPC("qn_estimatePriorityFees", params)
	if err != nil {
		return nil, err
	}
	parseFee := func(key string) *pb.PriorityFeeEstimate {
		m := toMap(data[key])
		if m == nil {
			return nil
		}
		return &pb.PriorityFeeEstimate{PerComputeUnit: toStr(m["per_compute_unit"])}
	}
	return &pb.EstimatePriorityFeesResponse{
		Low:         parseFee("low"),
		Medium:      parseFee("medium"),
		High:        parseFee("high"),
		Extreme:     parseFee("extreme"),
		Recommended: parseFee("recommended"),
	}, nil
}

// ═════════════════════════════════════════════════════════════════════════════
// Solana DAS Service (JSON-RPC against endpoint URL)
// ═════════════════════════════════════════════════════════════════════════════

func parseDASAsset(m map[string]any) *pb.DASAsset {
	if m == nil {
		return &pb.DASAsset{}
	}
	content := toMap(m["content"])
	metadata := toMap(content["metadata"])
	links := toMap(content["links"])
	ownership := toMap(m["ownership"])
	compression := toMap(m["compression"])
	grouping := toSlice(m["grouping"])
	royalty := toMap(m["royalty"])

	asset := &pb.DASAsset{
		Id:                 toStr(m["id"]),
		Interface:          toStr(m["interface"]),
		Owner:              toStr(ownership["owner"]),
		Compressed:         toBool(compression["compressed"]),
		Burnt:              toBool(m["burnt"]),
		Mutable:            toBool(m["mutable"]),
		Name:               toStr(metadata["name"]),
		Symbol:             toStr(metadata["symbol"]),
		Description:        toStr(metadata["description"]),
		MetadataUri:        toStr(content["json_uri"]),
		RoyaltyBasisPoints: toInt32(royalty["basis_points"]),
		Supply:             toStr(m["supply"]),
	}
	if links != nil {
		asset.ImageUri = toStr(links["image"])
	}
	for _, g := range grouping {
		gm := toMap(g)
		if toStr(gm["group_key"]) == "collection" {
			asset.Collection = toStr(gm["group_value"])
		}
	}
	return asset
}

func (s *QuickNodeSolanaDASService) GetAsset(_ context.Context, req *pb.GetDASAssetRequest) (*pb.DASAsset, error) {
	data, err := s.jsonRPC("getAsset", map[string]any{"id": req.GetId()})
	if err != nil {
		return nil, err
	}
	return parseDASAsset(data), nil
}

func (s *QuickNodeSolanaDASService) GetAssets(_ context.Context, req *pb.GetDASAssetsRequest) (*pb.GetDASAssetsResponse, error) {
	data, err := s.jsonRPC("getAssets", map[string]any{"ids": req.GetIds()})
	if err != nil {
		return nil, err
	}
	resp := &pb.GetDASAssetsResponse{}
	for _, item := range toSlice(data["result"]) {
		resp.Assets = append(resp.Assets, parseDASAsset(toMap(item)))
	}
	return resp, nil
}

func (s *QuickNodeSolanaDASService) GetAssetProof(_ context.Context, req *pb.GetDASAssetProofRequest) (*pb.DASAssetProof, error) {
	data, err := s.jsonRPC("getAssetProof", map[string]any{"id": req.GetId()})
	if err != nil {
		return nil, err
	}
	return &pb.DASAssetProof{
		Id:        toStr(data["id"]),
		Root:      toStr(data["root"]),
		Proof:     toStringSlice(data["proof"]),
		TreeId:    toStr(data["tree_id"]),
		NodeIndex: toInt32(data["node_index"]),
	}, nil
}

func (s *QuickNodeSolanaDASService) GetAssetProofs(_ context.Context, req *pb.GetDASAssetProofsRequest) (*pb.GetDASAssetProofsResponse, error) {
	data, err := s.jsonRPC("getAssetProofs", map[string]any{"ids": req.GetIds()})
	if err != nil {
		return nil, err
	}
	resp := &pb.GetDASAssetProofsResponse{}
	for _, item := range toSlice(data["result"]) {
		m := toMap(item)
		resp.Proofs = append(resp.Proofs, &pb.DASAssetProof{
			Id:        toStr(m["id"]),
			Root:      toStr(m["root"]),
			Proof:     toStringSlice(m["proof"]),
			TreeId:    toStr(m["tree_id"]),
			NodeIndex: toInt32(m["node_index"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeSolanaDASService) GetAssetsByAuthority(_ context.Context, req *pb.GetDASAssetsByAuthorityRequest) (*pb.GetDASAssetsListResponse, error) {
	params := map[string]any{
		"authorityAddress": req.GetAuthorityAddress(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getAssetsByAuthority", params)
	if err != nil {
		return nil, err
	}
	return parseDASAssetsList(data), nil
}

func (s *QuickNodeSolanaDASService) GetAssetsByCreator(_ context.Context, req *pb.GetDASAssetsByCreatorRequest) (*pb.GetDASAssetsListResponse, error) {
	params := map[string]any{
		"creatorAddress": req.GetCreatorAddress(),
	}
	if req.GetOnlyVerified() {
		params["onlyVerified"] = true
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getAssetsByCreator", params)
	if err != nil {
		return nil, err
	}
	return parseDASAssetsList(data), nil
}

func (s *QuickNodeSolanaDASService) GetAssetsByGroup(_ context.Context, req *pb.GetDASAssetsByGroupRequest) (*pb.GetDASAssetsListResponse, error) {
	params := map[string]any{
		"groupKey":   req.GetGroupKey(),
		"groupValue": req.GetGroupValue(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getAssetsByGroup", params)
	if err != nil {
		return nil, err
	}
	return parseDASAssetsList(data), nil
}

func (s *QuickNodeSolanaDASService) GetAssetsByOwner(_ context.Context, req *pb.GetDASAssetsByOwnerRequest) (*pb.GetDASAssetsListResponse, error) {
	params := map[string]any{
		"ownerAddress": req.GetOwnerAddress(),
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getAssetsByOwner", params)
	if err != nil {
		return nil, err
	}
	return parseDASAssetsList(data), nil
}

func parseDASAssetsList(data map[string]any) *pb.GetDASAssetsListResponse {
	resp := &pb.GetDASAssetsListResponse{
		Total: toInt32(data["total"]),
		Page:  toInt32(data["page"]),
		Limit: toInt32(data["limit"]),
	}
	for _, item := range toSlice(data["items"]) {
		resp.Items = append(resp.Items, parseDASAsset(toMap(item)))
	}
	return resp
}

func (s *QuickNodeSolanaDASService) GetAssetSignatures(_ context.Context, req *pb.GetDASAssetSignaturesRequest) (*pb.GetDASAssetSignaturesResponse, error) {
	params := map[string]any{"id": req.GetId()}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getAssetSignatures", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetDASAssetSignaturesResponse{
		Total: toInt32(data["total"]),
	}
	for _, item := range toSlice(data["items"]) {
		m := toMap(item)
		resp.Signatures = append(resp.Signatures, &pb.DASSignature{
			Signature: toStr(m["signature"]),
			Slot:      toInt64(m["slot"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeSolanaDASService) GetTokenAccounts(_ context.Context, req *pb.GetDASTokenAccountsRequest) (*pb.GetDASTokenAccountsResponse, error) {
	params := map[string]any{}
	if req.GetMint() != "" {
		params["mint"] = req.GetMint()
	}
	if req.GetOwner() != "" {
		params["owner"] = req.GetOwner()
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getTokenAccounts", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetDASTokenAccountsResponse{
		Total: toInt32(data["total"]),
	}
	for _, item := range toSlice(data["token_accounts"]) {
		m := toMap(item)
		resp.TokenAccounts = append(resp.TokenAccounts, &pb.DASTokenAccount{
			Address:  toStr(m["address"]),
			Mint:     toStr(m["mint"]),
			Owner:    toStr(m["owner"]),
			Amount:   toStr(m["amount"]),
			Decimals: toInt32(m["decimals"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeSolanaDASService) GetNftEditions(_ context.Context, req *pb.GetDASNftEditionsRequest) (*pb.GetDASNftEditionsResponse, error) {
	params := map[string]any{"mint": req.GetMint()}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("getNftEditions", params)
	if err != nil {
		return nil, err
	}
	resp := &pb.GetDASNftEditionsResponse{
		Total: toInt32(data["total"]),
	}
	for _, item := range toSlice(data["editions"]) {
		m := toMap(item)
		resp.Editions = append(resp.Editions, &pb.DASNftEdition{
			Mint:          toStr(m["mint"]),
			EditionNumber: toInt64(m["edition_number"]),
		})
	}
	return resp, nil
}

func (s *QuickNodeSolanaDASService) SearchAssets(_ context.Context, req *pb.SearchDASAssetsRequest) (*pb.GetDASAssetsListResponse, error) {
	params := map[string]any{}
	if req.GetOwnerAddress() != "" {
		params["ownerAddress"] = req.GetOwnerAddress()
	}
	if req.GetCreatorAddress() != "" {
		params["creatorAddress"] = req.GetCreatorAddress()
	}
	if req.GetCollection() != "" {
		params["grouping"] = []any{"collection", req.GetCollection()}
	}
	if req.GetName() != "" {
		params["name"] = req.GetName()
	}
	if req.GetCompressed() {
		params["compressed"] = true
	}
	if req.GetBurnt() {
		params["burnt"] = true
	}
	if req.GetInterface() != "" {
		params["interface"] = req.GetInterface()
	}
	if req.GetPage() > 0 {
		params["page"] = req.GetPage()
	}
	if req.GetLimit() > 0 {
		params["limit"] = req.GetLimit()
	}
	data, err := s.jsonRPC("searchAssets", params)
	if err != nil {
		return nil, err
	}
	return parseDASAssetsList(data), nil
}

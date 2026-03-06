package main

import (
	"context"
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	pb "github.com/jim-technologies/invariantaf/googlesheets/googlesheets/v1"
)

// GoogleSheetsService implements googlesheets.v1.GoogleSheetsService RPCs by
// calling the Google Sheets API v4.
type GoogleSheetsService struct {
	baseURL     string
	client      *http.Client
	apiKey      string
	accessToken string

	mu          sync.Mutex
	tokenExpiry time.Time
	saKey       *serviceAccountKey
}

type serviceAccountKey struct {
	ClientEmail string `json:"client_email"`
	PrivateKey  string `json:"private_key"`
	TokenURI    string `json:"token_uri"`
}

// NewGoogleSheetsService creates a service pointing at the real Google Sheets API.
func NewGoogleSheetsService() *GoogleSheetsService {
	baseURL := os.Getenv("GOOGLE_SHEETS_BASE_URL")
	if baseURL == "" {
		baseURL = "https://sheets.googleapis.com"
	}

	svc := &GoogleSheetsService{
		baseURL: baseURL,
		client:  &http.Client{},
		apiKey:  os.Getenv("GOOGLE_API_KEY"),
	}

	if encoded := os.Getenv("GOOGLE_SERVICE_ACCOUNT_KEY"); encoded != "" {
		decoded, err := base64.StdEncoding.DecodeString(encoded)
		if err == nil {
			var key serviceAccountKey
			if err := json.Unmarshal(decoded, &key); err == nil {
				svc.saKey = &key
			}
		}
	}

	return svc
}

// ensureAccessToken obtains or refreshes an OAuth2 access token using the
// service account JWT grant flow.
func (s *GoogleSheetsService) ensureAccessToken() error {
	if s.saKey == nil {
		return nil
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if s.accessToken != "" && time.Now().Before(s.tokenExpiry) {
		return nil
	}

	now := time.Now()
	header := base64URLEncode([]byte(`{"alg":"RS256","typ":"JWT"}`))

	claimSet := map[string]any{
		"iss":   s.saKey.ClientEmail,
		"scope": "https://www.googleapis.com/auth/spreadsheets",
		"aud":   "https://oauth2.googleapis.com/token",
		"iat":   now.Unix(),
		"exp":   now.Add(time.Hour).Unix(),
	}
	claimBytes, err := json.Marshal(claimSet)
	if err != nil {
		return fmt.Errorf("marshal claims: %w", err)
	}
	claims := base64URLEncode(claimBytes)

	signingInput := header + "." + claims

	block, _ := pem.Decode([]byte(s.saKey.PrivateKey))
	if block == nil {
		return fmt.Errorf("failed to decode PEM block from private key")
	}

	key, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return fmt.Errorf("parse private key: %w", err)
	}
	rsaKey, ok := key.(*rsa.PrivateKey)
	if !ok {
		return fmt.Errorf("private key is not RSA")
	}

	hash := sha256.Sum256([]byte(signingInput))
	sig, err := rsa.SignPKCS1v15(nil, rsaKey, crypto.SHA256, hash[:])
	if err != nil {
		return fmt.Errorf("sign jwt: %w", err)
	}
	jwt := signingInput + "." + base64URLEncode(sig)

	tokenURI := "https://oauth2.googleapis.com/token"
	if s.saKey.TokenURI != "" {
		tokenURI = s.saKey.TokenURI
	}

	form := url.Values{}
	form.Set("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer")
	form.Set("assertion", jwt)

	resp, err := s.client.PostForm(tokenURI, form)
	if err != nil {
		return fmt.Errorf("token request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read token response: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("token endpoint returned %d: %s", resp.StatusCode, string(body))
	}

	var tokenResp struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int    `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return fmt.Errorf("decode token response: %w", err)
	}

	s.accessToken = tokenResp.AccessToken
	s.tokenExpiry = now.Add(time.Duration(tokenResp.ExpiresIn) * time.Second).Add(-60 * time.Second)
	return nil
}

func base64URLEncode(data []byte) string {
	return strings.TrimRight(base64.URLEncoding.EncodeToString(data), "=")
}

// addAuth adds authentication to a request. If an access token is available
// it is sent as a Bearer header; otherwise the API key is appended as a query
// parameter.
func (s *GoogleSheetsService) addAuth(req *http.Request) error {
	if err := s.ensureAccessToken(); err != nil {
		return err
	}
	if s.accessToken != "" {
		req.Header.Set("Authorization", "Bearer "+s.accessToken)
	} else if s.apiKey != "" {
		q := req.URL.Query()
		q.Set("key", s.apiKey)
		req.URL.RawQuery = q.Encode()
	}
	return nil
}

// get fetches a JSON response from the Google Sheets API.
func (s *GoogleSheetsService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest(http.MethodGet, u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	if err := s.addAuth(req); err != nil {
		return nil, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http get %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("google sheets api returned %d: %s", resp.StatusCode, string(body))
	}
	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

// post sends a JSON POST request to the Google Sheets API.
func (s *GoogleSheetsService) post(path string, payload any) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	var bodyReader io.Reader
	if payload != nil {
		data, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		bodyReader = strings.NewReader(string(data))
	}
	req, err := http.NewRequest(http.MethodPost, u, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if err := s.addAuth(req); err != nil {
		return nil, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http post %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("google sheets api returned %d: %s", resp.StatusCode, string(body))
	}
	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

// put sends a JSON PUT request to the Google Sheets API.
func (s *GoogleSheetsService) put(path string, payload any) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	var bodyReader io.Reader
	if payload != nil {
		data, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		bodyReader = strings.NewReader(string(data))
	}
	req, err := http.NewRequest(http.MethodPut, u, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if err := s.addAuth(req); err != nil {
		return nil, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http put %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("google sheets api returned %d: %s", resp.StatusCode, string(body))
	}
	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

func toStr(v any) string {
	if v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
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

// parseRows converts a JSON 2D array ([]any of []any) into []*pb.Row.
func parseRows(v any) []*pb.Row {
	raw := toSlice(v)
	if raw == nil {
		return nil
	}
	var rows []*pb.Row
	for _, rowVal := range raw {
		rowSlice := toSlice(rowVal)
		row := &pb.Row{}
		for _, cell := range rowSlice {
			row.Cells = append(row.Cells, toStr(cell))
		}
		rows = append(rows, row)
	}
	return rows
}

// rowsToAny converts []*pb.Row into a [][]any suitable for JSON marshalling.
func rowsToAny(rows []*pb.Row) [][]any {
	var result [][]any
	for _, row := range rows {
		var cells []any
		for _, cell := range row.GetCells() {
			cells = append(cells, cell)
		}
		result = append(result, cells)
	}
	return result
}

// GetSpreadsheet gets spreadsheet metadata including title, sheets list, and properties.
func (s *GoogleSheetsService) GetSpreadsheet(_ context.Context, req *pb.GetSpreadsheetRequest) (*pb.GetSpreadsheetResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s", req.GetSpreadsheetId())
	params := url.Values{}
	params.Set("fields", "spreadsheetId,properties,sheets.properties,spreadsheetUrl")
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	props := toMap(data["properties"])
	resp := &pb.GetSpreadsheetResponse{
		SpreadsheetId:  toStr(data["spreadsheetId"]),
		Title:          toStr(props["title"]),
		Locale:         toStr(props["locale"]),
		SpreadsheetUrl: toStr(data["spreadsheetUrl"]),
	}

	for _, sheetVal := range toSlice(data["sheets"]) {
		sheetMap := toMap(sheetVal)
		sp := toMap(sheetMap["properties"])
		gridProps := toMap(sp["gridProperties"])
		resp.Sheets = append(resp.Sheets, &pb.SheetProperties{
			SheetId:     toInt32(sp["sheetId"]),
			Title:       toStr(sp["title"]),
			Index:       toInt32(sp["index"]),
			RowCount:    toInt32(gridProps["rowCount"]),
			ColumnCount: toInt32(gridProps["columnCount"]),
		})
	}

	return resp, nil
}

// CreateSpreadsheet creates a new spreadsheet with a given title and optional sheet names.
func (s *GoogleSheetsService) CreateSpreadsheet(_ context.Context, req *pb.CreateSpreadsheetRequest) (*pb.CreateSpreadsheetResponse, error) {
	body := map[string]any{
		"properties": map[string]any{
			"title": req.GetTitle(),
		},
	}

	if len(req.GetSheetNames()) > 0 {
		var sheets []map[string]any
		for _, name := range req.GetSheetNames() {
			sheets = append(sheets, map[string]any{
				"properties": map[string]any{
					"title": name,
				},
			})
		}
		body["sheets"] = sheets
	}

	data, err := s.post("/v4/spreadsheets", body)
	if err != nil {
		return nil, err
	}

	return &pb.CreateSpreadsheetResponse{
		SpreadsheetId:  toStr(data["spreadsheetId"]),
		SpreadsheetUrl: toStr(data["spreadsheetUrl"]),
	}, nil
}

// GetValues reads cell values from a range in A1 notation.
func (s *GoogleSheetsService) GetValues(_ context.Context, req *pb.GetValuesRequest) (*pb.GetValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values/%s",
		req.GetSpreadsheetId(), url.PathEscape(req.GetRange()))
	data, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}

	return &pb.GetValuesResponse{
		Range:  toStr(data["range"]),
		Values: parseRows(data["values"]),
	}, nil
}

// BatchGetValues reads cell values from multiple ranges in a single request.
func (s *GoogleSheetsService) BatchGetValues(_ context.Context, req *pb.BatchGetValuesRequest) (*pb.BatchGetValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values:batchGet", req.GetSpreadsheetId())
	params := url.Values{}
	for _, r := range req.GetRanges() {
		params.Add("ranges", r)
	}
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	resp := &pb.BatchGetValuesResponse{
		SpreadsheetId: toStr(data["spreadsheetId"]),
	}
	for _, vrVal := range toSlice(data["valueRanges"]) {
		vrMap := toMap(vrVal)
		resp.ValueRanges = append(resp.ValueRanges, &pb.ValueRange{
			Range:  toStr(vrMap["range"]),
			Values: parseRows(vrMap["values"]),
		})
	}
	return resp, nil
}

// UpdateValues writes cell values to a range in A1 notation.
func (s *GoogleSheetsService) UpdateValues(_ context.Context, req *pb.UpdateValuesRequest) (*pb.UpdateValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values/%s?valueInputOption=USER_ENTERED",
		req.GetSpreadsheetId(), url.PathEscape(req.GetRange()))

	body := map[string]any{
		"range":  req.GetRange(),
		"values": rowsToAny(req.GetValues()),
	}

	data, err := s.put(path, body)
	if err != nil {
		return nil, err
	}

	return &pb.UpdateValuesResponse{
		UpdatedRange:   toStr(data["updatedRange"]),
		UpdatedRows:    toInt32(data["updatedRows"]),
		UpdatedColumns: toInt32(data["updatedColumns"]),
		UpdatedCells:   toInt32(data["updatedCells"]),
	}, nil
}

// AppendValues appends rows after the last row with data in a sheet or range.
func (s *GoogleSheetsService) AppendValues(_ context.Context, req *pb.AppendValuesRequest) (*pb.AppendValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values/%s:append?valueInputOption=USER_ENTERED",
		req.GetSpreadsheetId(), url.PathEscape(req.GetRange()))

	body := map[string]any{
		"range":  req.GetRange(),
		"values": rowsToAny(req.GetValues()),
	}

	data, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	updates := toMap(data["updates"])
	return &pb.AppendValuesResponse{
		UpdatedRange:   toStr(updates["updatedRange"]),
		UpdatedRows:    toInt32(updates["updatedRows"]),
		UpdatedColumns: toInt32(updates["updatedColumns"]),
		UpdatedCells:   toInt32(updates["updatedCells"]),
	}, nil
}

// BatchUpdateValues writes cell values to multiple ranges in a single request.
func (s *GoogleSheetsService) BatchUpdateValues(_ context.Context, req *pb.BatchUpdateValuesRequest) (*pb.BatchUpdateValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values:batchUpdate", req.GetSpreadsheetId())

	var dataEntries []map[string]any
	for _, rv := range req.GetData() {
		dataEntries = append(dataEntries, map[string]any{
			"range":  rv.GetRange(),
			"values": rowsToAny(rv.GetValues()),
		})
	}

	body := map[string]any{
		"valueInputOption": "USER_ENTERED",
		"data":             dataEntries,
	}

	data, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	return &pb.BatchUpdateValuesResponse{
		SpreadsheetId:       toStr(data["spreadsheetId"]),
		TotalUpdatedRows:    toInt32(data["totalUpdatedRows"]),
		TotalUpdatedColumns: toInt32(data["totalUpdatedColumns"]),
		TotalUpdatedCells:   toInt32(data["totalUpdatedCells"]),
	}, nil
}

// ClearValues clears all values from a range (formatting is preserved).
func (s *GoogleSheetsService) ClearValues(_ context.Context, req *pb.ClearValuesRequest) (*pb.ClearValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values/%s:clear",
		req.GetSpreadsheetId(), url.PathEscape(req.GetRange()))

	data, err := s.post(path, map[string]any{})
	if err != nil {
		return nil, err
	}

	return &pb.ClearValuesResponse{
		ClearedRange: toStr(data["clearedRange"]),
	}, nil
}

// BatchClearValues clears values from multiple ranges in a single request.
func (s *GoogleSheetsService) BatchClearValues(_ context.Context, req *pb.BatchClearValuesRequest) (*pb.BatchClearValuesResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s/values:batchClear", req.GetSpreadsheetId())

	body := map[string]any{
		"ranges": req.GetRanges(),
	}

	data, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	var clearedRanges []string
	for _, r := range toSlice(data["clearedRanges"]) {
		clearedRanges = append(clearedRanges, toStr(r))
	}

	return &pb.BatchClearValuesResponse{
		SpreadsheetId: toStr(data["spreadsheetId"]),
		ClearedRanges: clearedRanges,
	}, nil
}

// AddSheet adds a new sheet (tab) to an existing spreadsheet.
func (s *GoogleSheetsService) AddSheet(_ context.Context, req *pb.AddSheetRequest) (*pb.AddSheetResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s:batchUpdate", req.GetSpreadsheetId())

	sheetProps := map[string]any{
		"title": req.GetTitle(),
	}
	if req.GetRowCount() > 0 || req.GetColumnCount() > 0 {
		gridProps := map[string]any{}
		if req.GetRowCount() > 0 {
			gridProps["rowCount"] = req.GetRowCount()
		}
		if req.GetColumnCount() > 0 {
			gridProps["columnCount"] = req.GetColumnCount()
		}
		sheetProps["gridProperties"] = gridProps
	}

	body := map[string]any{
		"requests": []map[string]any{
			{
				"addSheet": map[string]any{
					"properties": sheetProps,
				},
			},
		},
	}

	data, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	replies := toSlice(data["replies"])
	if len(replies) == 0 {
		return &pb.AddSheetResponse{}, nil
	}
	reply := toMap(replies[0])
	addSheetReply := toMap(reply["addSheet"])
	props := toMap(addSheetReply["properties"])

	return &pb.AddSheetResponse{
		SheetId: toInt32(props["sheetId"]),
		Title:   toStr(props["title"]),
		Index:   toInt32(props["index"]),
	}, nil
}

// DeleteSheet deletes a sheet (tab) from a spreadsheet by its sheet ID.
func (s *GoogleSheetsService) DeleteSheet(_ context.Context, req *pb.DeleteSheetRequest) (*pb.DeleteSheetResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s:batchUpdate", req.GetSpreadsheetId())

	body := map[string]any{
		"requests": []map[string]any{
			{
				"deleteSheet": map[string]any{
					"sheetId": req.GetSheetId(),
				},
			},
		},
	}

	_, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	return &pb.DeleteSheetResponse{}, nil
}

// DuplicateSheet duplicates a sheet within the same spreadsheet.
func (s *GoogleSheetsService) DuplicateSheet(_ context.Context, req *pb.DuplicateSheetRequest) (*pb.DuplicateSheetResponse, error) {
	path := fmt.Sprintf("/v4/spreadsheets/%s:batchUpdate", req.GetSpreadsheetId())

	dupReq := map[string]any{
		"sourceSheetId": req.GetSourceSheetId(),
	}
	if req.GetNewSheetName() != "" {
		dupReq["newSheetName"] = req.GetNewSheetName()
	}

	body := map[string]any{
		"requests": []map[string]any{
			{
				"duplicateSheet": dupReq,
			},
		},
	}

	data, err := s.post(path, body)
	if err != nil {
		return nil, err
	}

	replies := toSlice(data["replies"])
	if len(replies) == 0 {
		return &pb.DuplicateSheetResponse{}, nil
	}
	reply := toMap(replies[0])
	dupReply := toMap(reply["duplicateSheet"])
	props := toMap(dupReply["properties"])

	return &pb.DuplicateSheetResponse{
		SheetId: toInt32(props["sheetId"]),
		Title:   toStr(props["title"]),
		Index:   toInt32(props["index"]),
	}, nil
}

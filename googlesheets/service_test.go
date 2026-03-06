package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	pb "github.com/jim-technologies/invariantaf/googlesheets/googlesheets/v1"
)

func mockSheetsServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		// POST /v4/spreadsheets - CreateSpreadsheet
		case r.URL.Path == "/v4/spreadsheets" && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"spreadsheetId":  "new-spreadsheet-123",
				"spreadsheetUrl": "https://docs.google.com/spreadsheets/d/new-spreadsheet-123/edit",
			})

		// POST /v4/spreadsheets/{id}:batchUpdate - AddSheet, DeleteSheet, DuplicateSheet
		case strings.HasSuffix(r.URL.Path, ":batchUpdate") && r.Method == http.MethodPost && !strings.Contains(r.URL.Path, "/values"):
			var body map[string]any
			json.NewDecoder(r.Body).Decode(&body)
			requests := body["requests"].([]any)
			req := requests[0].(map[string]any)

			if _, ok := req["addSheet"]; ok {
				json.NewEncoder(w).Encode(map[string]any{
					"replies": []any{
						map[string]any{
							"addSheet": map[string]any{
								"properties": map[string]any{
									"sheetId": float64(42),
									"title":   "NewSheet",
									"index":   float64(1),
								},
							},
						},
					},
				})
			} else if _, ok := req["deleteSheet"]; ok {
				json.NewEncoder(w).Encode(map[string]any{
					"replies": []any{
						map[string]any{},
					},
				})
			} else if _, ok := req["duplicateSheet"]; ok {
				json.NewEncoder(w).Encode(map[string]any{
					"replies": []any{
						map[string]any{
							"duplicateSheet": map[string]any{
								"properties": map[string]any{
									"sheetId": float64(99),
									"title":   "Copy of Sheet1",
									"index":   float64(2),
								},
							},
						},
					},
				})
			}

		// POST /v4/spreadsheets/{id}/values:batchUpdate - BatchUpdateValues
		case strings.HasSuffix(r.URL.Path, "/values:batchUpdate") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"spreadsheetId":     "spreadsheet-123",
				"totalUpdatedRows":  float64(5),
				"totalUpdatedColumns": float64(3),
				"totalUpdatedCells":  float64(15),
			})

		// POST /v4/spreadsheets/{id}/values:batchClear - BatchClearValues
		case strings.HasSuffix(r.URL.Path, "/values:batchClear") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"spreadsheetId": "spreadsheet-123",
				"clearedRanges": []any{"Sheet1!A1:B2", "Sheet2!C3:D4"},
			})

		// POST /v4/spreadsheets/{id}/values/{range}:append - AppendValues
		case strings.Contains(r.URL.Path, "/values/") && strings.HasSuffix(r.URL.Path, ":append") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"updates": map[string]any{
					"updatedRange":   "Sheet1!A4:C5",
					"updatedRows":    float64(2),
					"updatedColumns": float64(3),
					"updatedCells":   float64(6),
				},
			})

		// POST /v4/spreadsheets/{id}/values/{range}:clear - ClearValues
		case strings.Contains(r.URL.Path, "/values/") && strings.HasSuffix(r.URL.Path, ":clear") && r.Method == http.MethodPost:
			json.NewEncoder(w).Encode(map[string]any{
				"clearedRange": "Sheet1!A1:C3",
			})

		// PUT /v4/spreadsheets/{id}/values/{range} - UpdateValues
		case strings.Contains(r.URL.Path, "/values/") && r.Method == http.MethodPut:
			json.NewEncoder(w).Encode(map[string]any{
				"updatedRange":   "Sheet1!A1:C3",
				"updatedRows":    float64(3),
				"updatedColumns": float64(3),
				"updatedCells":   float64(9),
			})

		// GET /v4/spreadsheets/{id}/values:batchGet - BatchGetValues
		case strings.HasSuffix(r.URL.Path, "/values:batchGet") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"spreadsheetId": "spreadsheet-123",
				"valueRanges": []any{
					map[string]any{
						"range": "Sheet1!A1:B2",
						"values": []any{
							[]any{"A1", "B1"},
							[]any{"A2", "B2"},
						},
					},
					map[string]any{
						"range": "Sheet2!C3:D4",
						"values": []any{
							[]any{"C3", "D3"},
							[]any{"C4", "D4"},
						},
					},
				},
			})

		// GET /v4/spreadsheets/{id}/values/{range} - GetValues
		case strings.Contains(r.URL.Path, "/values/") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"range": "Sheet1!A1:C3",
				"values": []any{
					[]any{"Name", "Age", "City"},
					[]any{"Alice", "30", "NYC"},
					[]any{"Bob", "25", "LA"},
				},
			})

		// GET /v4/spreadsheets/{id} - GetSpreadsheet
		case strings.HasPrefix(r.URL.Path, "/v4/spreadsheets/") && r.Method == http.MethodGet:
			json.NewEncoder(w).Encode(map[string]any{
				"spreadsheetId": "spreadsheet-123",
				"properties": map[string]any{
					"title":  "My Spreadsheet",
					"locale": "en_US",
				},
				"spreadsheetUrl": "https://docs.google.com/spreadsheets/d/spreadsheet-123/edit",
				"sheets": []any{
					map[string]any{
						"properties": map[string]any{
							"sheetId":    float64(0),
							"title":      "Sheet1",
							"index":      float64(0),
							"gridProperties": map[string]any{
								"rowCount":    float64(1000),
								"columnCount": float64(26),
							},
						},
					},
					map[string]any{
						"properties": map[string]any{
							"sheetId":    float64(1),
							"title":      "Sheet2",
							"index":      float64(1),
							"gridProperties": map[string]any{
								"rowCount":    float64(500),
								"columnCount": float64(10),
							},
						},
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"error": map[string]any{"message": "not found"}})
		}
	}))
}

func newTestService(serverURL string) *GoogleSheetsService {
	return &GoogleSheetsService{
		baseURL:     serverURL,
		apiKey:      "",
		accessToken: "test-token",
		client:      &http.Client{},
	}
}

func TestGetSpreadsheet(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetSpreadsheet(context.Background(), &pb.GetSpreadsheetRequest{
		SpreadsheetId: "spreadsheet-123",
	})
	if err != nil {
		t.Fatalf("GetSpreadsheet: %v", err)
	}
	if resp.SpreadsheetId != "spreadsheet-123" {
		t.Errorf("expected spreadsheet_id=spreadsheet-123, got %s", resp.SpreadsheetId)
	}
	if resp.Title != "My Spreadsheet" {
		t.Errorf("expected title=My Spreadsheet, got %s", resp.Title)
	}
	if resp.Locale != "en_US" {
		t.Errorf("expected locale=en_US, got %s", resp.Locale)
	}
	if resp.SpreadsheetUrl != "https://docs.google.com/spreadsheets/d/spreadsheet-123/edit" {
		t.Errorf("expected spreadsheet_url, got %s", resp.SpreadsheetUrl)
	}
	if len(resp.Sheets) != 2 {
		t.Fatalf("expected 2 sheets, got %d", len(resp.Sheets))
	}
	if resp.Sheets[0].Title != "Sheet1" {
		t.Errorf("expected first sheet title=Sheet1, got %s", resp.Sheets[0].Title)
	}
	if resp.Sheets[0].SheetId != 0 {
		t.Errorf("expected first sheet id=0, got %d", resp.Sheets[0].SheetId)
	}
	if resp.Sheets[0].RowCount != 1000 {
		t.Errorf("expected row_count=1000, got %d", resp.Sheets[0].RowCount)
	}
	if resp.Sheets[0].ColumnCount != 26 {
		t.Errorf("expected column_count=26, got %d", resp.Sheets[0].ColumnCount)
	}
	if resp.Sheets[1].Title != "Sheet2" {
		t.Errorf("expected second sheet title=Sheet2, got %s", resp.Sheets[1].Title)
	}
}

func TestCreateSpreadsheet(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.CreateSpreadsheet(context.Background(), &pb.CreateSpreadsheetRequest{
		Title:      "New Spreadsheet",
		SheetNames: []string{"Data", "Summary"},
	})
	if err != nil {
		t.Fatalf("CreateSpreadsheet: %v", err)
	}
	if resp.SpreadsheetId != "new-spreadsheet-123" {
		t.Errorf("expected spreadsheet_id=new-spreadsheet-123, got %s", resp.SpreadsheetId)
	}
	if resp.SpreadsheetUrl != "https://docs.google.com/spreadsheets/d/new-spreadsheet-123/edit" {
		t.Errorf("expected spreadsheet_url, got %s", resp.SpreadsheetUrl)
	}
}

func TestGetValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetValues(context.Background(), &pb.GetValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Range:         "Sheet1!A1:C3",
	})
	if err != nil {
		t.Fatalf("GetValues: %v", err)
	}
	if resp.Range != "Sheet1!A1:C3" {
		t.Errorf("expected range=Sheet1!A1:C3, got %s", resp.Range)
	}
	if len(resp.Values) != 3 {
		t.Fatalf("expected 3 rows, got %d", len(resp.Values))
	}
	if len(resp.Values[0].Cells) != 3 {
		t.Fatalf("expected 3 cells in first row, got %d", len(resp.Values[0].Cells))
	}
	if resp.Values[0].Cells[0] != "Name" {
		t.Errorf("expected first cell=Name, got %s", resp.Values[0].Cells[0])
	}
	if resp.Values[0].Cells[1] != "Age" {
		t.Errorf("expected second cell=Age, got %s", resp.Values[0].Cells[1])
	}
	if resp.Values[1].Cells[0] != "Alice" {
		t.Errorf("expected row 2 first cell=Alice, got %s", resp.Values[1].Cells[0])
	}
	if resp.Values[2].Cells[0] != "Bob" {
		t.Errorf("expected row 3 first cell=Bob, got %s", resp.Values[2].Cells[0])
	}
}

func TestBatchGetValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.BatchGetValues(context.Background(), &pb.BatchGetValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Ranges:        []string{"Sheet1!A1:B2", "Sheet2!C3:D4"},
	})
	if err != nil {
		t.Fatalf("BatchGetValues: %v", err)
	}
	if resp.SpreadsheetId != "spreadsheet-123" {
		t.Errorf("expected spreadsheet_id=spreadsheet-123, got %s", resp.SpreadsheetId)
	}
	if len(resp.ValueRanges) != 2 {
		t.Fatalf("expected 2 value ranges, got %d", len(resp.ValueRanges))
	}
	if resp.ValueRanges[0].Range != "Sheet1!A1:B2" {
		t.Errorf("expected first range=Sheet1!A1:B2, got %s", resp.ValueRanges[0].Range)
	}
	if len(resp.ValueRanges[0].Values) != 2 {
		t.Fatalf("expected 2 rows in first range, got %d", len(resp.ValueRanges[0].Values))
	}
	if resp.ValueRanges[0].Values[0].Cells[0] != "A1" {
		t.Errorf("expected first cell=A1, got %s", resp.ValueRanges[0].Values[0].Cells[0])
	}
	if resp.ValueRanges[1].Range != "Sheet2!C3:D4" {
		t.Errorf("expected second range=Sheet2!C3:D4, got %s", resp.ValueRanges[1].Range)
	}
	if resp.ValueRanges[1].Values[0].Cells[0] != "C3" {
		t.Errorf("expected first cell of second range=C3, got %s", resp.ValueRanges[1].Values[0].Cells[0])
	}
}

func TestUpdateValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.UpdateValues(context.Background(), &pb.UpdateValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Range:         "Sheet1!A1:C3",
		Values: []*pb.Row{
			{Cells: []string{"Name", "Age", "City"}},
			{Cells: []string{"Alice", "30", "NYC"}},
			{Cells: []string{"Bob", "25", "LA"}},
		},
	})
	if err != nil {
		t.Fatalf("UpdateValues: %v", err)
	}
	if resp.UpdatedRange != "Sheet1!A1:C3" {
		t.Errorf("expected updated_range=Sheet1!A1:C3, got %s", resp.UpdatedRange)
	}
	if resp.UpdatedRows != 3 {
		t.Errorf("expected updated_rows=3, got %d", resp.UpdatedRows)
	}
	if resp.UpdatedColumns != 3 {
		t.Errorf("expected updated_columns=3, got %d", resp.UpdatedColumns)
	}
	if resp.UpdatedCells != 9 {
		t.Errorf("expected updated_cells=9, got %d", resp.UpdatedCells)
	}
}

func TestAppendValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.AppendValues(context.Background(), &pb.AppendValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Range:         "Sheet1!A1:C3",
		Values: []*pb.Row{
			{Cells: []string{"Charlie", "35", "Chicago"}},
			{Cells: []string{"Diana", "28", "Seattle"}},
		},
	})
	if err != nil {
		t.Fatalf("AppendValues: %v", err)
	}
	if resp.UpdatedRange != "Sheet1!A4:C5" {
		t.Errorf("expected updated_range=Sheet1!A4:C5, got %s", resp.UpdatedRange)
	}
	if resp.UpdatedRows != 2 {
		t.Errorf("expected updated_rows=2, got %d", resp.UpdatedRows)
	}
	if resp.UpdatedColumns != 3 {
		t.Errorf("expected updated_columns=3, got %d", resp.UpdatedColumns)
	}
	if resp.UpdatedCells != 6 {
		t.Errorf("expected updated_cells=6, got %d", resp.UpdatedCells)
	}
}

func TestBatchUpdateValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.BatchUpdateValues(context.Background(), &pb.BatchUpdateValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Data: []*pb.RangeValues{
			{
				Range: "Sheet1!A1:B2",
				Values: []*pb.Row{
					{Cells: []string{"A1", "B1"}},
					{Cells: []string{"A2", "B2"}},
				},
			},
			{
				Range: "Sheet2!C3:D4",
				Values: []*pb.Row{
					{Cells: []string{"C3", "D3"}},
					{Cells: []string{"C4", "D4"}},
				},
			},
		},
	})
	if err != nil {
		t.Fatalf("BatchUpdateValues: %v", err)
	}
	if resp.SpreadsheetId != "spreadsheet-123" {
		t.Errorf("expected spreadsheet_id=spreadsheet-123, got %s", resp.SpreadsheetId)
	}
	if resp.TotalUpdatedRows != 5 {
		t.Errorf("expected total_updated_rows=5, got %d", resp.TotalUpdatedRows)
	}
	if resp.TotalUpdatedColumns != 3 {
		t.Errorf("expected total_updated_columns=3, got %d", resp.TotalUpdatedColumns)
	}
	if resp.TotalUpdatedCells != 15 {
		t.Errorf("expected total_updated_cells=15, got %d", resp.TotalUpdatedCells)
	}
}

func TestClearValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ClearValues(context.Background(), &pb.ClearValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Range:         "Sheet1!A1:C3",
	})
	if err != nil {
		t.Fatalf("ClearValues: %v", err)
	}
	if resp.ClearedRange != "Sheet1!A1:C3" {
		t.Errorf("expected cleared_range=Sheet1!A1:C3, got %s", resp.ClearedRange)
	}
}

func TestBatchClearValues(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.BatchClearValues(context.Background(), &pb.BatchClearValuesRequest{
		SpreadsheetId: "spreadsheet-123",
		Ranges:        []string{"Sheet1!A1:B2", "Sheet2!C3:D4"},
	})
	if err != nil {
		t.Fatalf("BatchClearValues: %v", err)
	}
	if resp.SpreadsheetId != "spreadsheet-123" {
		t.Errorf("expected spreadsheet_id=spreadsheet-123, got %s", resp.SpreadsheetId)
	}
	if len(resp.ClearedRanges) != 2 {
		t.Fatalf("expected 2 cleared ranges, got %d", len(resp.ClearedRanges))
	}
	if resp.ClearedRanges[0] != "Sheet1!A1:B2" {
		t.Errorf("expected first cleared range=Sheet1!A1:B2, got %s", resp.ClearedRanges[0])
	}
	if resp.ClearedRanges[1] != "Sheet2!C3:D4" {
		t.Errorf("expected second cleared range=Sheet2!C3:D4, got %s", resp.ClearedRanges[1])
	}
}

func TestAddSheet(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.AddSheet(context.Background(), &pb.AddSheetRequest{
		SpreadsheetId: "spreadsheet-123",
		Title:         "NewSheet",
		RowCount:      1000,
		ColumnCount:   26,
	})
	if err != nil {
		t.Fatalf("AddSheet: %v", err)
	}
	if resp.SheetId != 42 {
		t.Errorf("expected sheet_id=42, got %d", resp.SheetId)
	}
	if resp.Title != "NewSheet" {
		t.Errorf("expected title=NewSheet, got %s", resp.Title)
	}
	if resp.Index != 1 {
		t.Errorf("expected index=1, got %d", resp.Index)
	}
}

func TestDeleteSheet(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.DeleteSheet(context.Background(), &pb.DeleteSheetRequest{
		SpreadsheetId: "spreadsheet-123",
		SheetId:       1,
	})
	if err != nil {
		t.Fatalf("DeleteSheet: %v", err)
	}
}

func TestDuplicateSheet(t *testing.T) {
	ts := mockSheetsServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.DuplicateSheet(context.Background(), &pb.DuplicateSheetRequest{
		SpreadsheetId: "spreadsheet-123",
		SourceSheetId: 0,
		NewSheetName:  "Copy of Sheet1",
	})
	if err != nil {
		t.Fatalf("DuplicateSheet: %v", err)
	}
	if resp.SheetId != 99 {
		t.Errorf("expected sheet_id=99, got %d", resp.SheetId)
	}
	if resp.Title != "Copy of Sheet1" {
		t.Errorf("expected title=Copy of Sheet1, got %s", resp.Title)
	}
	if resp.Index != 2 {
		t.Errorf("expected index=2, got %d", resp.Index)
	}
}

func TestErrorHandling(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte(`{"error": {"message": "not found"}}`))
	}))
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSpreadsheet(context.Background(), &pb.GetSpreadsheetRequest{
		SpreadsheetId: "nonexistent",
	})
	if err == nil {
		t.Fatal("expected error for 404 response")
	}
	if !strings.Contains(err.Error(), "404") {
		t.Errorf("expected error to contain 404, got %s", err.Error())
	}
}

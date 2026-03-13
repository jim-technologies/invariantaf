package main

import "testing"

func TestServiceCanBeCreated(t *testing.T) {
	svc := NewGoogleSheetsService()
	if svc == nil {
		t.Fatal("service is nil")
	}
}

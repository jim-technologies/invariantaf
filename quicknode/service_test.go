package main

import "testing"

func TestServiceCanBeCreated(t *testing.T) {
	svc := &QuickNodeConsoleService{newQuickNodeClient()}
	if svc == nil {
		t.Fatal("service is nil")
	}
}

package main

import "testing"

func TestServiceCanBeCreated(t *testing.T) {
	svc := NewSteamService()
	if svc == nil {
		t.Fatal("service is nil")
	}
}

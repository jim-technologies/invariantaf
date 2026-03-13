package main

import "testing"

func TestServiceCanBeCreated(t *testing.T) {
	svc := NewPredictFunService()
	if svc == nil {
		t.Fatal("service is nil")
	}
}

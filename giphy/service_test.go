package main

import "testing"

func TestServiceCanBeCreated(t *testing.T) {
	svc := NewGiphyService()
	if svc == nil {
		t.Fatal("service is nil")
	}
}

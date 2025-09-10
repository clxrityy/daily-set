package main

import "testing"

func TestRandomID(t *testing.T) {
	id := randomID()
	if len(id) == 0 {
		t.Fatalf("randomID returned empty string")
	}
}

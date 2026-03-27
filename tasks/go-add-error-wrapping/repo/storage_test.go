package main

import (
	"errors"
	"fmt"
	"testing"
)

func TestFindUserFound(t *testing.T) {
	u, err := FindUser(1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u.Name != "Alice" {
		t.Errorf("got %q, want Alice", u.Name)
	}
}

func TestFindUserNotFound(t *testing.T) {
	_, err := FindUser(999)
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("expected ErrNotFound, got %v", err)
	}
}

func TestNotFoundWrapped(t *testing.T) {
	_, err := FindUser(999)
	// Simulate a caller wrapping the error again
	wrapped := fmt.Errorf("service layer: %w", err)
	if !errors.Is(wrapped, ErrNotFound) {
		t.Errorf("errors.Is failed to unwrap to ErrNotFound: %v", wrapped)
	}
}

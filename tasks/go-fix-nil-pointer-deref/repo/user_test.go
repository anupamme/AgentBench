package main

import "testing"

func TestGetEmailWithContact(t *testing.T) {
	u := &User{
		ID:      1,
		Name:    "Alice",
		Contact: &Contact{Email: "alice@example.com"},
	}
	got := GetEmail(u)
	if got != "alice@example.com" {
		t.Errorf("GetEmail() = %q, want %q", got, "alice@example.com")
	}
}

func TestGetEmailNilContact(t *testing.T) {
	u := &User{ID: 2, Name: "Bob"}
	got := GetEmail(u)
	if got != "" {
		t.Errorf("GetEmail() = %q, want empty string", got)
	}
}

func TestGetName(t *testing.T) {
	u := &User{Name: "Carol"}
	if GetName(u) != "Carol" {
		t.Errorf("GetName() failed")
	}
}
